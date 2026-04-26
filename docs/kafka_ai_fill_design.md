# AI 填单异步处理 Kafka 组件设计文档

## 1. 概述

本文档描述了智能填单系统中 AI 填单功能的异步处理架构设计，使用 Kafka 作为消息队列实现请求的异步处理。

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API 层        │     │   Kafka 组件     │     │   数据库         │
│                 │     │                 │     │                 │
│ get_ai_fill_data│────▶│  Producer       │────▶│ fill_data_record│
│                 │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Kafka Topic   │
                        │ autofill.ai.    │
                        │   requests      │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Consumer      │
                        │                 │
                        │ 处理消息并调用   │
                        │    Dify         │
                        └─────────────────┘
```

### 2.2 流程说明

#### 同步模式 (response_mode=sync)
1. 接收请求参数
2. 存储原始数据到 fill_data_record 表
3. 直接调用 Dify 服务
4. 返回 Dify 响应结果

#### 异步模式 (response_mode=async)
1. 接收请求参数
2. 存储原始数据到 fill_data_record 表，状态为 `pending`
3. 将任务信息发送到 Kafka Topic
4. 更新状态为 `queued`
5. 立即返回队列状态
6. 消费者从 Kafka 获取消息
7. 更新状态为 `processing`
8. 调用 Dify 服务
9. 更新状态为 `completed` 或 `failed`
10. 存储结果到 result 字段

## 3. 数据库设计

### 3.1 fill_data_record 表扩展

新增字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| status | VARCHAR(32) | 处理状态: pending/queued/processing/completed/failed/timeout |
| result | JSON | AI填单结果数据 |
| error_msg | TEXT | 错误信息 |
| processed_at | DATETIME | 处理完成时间 |

### 3.2 状态流转

```
pending ──▶ queued ──▶ processing ──▶ completed
                              │
                              ▼
                           failed/timeout
```

## 4. Kafka 组件设计

### 4.1 Topic 设计

**Topic 名称**: `autofill.ai.requests`

**设计理由**:
- 使用点号分隔的命名空间风格
- `autofill` 表示业务域
- `ai` 表示 AI 相关功能
- `requests` 表示请求类型

**消息格式**:
```json
{
  "session_id": "会话ID",
  "tenant_id": 1,
  "app_name": "应用名称",
  "dify_config": {
    "url": "https://dify.example.com/v1/completion-messages",
    "api_key": "xxx"
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

### 4.2 生产者 (Producer)

**文件**: `app/core/kafka/producer.py`

**功能**:
- 基于 confluent-kafka-python (librdkafka)
- 支持异步发送消息
- 提供发送回调机制
- 全局单例模式

**配置项**:
- acks: all (等待所有副本确认)
- retries: 3 (发送失败重试次数)
- batch.size: 16384 (批量发送大小)
- linger.ms: 10 (延迟发送时间)

### 4.3 消费者 (Consumer)

**文件**: `app/core/kafka/consumer.py`

**功能**:
- 基于 confluent-kafka-python (librdkafka)
- 独立线程运行消费循环
- 支持异步消息处理器
- 消费者管理器支持多消费者

**配置项**:
- group.id: autofill-consumer-group
- auto.offset.reset: earliest
- enable.auto.commit: true
- auto.commit.interval.ms: 5000

## 5. Service 层设计

### 5.1 AIFillService

**文件**: `app/services/ai_fill_service.py`

**核心方法**:

| 方法 | 说明 |
|------|------|
| process_sync | 同步处理请求 |
| process_async | 异步处理请求，发送到 Kafka |
| process_kafka_message | Kafka 消费者调用，处理消息 |
| get_result | 查询异步处理结果 |
| _call_dify | 内部方法，调用 Dify 服务 |

### 5.2 职责分离

- **API 层**: 参数解析、认证、响应封装
- **Service 层**: 业务逻辑、状态管理、Dify 调用
- **Kafka 层**: 消息队列抽象、生产消费

## 6. 配置说明

### 6.1 config.toml 配置

```toml
[kafka]
# Kafka 连接配置
bootstrap_servers = "localhost:9092"
client_id = "autofill-python-client"

# 生产者配置
[kafka.producer]
acks = "all"              # 等待所有副本确认
retries = 3               # 发送失败重试次数
batch_size = 16384        # 批量发送大小
linger_ms = 10            # 延迟发送时间

# 消费者配置
[kafka.consumer]
group_id = "autofill-consumer-group"
auto_offset_reset = "earliest"   # 从最早消息开始消费
enable_auto_commit = true        # 自动提交偏移量
auto_commit_interval_ms = 5000   # 自动提交间隔

# 主题配置
[kafka.topic]
name = "autofill.ai.requests"
partitions = 3
replication_factor = 1
```

## 7. API 接口变更

### 7.1 获取 AI 填单数据

**接口**: `GET/POST /autofill/get_ai_fill_data`

**新增参数**:
- `response_mode`: 响应模式，可选 `sync`(默认) 或 `async`

**同步响应**:
```json
{
  "code": 200,
  "data": { /* Dify 响应内容 */ },
  "msg": "success"
}
```

**异步响应**:
```json
{
  "code": 200,
  "data": {
    "session_id": "xxx",
    "status": "queued",
    "message": "Request has been queued for async processing"
  },
  "msg": "success"
}
```

### 7.2 查询异步结果 (新增)

**接口**: `GET/POST /autofill/get_ai_fill_data_result`

**参数**:
- `session_id`: 会话ID

**响应**:
```json
{
  "code": 200,
  "data": {
    "session_id": "xxx",
    "status": "completed",
    "data": { /* 原始数据 */ },
    "result": { /* Dify 结果 */ },
    "error_msg": null,
    "created_at": "2024-01-01T00:00:00",
    "processed_at": "2024-01-01T00:00:05"
  },
  "msg": "success"
}
```

## 8. 启动流程

1. 应用启动时初始化数据库
2. 初始化 Redis 连接
3. 初始化 Kafka 消费者
   - 注册 AI 填单消费者
   - 订阅 `autofill.ai.requests` Topic
   - 启动消费线程
4. 应用就绪，开始接收请求

## 9. 关闭流程

1. 停止接收新请求
2. 关闭 Kafka 消费者
3. 关闭 Redis 连接
4. 关闭数据库连接

## 10. 错误处理

### 10.1 生产者错误
- 发送失败时更新记录状态为 `failed`
- 记录错误日志
- 返回 500 错误给调用方

### 10.2 消费者错误
- 处理异常时更新记录状态为 `failed`
- 记录错误日志
- 继续消费下一条消息

### 10.3 Dify 调用错误
- 超时：状态更新为 `timeout`
- HTTP 错误：状态更新为 `failed`，记录状态码
- 其他异常：状态更新为 `failed`，记录错误信息

## 11. 监控与日志

### 11.1 关键日志点
- 消费者启动/停止
- 消息发送成功/失败
- 消息处理开始/完成/失败
- Dify 调用耗时

### 11.2 监控指标
- 消息堆积数量
- 消费速率
- 处理成功率
- 平均处理耗时

## 12. 扩展性考虑

### 12.1 水平扩展
- 增加 Kafka 分区数可支持更多消费者实例
- 消费者组机制保证消息只被消费一次

### 12.2 未来扩展
- 支持更多 Topic 类型（如通知、日志等）
- 支持消息重试机制
- 支持死信队列
- 支持消息优先级

## 13. 文件清单

| 文件路径 | 说明 |
|----------|------|
| app/core/kafka/__init__.py | Kafka 模块入口 |
| app/core/kafka/config.py | Kafka 配置管理 |
| app/core/kafka/producer.py | Kafka 生产者 |
| app/core/kafka/consumer.py | Kafka 消费者 |
| app/services/ai_fill_service.py | AI 填单服务层 |
| app/api/autofill_public.py | 公开 API 接口 |
| app/models/autofill.py | 数据模型 |
| app/models/enums.py | 枚举定义 |
| app/schemas/autofill.py | 请求/响应 Schema |
| app/core/init_app.py | 应用初始化 |
| app/__init__.py | FastAPI 应用 |

## 14. 依赖项

新增依赖：
- `confluent-kafka==2.8.0` - Kafka 客户端 (librdkafka)
- `toml==0.10.2` - TOML 配置解析

## 15. 部署注意事项

1. 确保 Kafka 服务可访问
2. 配置正确的 bootstrap_servers 地址
3. 创建所需的 Topic（或配置自动创建）
4. 监控消费者组消费延迟
5. 配置适当的日志级别
