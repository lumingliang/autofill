"""
Kafka 组件模块
提供基于 librdkafka (confluent-kafka-python) 的生产者和消费者功能
"""
from .config import KafkaConfig
from .producer import KafkaProducer, get_kafka_producer, close_kafka_producer
from .consumer import KafkaConsumer, get_consumer_manager, init_kafka_consumers, shutdown_kafka_consumers

__all__ = [
    "KafkaConfig",
    "KafkaProducer",
    "get_kafka_producer",
    "close_kafka_producer",
    "KafkaConsumer",
    "get_consumer_manager",
    "init_kafka_consumers",
    "shutdown_kafka_consumers",
]