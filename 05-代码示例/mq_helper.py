# SPDX-License-Identifier: MIT
"""
消息队列测试辅助：Kafka / RabbitMQ
被引用方：13-系统集成测试 agent
"""
import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ===== Kafka =====

class KafkaProducerSimple:
    def __init__(self, brokers: Optional[str] = None):
        try:
            from kafka import KafkaProducer
        except ImportError:
            raise RuntimeError("kafka-python 未安装")
        b = brokers or os.getenv("KAFKA_BROKERS", "localhost:9092")
        self.producer = KafkaProducer(
            bootstrap_servers=b.split(","),
            key_serializer=lambda k: (k or "").encode("utf-8"),
            value_serializer=lambda v: json.dumps(v).encode("utf-8") if not isinstance(v, bytes) else v,
        )

    def send(self, topic: str, value: Any, key: Optional[str] = None):
        future = self.producer.send(topic, key=key, value=value)
        result = future.get(timeout=10)
        logger.info(f"Kafka 发送成功: {topic} → partition={result.partition}, offset={result.offset}")
        return {"partition": result.partition, "offset": result.offset}

    def close(self):
        self.producer.flush()
        self.producer.close()


class KafkaConsumerSimple:
    def __init__(self, brokers: Optional[str] = None, topic: str = "",
                 group: str = "test-group", from_beginning: bool = True):
        try:
            from kafka import KafkaConsumer, TopicPartition
        except ImportError:
            raise RuntimeError("kafka-python 未安装")
        b = brokers or os.getenv("KAFKA_BROKERS", "localhost:9092")
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=b.split(","),
            group_id=group,
            auto_offset_reset="earliest" if from_beginning else "latest",
            enable_auto_commit=True,
            consumer_timeout_ms=10_000,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None,
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
        )

    def poll(self, timeout: float = 10) -> Optional[Dict]:
        records = self.consumer.poll(timeout_ms=int(timeout * 1000), max_records=1)
        for _tp, msgs in records.items():
            for msg in msgs:
                return {
                    "topic": msg.topic, "partition": msg.partition, "offset": msg.offset,
                    "key": msg.key, "value": msg.value,
                }
        return None

    def close(self):
        self.consumer.close()


# ===== RabbitMQ =====

class RabbitMQClient:
    def __init__(self, url: Optional[str] = None):
        try:
            import pika
        except ImportError:
            raise RuntimeError("pika 未安装")
        u = url or os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.connection = pika.BlockingConnection(pika.URLParameters(u))
        self.channel = self.connection.channel()

    def publish(self, queue: str, body: str):
        self.channel.queue_declare(queue=queue, durable=True)
        self.channel.basic_publish(exchange="", routing_key=queue, body=body)

    def get(self, queue: str, timeout: float = 10) -> Optional[bytes]:
        end = time.time() + timeout
        while time.time() < end:
            method, props, body = self.channel.basic_get(queue=queue, auto_ack=True)
            if body is not None:
                return body
            time.sleep(0.2)
        return None

    def close(self):
        self.connection.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("mq_helper module loaded")
