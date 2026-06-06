"""
Kafka 配置管理
"""
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

import toml


@dataclass
class KafkaProducerConfig:
    """Kafka 生产者配置"""
    acks: str = "all"
    retries: int = 3
    batch_size: int = 16384
    linger_ms: int = 10


@dataclass
class KafkaConsumerConfig:
    """Kafka 消费者配置"""
    group_id: str = "autofill-consumer-group"
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True
    auto_commit_interval_ms: int = 5000


@dataclass
class KafkaTopicConfig:
    """Kafka Topic 配置"""
    name: str = "autofill-ai-requests"
    partitions: int = 3
    replication_factor: int = 1


@dataclass
class KafkaSaslConfig:
    """Kafka SASL 认证配置"""
    enabled: bool = False
    mechanism: str = "PLAIN"  # PLAIN, SCRAM-SHA-256, SCRAM-SHA-512, GSSAPI, OAUTHBEARER
    username: str = ""
    password: str = ""
    protocol: str = "SASL_PLAINTEXT"  # SASL_PLAINTEXT, SASL_SSL
    # SSL 相关配置（当 protocol 为 SASL_SSL 时使用）
    ca_location: str = ""  # CA 证书路径
    cert_location: str = ""  # 客户端证书路径
    key_location: str = ""  # 客户端私钥路径
    key_password: str = ""  # 私钥密码


@dataclass
class KafkaConfig:
    """Kafka 全局配置"""
    bootstrap_servers: str = "localhost:9092"
    client_id: str = "autofill-python-client"
    producer: KafkaProducerConfig = field(default_factory=KafkaProducerConfig)
    consumer: KafkaConsumerConfig = field(default_factory=KafkaConsumerConfig)
    topic: KafkaTopicConfig = field(default_factory=KafkaTopicConfig)
    sasl: KafkaSaslConfig = field(default_factory=KafkaSaslConfig)

    @classmethod
    def from_toml(cls, config_path: Optional[str] = None) -> "KafkaConfig":
        """从 TOML 配置文件加载配置"""
        if config_path is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            config_path = os.path.join(base_dir, "config.toml")

        if not os.path.exists(config_path):
            return cls()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = toml.load(f)

            kafka_config = config.get("kafka", {})

            # 基础配置
            bootstrap_servers = kafka_config.get("bootstrap_servers", "localhost:9092")
            client_id = kafka_config.get("client_id", "autofill-python-client")

            # 生产者配置
            producer_config = kafka_config.get("producer", {})
            producer = KafkaProducerConfig(
                acks=producer_config.get("acks", "all"),
                retries=producer_config.get("retries", 3),
                batch_size=producer_config.get("batch_size", 16384),
                linger_ms=producer_config.get("linger_ms", 10),
            )

            # 消费者配置
            consumer_config = kafka_config.get("consumer", {})
            consumer = KafkaConsumerConfig(
                group_id=consumer_config.get("group_id", "autofill-consumer-group"),
                auto_offset_reset=consumer_config.get("auto_offset_reset", "earliest"),
                enable_auto_commit=consumer_config.get("enable_auto_commit", True),
                auto_commit_interval_ms=consumer_config.get("auto_commit_interval_ms", 5000),
            )

            # Topic 配置
            topic_config = kafka_config.get("topic", {})
            topic = KafkaTopicConfig(
                name=topic_config.get("name", "autofill-ai-requests"),
                partitions=topic_config.get("partitions", 3),
                replication_factor=topic_config.get("replication_factor", 1),
            )

            # SASL 配置
            sasl_config = kafka_config.get("sasl", {})
            sasl = KafkaSaslConfig(
                enabled=sasl_config.get("enabled", False),
                mechanism=sasl_config.get("mechanism", "PLAIN"),
                username=sasl_config.get("username", ""),
                password=sasl_config.get("password", ""),
                protocol=sasl_config.get("protocol", "SASL_PLAINTEXT"),
                ca_location=sasl_config.get("ca_location", ""),
                cert_location=sasl_config.get("cert_location", ""),
                key_location=sasl_config.get("key_location", ""),
                key_password=sasl_config.get("key_password", ""),
            )

            return cls(
                bootstrap_servers=bootstrap_servers,
                client_id=client_id,
                producer=producer,
                consumer=consumer,
                topic=topic,
                sasl=sasl,
            )
        except Exception as e:
            print(f"Warning: Failed to load Kafka config from TOML: {e}")
            return cls()

    def _get_sasl_config(self) -> Dict[str, Any]:
        """获取 SASL 认证配置字典"""
        if not self.sasl.enabled:
            return {}

        config = {
            "security.protocol": self.sasl.protocol,
            "sasl.mechanism": self.sasl.mechanism,
            "sasl.username": self.sasl.username,
            "sasl.password": self.sasl.password,
        }

        # SSL 相关配置
        if self.sasl.protocol == "SASL_SSL":
            if self.sasl.ca_location:
                config["ssl.ca.location"] = self.sasl.ca_location
            if self.sasl.cert_location:
                config["ssl.certificate.location"] = self.sasl.cert_location
            if self.sasl.key_location:
                config["ssl.key.location"] = self.sasl.key_location
            if self.sasl.key_password:
                config["ssl.key.password"] = self.sasl.key_password

        return config

    def get_producer_config(self) -> Dict[str, Any]:
        """获取生产者配置字典"""
        config = {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": f"{self.client_id}-producer",
            "acks": self.producer.acks,
            "retries": self.producer.retries,
            "batch.size": self.producer.batch_size,
            "linger.ms": self.producer.linger_ms,
            "allow.auto.create.topics": True,  # 允许自动创建 Topic
        }
        # 添加 SASL 配置
        config.update(self._get_sasl_config())
        return config

    def get_consumer_config(self) -> Dict[str, Any]:
        """获取消费者配置字典"""
        config = {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": f"{self.client_id}-consumer",
            "group.id": self.consumer.group_id,
            "auto.offset.reset": self.consumer.auto_offset_reset,
            "enable.auto.commit": self.consumer.enable_auto_commit,
            "auto.commit.interval.ms": self.consumer.auto_commit_interval_ms,
            "allow.auto.create.topics": True,  # 允许自动创建 Topic
        }
        # 添加 SASL 配置
        config.update(self._get_sasl_config())
        return config