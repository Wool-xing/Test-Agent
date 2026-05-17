# SPDX-License-Identifier: MIT
"""
通用协议测试工具：gRPC / TCP / UDP / GraphQL / SOAP / Modbus
HTTP/REST 用 requests + utils.api_retry_util；WebSocket 用 utils.websocket_helper；
MQTT/SSH/串口用 utils.iot_helper；Kafka/RabbitMQ 用 utils.mq_helper。
"""
import json
import logging
import socket
import time
from xml.sax.saxutils import escape as xml_escape
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ===== TCP =====

def tcp_send_recv(host: str, port: int, payload: bytes,
                   timeout: float = 5, recv_size: int = 4096) -> bytes:
    """TCP 单次发送 + 接收"""
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(payload)
        return s.recv(recv_size)


class TCPClient:
    """长连接 TCP 客户端"""

    def __init__(self, host: str, port: int, timeout: float = 5):
        self.sock = socket.create_connection((host, port), timeout=timeout)

    def send(self, data: bytes):
        self.sock.sendall(data)

    def recv(self, size: int = 4096) -> bytes:
        return self.sock.recv(size)

    def close(self):
        self.sock.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ===== UDP =====

def udp_send_recv(host: str, port: int, payload: bytes,
                   timeout: float = 5, recv_size: int = 4096) -> bytes:
    """UDP 单次发送 + 接收"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        s.sendto(payload, (host, port))
        data, _ = s.recvfrom(recv_size)
        return data


# ===== GraphQL =====

def graphql_query(endpoint: str, query: str, variables: Optional[Dict] = None,
                   headers: Optional[Dict] = None, timeout: float = 30) -> Dict:
    """GraphQL 查询/变更"""
    import requests
    body = {"query": query, "variables": variables or {}}
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    r = requests.post(endpoint, json=body, headers=h, timeout=timeout)
    r.raise_for_status()
    return r.json()


# ===== SOAP =====

def soap_call(endpoint: str, action: str, body_xml: str,
               timeout: float = 30) -> str:
    """SOAP 简化调用（用 requests + 手拼 envelope）"""
    import requests
    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>{xml_escape(body_xml)}</soap:Body>
</soap:Envelope>"""
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": action,
    }
    r = requests.post(endpoint, data=envelope, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text


# ===== gRPC =====

def grpc_call(stub_class_path: str, method: str, request_obj: Any,
               address: str, timeout: float = 10) -> Any:
    """
    动态调 gRPC stub。需先 protoc 生成 _pb2_grpc.py + _pb2.py。
    stub_class_path: "your_module._pb2_grpc.YourServiceStub"
    """
    import grpc
    import importlib

    module_path, class_name = stub_class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    StubClass = getattr(module, class_name)

    with grpc.insecure_channel(address) as ch:
        stub = StubClass(ch)
        rpc = getattr(stub, method)
        return rpc(request_obj, timeout=timeout)


# ===== Modbus =====

def modbus_read_holding(host: str, port: int = 502, address: int = 0,
                         count: int = 1, unit: int = 1, timeout: float = 5) -> Optional[list]:
    """Modbus TCP 读保持寄存器"""
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        raise RuntimeError("pymodbus 未安装：pip install pymodbus")
    with ModbusTcpClient(host=host, port=port, timeout=timeout) as client:
        rr = client.read_holding_registers(address, count, slave=unit)
        if rr.isError():
            logger.error(f"Modbus 错误: {rr}")
            return None
        return rr.registers


def modbus_write_register(host: str, port: int = 502, address: int = 0,
                           value: int = 0, unit: int = 1, timeout: float = 5) -> bool:
    """Modbus TCP 写单个寄存器"""
    from pymodbus.client import ModbusTcpClient
    with ModbusTcpClient(host=host, port=port, timeout=timeout) as client:
        rr = client.write_register(address, value, slave=unit)
        return not rr.isError()


# ===== TCP/UDP 端口探活 =====

def is_tcp_open(host: str, port: int, timeout: float = 3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


# ===== CLI =====

def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="通用协议工具")
    sub = parser.add_subparsers(dest="cmd")

    tcp = sub.add_parser("tcp")
    tcp.add_argument("--host", required=True)
    tcp.add_argument("--port", type=int, required=True)
    tcp.add_argument("--data", required=True, help="hex 编码的数据，如 0a0b0c")

    udp = sub.add_parser("udp")
    udp.add_argument("--host", required=True)
    udp.add_argument("--port", type=int, required=True)
    udp.add_argument("--data", required=True)

    gql = sub.add_parser("graphql")
    gql.add_argument("--endpoint", required=True)
    gql.add_argument("--query", required=True)

    probe = sub.add_parser("probe")
    probe.add_argument("--host", required=True)
    probe.add_argument("--port", type=int, required=True)

    args = parser.parse_args()
    if args.cmd == "tcp":
        resp = tcp_send_recv(args.host, args.port, bytes.fromhex(args.data))
        print(resp.hex())
    elif args.cmd == "udp":
        resp = udp_send_recv(args.host, args.port, bytes.fromhex(args.data))
        print(resp.hex())
    elif args.cmd == "graphql":
        print(json.dumps(graphql_query(args.endpoint, args.query), indent=2, ensure_ascii=False))
    elif args.cmd == "probe":
        print("OPEN" if is_tcp_open(args.host, args.port) else "CLOSED")


if __name__ == "__main__":
    main()
