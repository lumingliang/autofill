"""
Kafka 消费者组件
基于 confluent-kafka-python (librdkafka)
"""
import asyncio
import json
import signal
import threading
from typing import Any, Callable, Dict, List, Optional

from confluent_kafka import Consumer, KafkaError, KafkaException

from app.log import logger
from .config import KafkaConfig


class KafkaConsumer:
    """Kafka 消费者封装"""

    def __init__(
        self,
        topics: List[str],
        config: Optional[KafkaConfig] = None,
        message_handler: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.config = config or KafkaConfig.from_toml()
        self.topics = topics if isinstance(topics, list) else [topics]
        self._consumer: Optional[Consumer] = None
        self._message_handler = message_handler
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def connect(self) -> "KafkaConsumer":
        """连接 Kafka"""
        if self._consumer is None:
            config = self.config.get_consumer_config()
            self._consumer = Consumer(config)
            self._consumer.subscribe(self.topics)
            logger.info(f"Kafka consumer connected to {self.config.bootstrap_servers}, subscribed to: {self.topics}")
        return self

    def disconnect(self):
        """断开连接"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        if self._consumer:
            self._consumer.close()
            self._consumer = None
            logger.info("Kafka consumer disconnected")

    def _deserialize_message(self, msg: Any) -> Optional[Dict[str, Any]]:
        """反序列化消息"""
        try:
            value = msg.value()
            if value is None:
                return None
            return json.loads(value.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to deserialize message: {e}")
            return None

    def _consume_loop(self):
        """消费循环（在独立线程中运行）"""
        logger.info(f"Kafka consumer loop started for topics: {self.topics}")

        while self._running:
            try:
                msg = self._consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f"Reached end of partition {msg.topic()}[{msg.partition()}]")
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                else:
                    # 处理消息
                    data = self._deserialize_message(msg)
                    if data:
                        logger.info(f"[KAFKA CONSUMER] Received message from {msg.topic()}[{msg.partition()}] @ offset {msg.offset()}")
                        logger.info(f"[KAFKA CONSUMER] Message key: {msg.key().decode('utf-8') if msg.key() else None}")
                        logger.info(f"[KAFKA CONSUMER] Message content: {data}")

                        # 添加元数据
                        data["_kafka_meta"] = {
                            "topic": msg.topic(),
                            "partition": msg.partition(),
                            "offset": msg.offset(),
                            "timestamp": msg.timestamp()[1] if msg.timestamp() else None,
                        }

                        # 调用消息处理器
                        if self._message_handler:
                            try:
                                logger.info(f"[KAFKA CONSUMER] Calling message handler for session: {data.get('session_id')}")
                                if asyncio.iscoroutinefunction(self._message_handler):
                                    # 如果是异步函数，使用事件循环
                                    if self._loop and self._loop.is_running():
                                        future = asyncio.run_coroutine_threadsafe(
                                            self._message_handler(data), self._loop
                                        )
                                        logger.info(f"[KAFKA CONSUMER] Async message handler scheduled, waiting for result...")
                                        # 等待异步任务完成（带超时）
                                        try:
                                            future.result(timeout=120)  # 等待最多120秒
                                            logger.info(f"[KAFKA CONSUMER] Async message handler completed successfully")
                                        except Exception as e:
                                            logger.error(f"[KAFKA CONSUMER] Async message handler failed: {e}", exc_info=True)
                                    else:
                                        logger.error(f"[KAFKA CONSUMER] Event loop not available or not running")
                                else:
                                    self._message_handler(data)
                                    logger.info(f"[KAFKA CONSUMER] Sync message handler completed")
                            except Exception as e:
                                logger.error(f"[KAFKA CONSUMER] Error in message handler: {e}", exc_info=True)

            except Exception as e:
                logger.error(f"Error in consume loop: {e}")

        logger.info("Kafka consumer loop stopped")

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """启动消费者"""
        if self._running:
            logger.warning("Consumer is already running")
            return

        self.connect()
        self._running = True
        self._loop = loop

        logger.info(f"[KAFKA CONSUMER] Starting consumer with loop: {loop}")
        if loop:
            logger.info(f"[KAFKA CONSUMER] Loop is running: {loop.is_running()}")

        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()

        logger.info(f"Kafka consumer started for topics: {self.topics}")

    def stop(self):
        """停止消费者"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self.disconnect()
        logger.info("Kafka consumer stopped")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class KafkaConsumerManager:
    """Kafka 消费者管理器 - 管理多个消费者"""

    def __init__(self):
        self._consumers: Dict[str, KafkaConsumer] = {}
        self._running = False

    def register_consumer(
        self,
        name: str,
        topics: List[str],
        message_handler: Callable[[Dict[str, Any]], None],
        config: Optional[KafkaConfig] = None
    ):
        """注册消费者"""
        if name in self._consumers:
            logger.warning(f"Consumer '{name}' already registered, will be replaced")
            self._consumers[name].stop()

        consumer = KafkaConsumer(
            topics=topics,
            config=config,
            message_handler=message_handler
        )
        self._consumers[name] = consumer
        logger.info(f"Registered consumer '{name}' for topics: {topics}")

    def start_all(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """启动所有消费者"""
        self._running = True
        for name, consumer in self._consumers.items():
            try:
                consumer.start(loop=loop)
                logger.info(f"Started consumer: {name}")
            except Exception as e:
                logger.error(f"Failed to start consumer '{name}': {e}")

    def stop_all(self):
        """停止所有消费者"""
        self._running = False
        for name, consumer in self._consumers.items():
            try:
                consumer.stop()
                logger.info(f"Stopped consumer: {name}")
            except Exception as e:
                logger.error(f"Error stopping consumer '{name}': {e}")
        self._consumers.clear()


# 全局消费者管理器实例
_consumer_manager: Optional[KafkaConsumerManager] = None


def get_consumer_manager() -> KafkaConsumerManager:
    """获取全局消费者管理器"""
    global _consumer_manager
    if _consumer_manager is None:
        _consumer_manager = KafkaConsumerManager()
    return _consumer_manager


def init_kafka_consumers(loop: Optional[asyncio.AbstractEventLoop] = None):
    """初始化并启动所有 Kafka 消费者"""
    manager = get_consumer_manager()
    manager.start_all(loop=loop)
    logger.info("All Kafka consumers initialized")


def shutdown_kafka_consumers():
    """关闭所有 Kafka 消费者"""
    global _consumer_manager
    if _consumer_manager:
        _consumer_manager.stop_all()
        _consumer_manager = None
        logger.info("All Kafka consumers shutdown")