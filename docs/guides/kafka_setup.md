# Kafka 设置指南

## 自动创建 Topic

代码已配置 `allow.auto.create.topics: true`，如果 Kafka 服务器也开启了自动创建 Topic，则无需手动创建。

## 使用 Python 脚本创建 Topic（推荐）

项目提供了 Python 脚本用于管理 Kafka Topic：

```bash
# 进入项目目录
cd /Users/lu/code/code/py/autofill

# 激活 conda 环境
source /opt/homebrew/Caskroom/miniconda/base/bin/activate autofill

# 创建 Topic（使用默认配置）
python scripts/create_kafka_topic.py

# 指定参数创建 Topic
python scripts/create_kafka_topic.py \
  --bootstrap-servers localhost:9092 \
  --topic autofill.ai.requests \
  --partitions 3 \
  --replication-factor 1

# 列出所有 Topic
python scripts/create_kafka_topic.py list

# 列出指定服务器的 Topic
python scripts/create_kafka_topic.py list --bootstrap-servers localhost:9092

# 删除 Topic
python scripts/create_kafka_topic.py delete --topic autofill.ai.requests
```

## 手动创建 Topic（Kafka 命令行）

如果 Kafka 服务器禁用了自动创建 Topic，请使用以下命令手动创建：

```bash
# 进入 Kafka 安装目录
cd /path/to/kafka

# 创建 Topic
bin/kafka-topics.sh --create \
  --topic autofill.ai.requests \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1

# 查看 Topic 列表
bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# 查看 Topic 详情
bin/kafka-topics.sh --describe \
  --topic autofill.ai.requests \
  --bootstrap-server localhost:9092
```

## 使用 Docker 创建 Topic

如果使用 Docker 运行 Kafka：

```bash
# 进入 Kafka 容器
docker exec -it kafka-container-name bash

# 创建 Topic
kafka-topics.sh --create \
  --topic autofill.ai.requests \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

## 检查 Kafka 服务器配置

在 Kafka 服务器的 `config/server.properties` 文件中，确保以下配置：

```properties
# 允许自动创建 Topic（默认 true）
auto.create.topics.enable=true

# 默认分区数
num.partitions=3

# 默认副本因子
default.replication.factor=1
```

## 测试 Kafka 连接

```bash
# 发送测试消息
bin/kafka-console-producer.sh \
  --topic autofill.ai.requests \
  --bootstrap-server localhost:9092

# 消费测试消息
bin/kafka-console-consumer.sh \
  --topic autofill.ai.requests \
  --from-beginning \
  --bootstrap-server localhost:9092
```
