#!/usr/bin/env python3
"""
Kafka 状态检查脚本
用于诊断 Kafka 消费者和消息队列状态
"""
import asyncio
import sys
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.models.autofill import FillDataRecord
from app.models.enums import AIFillDataStatus
from app.core.kafka import KafkaConfig
from confluent_kafka.admin import AdminClient
from confluent_kafka import Consumer, KafkaException


async def check_database_records():
    """检查数据库中的记录状态"""
    print("\n" + "=" * 60)
    print("数据库记录状态检查")
    print("=" * 60)

    # 统计各状态记录数
    status_counts = {}
    for status in AIFillDataStatus:
        count = await FillDataRecord.filter(status=status.value).count()
        status_counts[status.value] = count

    print("\n各状态记录数:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    # 显示最近 5 条 queued 状态的记录
    queued_records = await FillDataRecord.filter(
        status=AIFillDataStatus.QUEUED.value
    ).order_by('-created_at').limit(5).all()

    if queued_records:
        print(f"\n最近 5 条 queued 状态的记录:")
        for record in queued_records:
            print(f"  - session_id: {record.session_id}")
            print(f"    created_at: {record.created_at}")
            print(f"    app_name: {record.app_name}")
            print(f"    tenant_id: {record.tenant_id}")
    else:
        print("\n没有 queued 状态的记录")

    # 显示最近 5 条 processing 状态的记录
    processing_records = await FillDataRecord.filter(
        status=AIFillDataStatus.PROCESSING.value
    ).order_by('-created_at').limit(5).all()

    if processing_records:
        print(f"\n最近 5 条 processing 状态的记录:")
        for record in processing_records:
            print(f"  - session_id: {record.session_id}")
            print(f"    created_at: {record.created_at}")
    else:
        print("\n没有 processing 状态的记录")


def check_kafka_topic():
    """检查 Kafka Topic 状态"""
    print("\n" + "=" * 60)
    print("Kafka Topic 状态检查")
    print("=" * 60)

    config = KafkaConfig.from_toml()
    bootstrap_servers = config.bootstrap_servers
    topic_name = config.topic.name

    print(f"\nKafka 服务器: {bootstrap_servers}")
    print(f"Topic 名称: {topic_name}")

    # 创建 Admin Client
    admin_conf = {'bootstrap.servers': bootstrap_servers}
    admin_client = AdminClient(admin_conf)

    try:
        # 获取 Topic 元数据
        metadata = admin_client.list_topics(timeout=10)

        if topic_name in metadata.topics:
            topic = metadata.topics[topic_name]
            print(f"\nTopic '{topic_name}' 存在")
            print(f"  分区数: {len(topic.partitions)}")

            # 检查每个分区的消息数
            consumer_conf = {
                'bootstrap.servers': bootstrap_servers,
                'group.id': 'check-kafka-status',
                'auto.offset.reset': 'earliest'
            }
            consumer = Consumer(consumer_conf)

            total_messages = 0
            for partition_id in topic.partitions:
                topic_partition = TopicPartition(topic_name, partition_id)
                low, high = consumer.get_watermark_offsets(topic_partition)
                count = high - low
                total_messages += count
                print(f"  分区 {partition_id}: {count} 条消息 (offset: {low} - {high})")

            print(f"\n  总计: {total_messages} 条消息")
            consumer.close()
        else:
            print(f"\nTopic '{topic_name}' 不存在!")
            print("  请先创建 Topic:")
            print(f"  python scripts/create_kafka_topic.py --topic {topic_name}")

    except KafkaException as e:
        print(f"\n连接 Kafka 失败: {e}")
        print("  请检查:")
        print("  1. Kafka 服务是否启动")
        print("  2. 配置文件中的 bootstrap_servers 是否正确")


def check_consumer_group():
    """检查消费者组状态"""
    print("\n" + "=" * 60)
    print("消费者组状态检查")
    print("=" * 60)

    config = KafkaConfig.from_toml()
    bootstrap_servers = config.bootstrap_servers
    group_id = config.consumer.group_id

    print(f"\nKafka 服务器: {bootstrap_servers}")
    print(f"消费者组: {group_id}")

    # 创建 Admin Client
    admin_conf = {'bootstrap.servers': bootstrap_servers}
    admin_client = AdminClient(admin_conf)

    try:
        # 获取消费者组信息
        groups = admin_client.list_groups()
        found = False
        for group in groups:
            if group.id == group_id:
                found = True
                print(f"\n消费者组 '{group_id}' 存在")
                print(f"  状态: {group.state}")
                print(f"  协议类型: {group.protocol_type}")
                print(f"  成员数: {len(group.members)}")

        if not found:
            print(f"\n消费者组 '{group_id}' 不存在或未激活")
            print("  消费者可能尚未启动或没有消费消息")

    except KafkaException as e:
        print(f"\n获取消费者组信息失败: {e}")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Kafka AI 填单系统状态检查")
    print("=" * 60)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查数据库
    await check_database_records()

    # 检查 Kafka Topic
    check_kafka_topic()

    # 检查消费者组
    check_consumer_group()

    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)


if __name__ == '__main__':
    # 导入需要的模块
    from confluent_kafka import TopicPartition

    # 初始化 Tortoise ORM
    from tortoise import Tortoise
    from app.settings.config import settings

    async def init_orm():
        await Tortoise.init(config=settings.TORTOISE_ORM)

    async def close_orm():
        await Tortoise.close_connections()

    async def run():
        await init_orm()
        try:
            await main()
        finally:
            await close_orm()

    asyncio.run(run())
