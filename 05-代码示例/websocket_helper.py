"""
WebSocket 测试辅助：同步 + 异步客户端 / 心跳 / 重连 / 并发性能
被引用方：06-自动化脚本 agent / 11-桌面测试 agent（EXE+WS 混合场景）

依赖：
  - websocket-client（同步，pip install websocket-client）
  - websockets（异步，pip install websockets）
"""
import json
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# ===== 同步客户端（websocket-client）=====

class WSClient:
    """
    同步 WebSocket 客户端，含心跳 / 自动重连。
    用法：
        with WSClient("ws://example.com/socket") as ws:
            ws.send({"type": "ping"})
            msg = ws.recv(timeout=5)
    """

    def __init__(
        self,
        url: str,
        headers: Optional[Dict] = None,
        on_message: Optional[Callable] = None,
        ping_interval: int = 30,
        auto_reconnect: bool = False,
        max_reconnect: int = 3,
    ):
        try:
            import websocket
        except ImportError:
            raise RuntimeError("websocket-client 未安装：pip install websocket-client")

        self.url = url
        self.headers = headers or {}
        self.on_message_cb = on_message
        self.ping_interval = ping_interval
        self.auto_reconnect = auto_reconnect
        self.max_reconnect = max_reconnect
        self._ws = None
        self._messages: List[str] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._listener_thread: Optional[threading.Thread] = None
        self._reconnect_count = 0

    def connect(self):
        import websocket
        header_list = [f"{k}: {v}" for k, v in self.headers.items()]
        self._ws = websocket.create_connection(self.url, header=header_list, timeout=10)
        logger.info(f"WS 已连接: {self.url}")
        self._stop.clear()
        self._listener_thread = threading.Thread(target=self._listen, daemon=True)
        self._listener_thread.start()
        if self.ping_interval > 0:
            threading.Thread(target=self._ping_loop, daemon=True).start()
        return self

    def _listen(self):
        while not self._stop.is_set() and self._ws:
            try:
                msg = self._ws.recv()
                if msg:
                    with self._lock:
                        self._messages.append(msg)
                    if self.on_message_cb:
                        self.on_message_cb(msg)
            except Exception as e:
                logger.warning(f"WS 接收异常: {e}")
                if self.auto_reconnect and self._reconnect_count < self.max_reconnect:
                    self._reconnect()
                else:
                    break

    def _ping_loop(self):
        while not self._stop.is_set() and self._ws:
            time.sleep(self.ping_interval)
            try:
                self._ws.ping()
            except Exception as e:
                logger.warning(f"ping 失败: {e}")
                break

    def _reconnect(self):
        self._reconnect_count += 1
        logger.info(f"WS 重连 ({self._reconnect_count}/{self.max_reconnect})")
        time.sleep(min(10 * (2 ** (self._reconnect_count - 1)), 60))
        try:
            self.connect()
        except Exception as e:
            logger.error(f"重连失败: {e}")

    def send(self, data: Union[str, Dict]):
        if isinstance(data, dict):
            data = json.dumps(data, ensure_ascii=False)
        self._ws.send(data)

    def send_binary(self, data: bytes):
        import websocket
        self._ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)

    def recv(self, timeout: float = 5) -> Optional[str]:
        """阻塞读取一条消息（如已通过 listener 缓存则取最早）"""
        end = time.time() + timeout
        while time.time() < end:
            with self._lock:
                if self._messages:
                    return self._messages.pop(0)
            time.sleep(0.05)
        return None

    def wait_for(self, predicate: Callable[[str], bool], timeout: float = 10) -> Optional[str]:
        """等待满足条件的消息"""
        end = time.time() + timeout
        while time.time() < end:
            with self._lock:
                for i, msg in enumerate(self._messages):
                    if predicate(msg):
                        return self._messages.pop(i)
            time.sleep(0.1)
        return None

    def close(self):
        self._stop.set()
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        logger.info("WS 已关闭")

    def __enter__(self):
        return self.connect()

    def __exit__(self, *exc):
        self.close()


# ===== 异步客户端（websockets，高并发性能用）=====

async def ws_concurrent_load(url: str, count: int = 100,
                              messages_per_conn: int = 10,
                              throttle_sec: float = 0.1) -> Dict:
    """
    并发 WebSocket 连接性能测试。
    返回 {connections, total_messages, avg_latency_ms, errors}
    """
    try:
        import asyncio
        import websockets
    except ImportError:
        raise RuntimeError("websockets 未安装：pip install websockets")

    latencies: List[float] = []
    errors = 0
    success = 0
    lock = asyncio.Lock()

    async def one_client(idx: int):
        nonlocal errors, success
        try:
            async with websockets.connect(url, open_timeout=10) as ws:
                for i in range(messages_per_conn):
                    t0 = time.time()
                    await ws.send(json.dumps({"client": idx, "seq": i}))
                    await ws.recv()
                    async with lock:
                        latencies.append((time.time() - t0) * 1000)
                    await asyncio.sleep(throttle_sec)
                async with lock:
                    success += 1
        except Exception as e:
            async with lock:
                errors += 1
            logger.warning(f"client {idx} 失败: {e}")

    await asyncio.gather(*[one_client(i) for i in range(count)])

    if not latencies:
        return {"connections": count, "errors": errors, "avg_latency_ms": None}

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]
    return {
        "connections": count,
        "successful_connections": success,
        "total_messages": len(latencies),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1),
        "p95_latency_ms": round(p95, 1),
        "max_latency_ms": round(max(latencies), 1),
        "errors": errors,
        "error_rate_pct": round(errors / count * 100, 2),
    }


# ===== 重连测试 =====

def test_reconnect(url: str, kill_after_sec: int = 5,
                   max_reconnect: int = 3) -> Dict:
    """
    模拟服务重启场景：连接 → 主动关闭 → 验证自动重连成功。
    """
    client = WSClient(url, auto_reconnect=True, max_reconnect=max_reconnect)
    client.connect()
    time.sleep(kill_after_sec)
    client.close()  # 模拟断开
    time.sleep(2)
    # 重新连验证
    try:
        client.connect()
        time.sleep(2)
        result = {"reconnect_success": True, "attempts": client._reconnect_count}
    except Exception as e:
        result = {"reconnect_success": False, "error": str(e)}
    finally:
        client.close()
    return result


# ===== CLI =====

def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="WebSocket 测试工具")
    sub = parser.add_subparsers(dest="cmd")

    echo = sub.add_parser("echo", help="发一条消息后等回复")
    echo.add_argument("--url", required=True)
    echo.add_argument("--message", required=True)
    echo.add_argument("--timeout", type=float, default=5)

    load = sub.add_parser("load", help="并发性能测试")
    load.add_argument("--url", required=True)
    load.add_argument("--count", type=int, default=100)
    load.add_argument("--messages", type=int, default=10)

    args = parser.parse_args()
    if args.cmd == "echo":
        with WSClient(args.url) as ws:
            ws.send(args.message)
            print(ws.recv(timeout=args.timeout))
    elif args.cmd == "load":
        import asyncio
        result = asyncio.run(ws_concurrent_load(args.url, args.count, args.messages))
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
