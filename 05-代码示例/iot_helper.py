"""
IoT / 嵌入式辅助：SSH / 串口 / MQTT
被引用方：13-系统集成测试 agent
"""
import logging
import os
import threading
import time
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


# ===== SSH =====

class SSHClient:
    def __init__(self, host: str, user: str, password: Optional[str] = None,
                 key_path: Optional[str] = None, port: int = 22):
        try:
            import paramiko
        except ImportError:
            raise RuntimeError("paramiko 未安装")
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if key_path:
            self.client.connect(host, port=port, username=user, key_filename=key_path, timeout=10)
        else:
            self.client.connect(host, port=port, username=user, password=password, timeout=10)
        logger.info(f"SSH 连接成功: {user}@{host}:{port}")

    def exec(self, cmd: str, timeout: int = 30) -> str:
        stdin, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        if err and not out:
            logger.warning(f"stderr: {err.strip()}")
        return out

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ===== 串口 =====

def open_serial(port: str, baudrate: int = 115200, timeout: float = 3.0):
    try:
        import serial
    except ImportError:
        raise RuntimeError("pyserial 未安装")
    ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
    logger.info(f"串口打开: {port} @ {baudrate}")
    return ser


# ===== MQTT =====

class MQTTClient:
    def __init__(self, broker: str, port: int = 1883,
                 username: Optional[str] = None, password: Optional[str] = None):
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            raise RuntimeError("paho-mqtt 未安装")
        self.client = mqtt.Client()
        if username:
            self.client.username_pw_set(username, password)
        self.broker = broker
        self.port = port
        self._messages: List[str] = []
        self._lock = threading.Lock()
        self.client.on_message = self._on_message

    def connect(self):
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()
        logger.info(f"MQTT 已连接: {self.broker}:{self.port}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def subscribe(self, topic: str, on_message: Optional[Callable] = None):
        if on_message:
            self._on_msg_cb = on_message
        self.client.subscribe(topic)

    def publish(self, topic: str, payload: str, qos: int = 1):
        self.client.publish(topic, payload, qos=qos)

    def _on_message(self, client, userdata, msg):
        text = msg.payload.decode("utf-8", errors="ignore")
        with self._lock:
            self._messages.append(text)
        if hasattr(self, "_on_msg_cb"):
            self._on_msg_cb(text)

    def wait_messages(self, timeout: float = 10, expected: int = 1) -> List[str]:
        end = time.time() + timeout
        while time.time() < end:
            with self._lock:
                if len(self._messages) >= expected:
                    return list(self._messages)
            time.sleep(0.1)
        with self._lock:
            return list(self._messages)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("iot_helper module loaded")
