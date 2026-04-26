#!/usr/bin/env python3
"""
Kafka Topic 创建脚本
用于手动创建 AI 填单所需的 Kafka Topic
"""
import argparse
import sys

from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaException


def create_topic(
    bootstrap_servers: str,
    topic_name: str,
    num_partitions: int = 3,
    replication_factor: int = 1
):
    """
    创建 Kafka Topic

    Args:
        bootstrap_servers: Kafka 服务器地址，如 "localhost:9092"
        topic_name: Topic 名称
        num_partitions: 分区数，默认 3
        replication_factor: 副本因子，默认 1
    """
    # 创建 Admin Client
    conf = {
        'bootstrap.servers': bootstrap_servers
    }
    admin_client = AdminClient(conf)

    # 检查 Topic 是否已存在
    try:
        metadata = admin_client.list_topics(timeout=10)
        if topic_name in metadata.topics:
            print(f"Topic '{topic_name}' 已存在，无需创建")
            return True
    except KafkaException as e:
        print(f"获取 Topic 列表失败: {e}")
        return False

    # 创建 Topic
    new_topic = NewTopic(
        topic=topic_name,
        num_partitions=num_partitions,
        replication_factor=replication_factor
    )

    # 异步创建
    fs = admin_client.create_topics([new_topic])

    # 等待结果
    for topic, f in fs.items():
        try:
            f.result()  # 等待操作完成
            print(f"Topic '{topic}' 创建成功")
            print(f"  - 分区数: {num_partitions}")
            print(f"  - 副本因子: {replication_factor}")
            return True
        except KafkaException as e:
            print(f"创建 Topic '{topic}' 失败: {e}")
            return False


def list_topics(bootstrap_servers: str):
    """列出所有 Topic"""
    conf = {
        'bootstrap.servers': bootstrap_servers
    }
    admin_client = AdminClient(conf)

    try:
        metadata = admin_client.list_topics(timeout=10)
        print(f"\nKafka 服务器: {bootstrap_servers}")
        print(f"Topic 列表:")
        print("-" * 50)
        for topic_name in metadata.topics:
            topic = metadata.topics[topic_name]
            print(f"  {topic_name}: {len(topic.partitions)} 个分区")
        print("-" * 50)
    except KafkaException as e:
        print(f"获取 Topic 列表失败: {e}")


def delete_topic(bootstrap_servers: str, topic_name: str):
    """删除 Topic"""
    conf = {
        'bootstrap.servers': bootstrap_servers
    }
    admin_client = AdminClient(conf)

    fs = admin_client.delete_topics([topic_name])

    for topic, f in fs.items():
        try:
            f.result()
            print(f"Topic '{topic}' 删除成功")
        except KafkaException as e:
            print(f"删除 Topic '{topic}' 失败: {e}")


def main():
    parser = argparse.ArgumentParser(description='Kafka Topic 管理工具')
    parser.add_argument(
        '--bootstrap-servers',
        default='localhost:9092',
        help='Kafka 服务器地址 (默认: localhost:9092)'
    )
    parser.add_argument(
        '--topic',
        default='autofill.ai.requests',
        help='Topic 名称 (默认: autofill.ai.requests)'
    )
    parser.add_argument(
        '--partitions',
        type=int,
        default=3,
        help='分区数 (默认: 3)'
    )
    parser.add_argument(
        '--replication-factor',
        type=int,
        default=1,
        help='副本因子 (默认: 1)'
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # 创建命令
    create_parser = subparsers.add_parser('create', help='创建 Topic')

    # 列出命令
    list_parser = subparsers.add_parser('list', help='列出所有 Topic')

    # 删除命令
    delete_parser = subparsers.add_parser('delete', help='删除 Topic')

    args = parser.parse_args()

    if args.command == 'create' or args.command is None:
        # 默认执行创建
        success = create_topic(
            bootstrap_servers=args.bootstrap_servers,
            topic_name=args.topic,
            num_partitions=args.partitions,
            replication_factor=args.replication_factor
        )
        sys.exit(0 if success else 1)

    elif args.command == 'list':
        list_topics(args.bootstrap_servers)

    elif args.command == 'delete':
        confirm = input(f"确定要删除 Topic '{args.topic}' 吗? (yes/no): ")
        if confirm.lower() == 'yes':
            delete_topic(args.bootstrap_servers, args.topic)
        else:
            print("操作已取消")


if __name__ == '__main__':
    main()
