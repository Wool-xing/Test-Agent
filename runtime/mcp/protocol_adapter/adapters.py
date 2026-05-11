"""5 concrete adapters: HTTP, gRPC, WebSocket, MQTT, Kafka."""

from __future__ import annotations

import json
import time
from typing import Any

from loguru import logger

from runtime.mcp.protocol_adapter.base import ProtocolAdapter, ProtocolResult, register


@register("http")
class HTTPAdapter(ProtocolAdapter):
    def __init__(self) -> None:
        self._client = None
        self._target: str | None = None

    async def connect(self, target: str, **kwargs) -> None:
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("httpx not installed") from e
        self._client = httpx.AsyncClient(timeout=kwargs.get("timeout", 30.0))
        self._target = target

    async def send(self, payload: bytes | str | dict, *, method: str = "POST", **kwargs) -> ProtocolResult:
        start = time.monotonic()
        try:
            kwargs.setdefault("json" if isinstance(payload, dict) else "content", payload)
            resp = await self._client.request(method, self._target, **kwargs)
            elapsed = int((time.monotonic() - start) * 1000)
            return ProtocolResult(
                ok=resp.is_success,
                payload=resp.text,
                elapsed_ms=elapsed,
                meta={"status_code": resp.status_code, "headers": dict(resp.headers)},
            )
        except Exception as e:
            return ProtocolResult(ok=False, payload=None, elapsed_ms=int((time.monotonic() - start) * 1000), error=str(e))

    async def recv(self, timeout: float = 30.0, **kwargs) -> ProtocolResult:
        # HTTP is request-response; recv reuses last send result if needed.
        return ProtocolResult(ok=True, payload=None, elapsed_ms=0, meta={"note": "HTTP is request-response"})

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def ping(self, target: str, payload: bytes | str | dict = b"ping", timeout: float = 10.0) -> ProtocolResult:
        await self.connect(target, timeout=timeout)
        try:
            return await self.send(payload, method="GET")
        finally:
            await self.close()


@register("grpc")
class GRPCAdapter(ProtocolAdapter):
    """Generic gRPC adapter (uses grpcio reflection if available, else fails-fast).

    Production usage requires per-service stub. Here we provide a ping helper
    using grpc health check service (standard).
    """

    def __init__(self) -> None:
        self._channel = None
        self._target: str | None = None

    async def connect(self, target: str, **kwargs) -> None:
        try:
            import grpc  # type: ignore
        except ImportError as e:
            raise RuntimeError("grpcio not installed") from e
        self._channel = grpc.aio.insecure_channel(target)
        self._target = target

    async def send(self, payload: bytes | str | dict, *, service: str = "", **kwargs) -> ProtocolResult:
        # Health check ping (grpc.health.v1.Health/Check)
        start = time.monotonic()
        try:
            from grpc_health.v1 import health_pb2, health_pb2_grpc  # type: ignore
            stub = health_pb2_grpc.HealthStub(self._channel)
            req = health_pb2.HealthCheckRequest(service=service)
            resp = await stub.Check(req, timeout=kwargs.get("timeout", 10.0))
            elapsed = int((time.monotonic() - start) * 1000)
            return ProtocolResult(
                ok=resp.status == health_pb2.HealthCheckResponse.SERVING,
                payload={"status": health_pb2.HealthCheckResponse.ServingStatus.Name(resp.status)},
                elapsed_ms=elapsed,
            )
        except ImportError:
            return ProtocolResult(ok=False, payload=None, elapsed_ms=0, error="grpcio-health-checking not installed")
        except Exception as e:
            return ProtocolResult(ok=False, payload=None, elapsed_ms=int((time.monotonic() - start) * 1000), error=str(e))

    async def recv(self, timeout: float = 30.0, **kwargs) -> ProtocolResult:
        return ProtocolResult(ok=True, payload=None, elapsed_ms=0, meta={"note": "gRPC is request-response by default"})

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
            self._channel = None


@register("ws")
class WebSocketAdapter(ProtocolAdapter):
    def __init__(self) -> None:
        self._ws = None

    async def connect(self, target: str, **kwargs) -> None:
        try:
            import websockets  # type: ignore
        except ImportError as e:
            raise RuntimeError("websockets not installed") from e
        self._ws = await websockets.connect(target, **kwargs)

    async def send(self, payload: bytes | str | dict, **kwargs) -> ProtocolResult:
        start = time.monotonic()
        try:
            data = json.dumps(payload) if isinstance(payload, dict) else payload
            await self._ws.send(data)
            return ProtocolResult(ok=True, payload=None, elapsed_ms=int((time.monotonic() - start) * 1000))
        except Exception as e:
            return ProtocolResult(ok=False, payload=None, elapsed_ms=int((time.monotonic() - start) * 1000), error=str(e))

    async def recv(self, timeout: float = 30.0, **kwargs) -> ProtocolResult:
        import asyncio

        start = time.monotonic()
        try:
            msg = await asyncio.wait_for(self._ws.recv(), timeout=timeout)
            return ProtocolResult(ok=True, payload=msg, elapsed_ms=int((time.monotonic() - start) * 1000))
        except Exception as e:
            return ProtocolResult(ok=False, payload=None, elapsed_ms=int((time.monotonic() - start) * 1000), error=str(e))

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None


@register("mqtt")
class MQTTAdapter(ProtocolAdapter):
    """MQTT v3.1.1 via paho-mqtt sync client wrapped in asyncio threadpool.

    Charter §21 横切准则: paho-mqtt's on_message callback runs on the network
    thread. We guard the shared buffer with a lock so async recv() and the
    callback don't race.
    """

    def __init__(self) -> None:
        import threading

        self._client = None
        self._target = None
        self._topic: str = ""
        self._buffer: list[dict] = []
        self._buffer_lock = threading.Lock()

    async def connect(self, target: str, *, topic: str = "test/agent", **kwargs) -> None:
        import asyncio

        try:
            import paho.mqtt.client as mqtt  # type: ignore
        except ImportError as e:
            raise RuntimeError("paho-mqtt not installed") from e
        host, _, port_s = target.partition(":")
        port = int(port_s) if port_s else 1883
        client = mqtt.Client()

        def _on_msg(c, u, msg):
            with self._buffer_lock:
                self._buffer.append({"topic": msg.topic, "payload": msg.payload.decode("utf-8", "replace")})

        client.on_message = _on_msg
        # asyncio.get_event_loop() is deprecated in 3.12+; use get_running_loop()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, client.connect, host, port, 30)
        client.subscribe(topic)
        client.loop_start()
        self._client = client
        self._target = target
        self._topic = topic

    async def send(self, payload: bytes | str | dict, *, topic: str | None = None, **kwargs) -> ProtocolResult:
        start = time.monotonic()
        try:
            data = json.dumps(payload) if isinstance(payload, dict) else payload
            self._client.publish(topic or self._topic, data, qos=kwargs.get("qos", 1))
            return ProtocolResult(ok=True, payload=None, elapsed_ms=int((time.monotonic() - start) * 1000))
        except Exception as e:
            return ProtocolResult(ok=False, payload=None, elapsed_ms=int((time.monotonic() - start) * 1000), error=str(e))

    async def recv(self, timeout: float = 30.0, **kwargs) -> ProtocolResult:
        import asyncio

        start = time.monotonic()
        deadline = start + timeout
        while time.monotonic() < deadline:
            with self._buffer_lock:
                msg = self._buffer.pop(0) if self._buffer else None
            if msg is not None:
                return ProtocolResult(ok=True, payload=msg, elapsed_ms=int((time.monotonic() - start) * 1000))
            await asyncio.sleep(0.05)
        return ProtocolResult(ok=False, payload=None, elapsed_ms=int((time.monotonic() - start) * 1000), error="recv timeout")

    async def close(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None


@register("kafka")
class KafkaAdapter(ProtocolAdapter):
    """Kafka via aiokafka."""

    def __init__(self) -> None:
        self._producer = None
        self._consumer = None
        self._topic: str | None = None

    async def connect(self, target: str, *, topic: str = "test-agent", group_id: str = "tagent", **kwargs) -> None:
        try:
            from aiokafka import AIOKafkaConsumer, AIOKafkaProducer  # type: ignore
        except ImportError as e:
            raise RuntimeError("aiokafka not installed") from e
        self._producer = AIOKafkaProducer(bootstrap_servers=target)
        self._consumer = AIOKafkaConsumer(topic, bootstrap_servers=target, group_id=group_id, auto_offset_reset="earliest")
        await self._producer.start()
        await self._consumer.start()
        self._topic = topic

    async def send(self, payload: bytes | str | dict, *, topic: str | None = None, **kwargs) -> ProtocolResult:
        start = time.monotonic()
        try:
            data = json.dumps(payload).encode() if isinstance(payload, dict) else (
                payload.encode() if isinstance(payload, str) else payload
            )
            await self._producer.send_and_wait(topic or self._topic, data)
            return ProtocolResult(ok=True, payload=None, elapsed_ms=int((time.monotonic() - start) * 1000))
        except Exception as e:
            return ProtocolResult(ok=False, payload=None, elapsed_ms=int((time.monotonic() - start) * 1000), error=str(e))

    async def recv(self, timeout: float = 30.0, **kwargs) -> ProtocolResult:
        import asyncio

        start = time.monotonic()
        try:
            msg = await asyncio.wait_for(self._consumer.getone(), timeout=timeout)
            return ProtocolResult(
                ok=True,
                payload={"topic": msg.topic, "value": msg.value.decode("utf-8", "replace")},
                elapsed_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as e:
            return ProtocolResult(ok=False, payload=None, elapsed_ms=int((time.monotonic() - start) * 1000), error=str(e))

    async def close(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
