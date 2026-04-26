"""
Kafka 生产者组件
基于 confluent-kafka-python (librdkafka)
"""
import json
import logging
from typing import Any, Dict, Optional, Callable

from confluent_kafka import Producer, KafkaError

from .config import KafkaConfig

logger = logging.getLogger(__name__)


class KafkaProducer:
    """Kafka 生产者封装"""

    def __init__(self, config: Optional[KafkaConfig] = None):
        self.config = config or KafkaConfig.from_toml()
        self._producer: Optional[Producer] = None
        self._delivery_callbacks: Dict[str, Callable] = {}

    def _delivery_callback(self, err: Optional[KafkaError], msg: Any, message_id: str):
        """消息投递回调函数"""
        callback = self._delivery_callbacks.pop(message_id, None)

        if err is not None:
            logger.error(f"Message delivery failed: {err}")
            if callback:
                callback(False, str(err))
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}")
            if callback:
                callback(True, None)

    def connect(self) -> "KafkaProducer":
        """连接 Kafka"""
        if self._producer is None:
            config = self.config.get_producer_config()
            self._producer = Producer(config)
            logger.info(f"Kafka producer connected to {self.config.bootstrap_servers}")
        return self

    def disconnect(self):
        """断开连接"""
        if self._producer:
            self._producer.flush(timeout=30)
            self._producer = None
            logger.info("Kafka producer disconnected")

    def produce(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        callback: Optional[Callable[[bool, Optional[str]], None]] = None
    ) -> bool:
        """
        发送消息到 Kafka

        Args:
            topic: Topic 名称
            value: 消息内容（字典，会被序列化为 JSON）
            key: 消息键（可选）
            headers: 消息头（可选）
            callback: 发送回调函数，参数为 (success: bool, error: Optional[str])

        Returns:
            bool: 是否成功加入发送队列
        """
        if self._producer is None:
            self.connect()

        try:
            # 生成消息 ID 用于回调跟踪
            import uuid
            message_id = str(uuid.uuid4())

            # 序列化消息
            value_bytes = json.dumps(value, ensure_ascii=False).encode("utf-8")
            key_bytes = key.encode("utf-8") if key else None

            logger.info(f"[KAFKA PRODUCER] Sending message to topic '{topic}'")
            logger.info(f"[KAFKA PRODUCER] Message key: {key}")
            logger.info(f"[KAFKA PRODUCER] Message content: {value}")

            # 转换 headers 格式
            headers_list = None
            if headers:
                headers_list = [(k, v.encode("utf-8")) for k, v in headers.items()]

            # 存储回调
            if callback:
                self._delivery_callbacks[message_id] = callback

            # 发送消息
            self._producer.produce(
                topic=topic,
                value=value_bytes,
                key=key_bytes,
                headers=headers_list,
                callback=lambda err, msg: self._delivery_callback(err, msg, message_id)
            )
            logger.info(f"[KAFKA PRODUCER] Message queued successfully, message_id: {message_id}")

            # 触发 poll 处理回调
            self._producer.poll(0)

            return True
        except Exception as e:
            logger.error(f"Failed to produce message: {e}")
            if callback:
                callback(False, str(e))
            return False

    def flush(self, timeout: float = 30.0):
        """刷新缓冲区，等待所有消息发送完成"""
        if self._producer:
            self._producer.flush(timeout=timeout)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# 全局生产者实例
_kafka_producer: Optional[KafkaProducer] = None


def get_kafka_producer() -> KafkaProducer:
    """获取全局 Kafka 生产者实例"""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = KafkaProducer().connect()
    return _kafka_producer


def close_kafka_producer():
    """关闭全局 Kafka 生产者实例"""
    global _kafka_producer
    if _kafka_producer:
        _kafka_producer.disconnect()
        _kafka_producer = None