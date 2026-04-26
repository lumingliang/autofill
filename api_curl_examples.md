# 智能填单系统公开接口 Curl 示例

> **API Key**: `af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR`  
> **Base URL**: `http://localhost:9999/api`

---

## 1. 查询模板列表

### GET 方式（URL 参数需要编码）
```bash
curl -X GET "http://localhost:9999/api/autofill/summary_template/list?class_name=%E5%85%85%E7%94%B5%E6%95%85%E9%9A%9C" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
```

或使用 `--data-urlencode` 自动编码：
```bash
curl -X GET "http://localhost:9999/api/autofill/summary_template/list" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  --data-urlencode "class_name=充电故障"
```

### POST + JSON Body 方式（推荐，无需编码）
```bash
curl -X POST "http://localhost:9999/api/autofill/summary_template/list" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/json" \
  -d '{
    "class_name": "充电故障"
  }'
```

### POST + Form 数据方式
```bash
curl -X POST "http://localhost:9999/api/autofill/summary_template/list" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "class_name=充电故障"
```

---

## 2. 查询模板详情

### GET 方式
```bash
curl -X GET "http://localhost:9999/api/autofill/summary_template?id=1" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
```

### POST + JSON Body 方式（推荐）
```bash
curl -X POST "http://localhost:9999/api/autofill/summary_template" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1
  }'
```

### POST + Form 数据方式
```bash
curl -X POST "http://localhost:9999/api/autofill/summary_template" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "id=1"
```

---

## 3. 查询下拉选项列表

### GET 方式（URL 参数需要编码）
```bash
curl -X GET "http://localhost:9999/api/autofill/dropdown_options/list?class_name=%E4%B8%9A%E5%8A%A1%E7%B1%BB%E5%9E%8B&parent_id=0" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
```

或使用 `--data-urlencode`：
```bash
curl -X GET "http://localhost:9999/api/autofill/dropdown_options/list" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  --data-urlencode "class_name=业务类型" \
  -d "parent_id=0"
```

### POST + JSON Body 方式（推荐）
```bash
curl -X POST "http://localhost:9999/api/autofill/dropdown_options/list" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/json" \
  -d '{
    "class_name": "业务类型",
    "parent_id": 0
  }'
```

### POST + Form 数据方式
```bash
curl -X POST "http://localhost:9999/api/autofill/dropdown_options/list" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "class_name=业务类型" \
  -d "parent_id=0"
```

---

## 4. 查询下拉选项详情

### GET 方式
```bash
curl -X GET "http://localhost:9999/api/autofill/dropdown_options?id=1" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
```

### POST + JSON Body 方式（推荐）
```bash
curl -X POST "http://localhost:9999/api/autofill/dropdown_options" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1
  }'
```

### POST + Form 数据方式
```bash
curl -X POST "http://localhost:9999/api/autofill/dropdown_options" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "id=1"
```

---

## 5. 记录填单数据

### GET 方式（仅简单参数）
```bash
curl -X GET "http://localhost:9999/api/autofill/record_fill_data?session_id=session_001&phone=13800138000" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
```

### POST + JSON Body 方式（推荐）
```bash
curl -X POST "http://localhost:9999/api/autofill/record_fill_data" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_001",
    "phone": "13800138000",
    "user_name": "张三",
    "user_unique_id": "user_001",
    "data": {
      "customer_name": "张三",
      "vehicle_system": "比亚迪汉EV",
      "vin_code": "LGX12345678901234",
      "issue_type": "预约充电故障",
      "description": "预约充电功能异常"
    }
  }'
```

### POST + Form 数据方式
```bash
curl -X POST "http://localhost:9999/api/autofill/record_fill_data" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "session_id=session_001" \
  -d "phone=13800138000" \
  --data-urlencode "user_name=张三" \
  -d "user_unique_id=user_001"
```

---

## 6. 获取AI填单数据

### GET 方式（仅简单参数）
```bash
curl -X GET "http://localhost:9999/api/autofill/get_ai_fill_data?session_id=session_001" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
```

### POST + JSON Body 方式（推荐）
```bash
curl -X POST "http://localhost:9999/api/autofill/get_ai_fill_data" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_001",
    "data": {
      "chat_messages": [
        {"type": "user", "msg": "我的车空调不制冷，风也不凉", "timestamp": "2024-01-15T10:00:00Z"},
        {"type": "assistant", "msg": "您好，我是比亚迪客服，请问您的车系和车架号是多少？", "timestamp": "2024-01-15T10:00:05Z"},
        {"type": "user", "msg": "汉EV，车架号LGXCE6CB5L1234567", "timestamp": "2024-01-15T10:00:15Z"},
        {"type": "assistant", "msg": "好的，请问您车辆目前行驶里程是多少？空调是从什么时候开始不制冷的？", "timestamp": "2024-01-15T10:00:25Z"},
        {"type": "user", "msg": "行驶了3万多公里，昨天开始不制冷的", "timestamp": "2024-01-15T10:00:35Z"},
        {"type": "assistant", "msg": "了解了，请问您设置的空调温度是多少度？风量档位开到最大了吗？", "timestamp": "2024-01-15T10:00:45Z"},
        {"type": "user", "msg": "设置18度，风量最大了，吹出来的还是热风", "timestamp": "2024-01-15T10:00:55Z"},
        {"type": "assistant", "msg": "收到，我已记录您的问题。空调制冷异常，车系汉EV，车架号LGXCE6CB5L1234567，行驶3万公里，昨天开始出现不制冷现象，设置18度最大风量仍出热风。我们会安排技师为您检修。", "timestamp": "2024-01-15T10:01:00Z"}
      ],
      "user_info": {"name": "李四", "phone": "13912345678"},
      "vehicle_info": {"model": "汉EV", "vin": "LGXCE6CB5L1234567", "mileage": "30000"},
      "issue_summary": "空调不制冷，设置18度最大风量仍出热风"
    }
  }'
```

### POST + Form 数据方式
```bash
curl -X POST "http://localhost:9999/api/autofill/get_ai_fill_data" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "session_id=session_001"
```

---

## 异步调用示例

### 1. 发送异步请求

添加 `response_mode=async` 参数，将请求放入 Kafka 队列异步处理：

```bash
curl -X POST "http://localhost:9999/api/autofill/get_ai_fill_data" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_async_001",
    "response_mode": "async",
    "data": {
      "chat_messages": [
        {"type": "user", "msg": "我的车空调不制冷，风也不凉", "timestamp": "2024-01-15T10:00:00Z"},
        {"type": "assistant", "msg": "您好，我是比亚迪客服，请问您的车系和车架号是多少？", "timestamp": "2024-01-15T10:00:05Z"},
        {"type": "user", "msg": "汉EV，车架号LGXCE6CB5L1234567", "timestamp": "2024-01-15T10:00:15Z"},
        {"type": "assistant", "msg": "好的，请问您车辆目前行驶里程是多少？空调是从什么时候开始不制冷的？", "timestamp": "2024-01-15T10:00:25Z"},
        {"type": "user", "msg": "行驶了3万多公里，昨天开始不制冷的", "timestamp": "2024-01-15T10:00:35Z"},
        {"type": "assistant", "msg": "了解了，请问您设置的空调温度是多少度？风量档位开到最大了吗？", "timestamp": "2024-01-15T10:00:45Z"},
        {"type": "user", "msg": "设置18度，风量最大了，吹出来的还是热风", "timestamp": "2024-01-15T10:00:55Z"},
        {"type": "assistant", "msg": "收到，我已记录您的问题。空调制冷异常，车系汉EV，车架号LGXCE6CB5L1234567，行驶3万公里，昨天开始出现不制冷现象，设置18度最大风量仍出热风。我们会安排技师为您检修。", "timestamp": "2024-01-15T10:01:00Z"}
      ],
      "user_info": {"name": "李四", "phone": "13912345678"},
      "vehicle_info": {"model": "汉EV", "vin": "LGXCE6CB5L1234567", "mileage": "30000"},
      "issue_summary": "空调不制冷，设置18度最大风量仍出热风"
    }
  }'
```

**返回示例（异步模式）：**
```json
{
  "code": 200,
  "data": {
    "session_id": "sess_async_001",
    "status": "queued",
    "message": "Request has been queued for async processing"
  },
  "msg": "success"
}
```

### 2. 查询异步处理结果

使用 `session_id` 查询处理结果：

```bash
curl -X POST "http://localhost:9999/api/autofill/get_ai_fill_data_result" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_async_001"
  }'
```

**返回示例（处理中）：**
```json
{
  "code": 200,
  "data": {
    "session_id": "sess_async_001",
    "status": "processing",
    "data": {
      "original_data": {
        "chat_messages": [...]
      }
    },
    "result": null,
    "error_msg": null,
    "created_at": "2024-01-15T10:00:00",
    "processed_at": null
  },
  "msg": "success"
}
```

**返回示例（已完成）：**
```json
{
  "code": 200,
  "data": {
    "session_id": "sess_async_001",
    "status": "completed",
    "data": {
      "original_data": {
        "chat_messages": [...]
      }
    },
    "result": {
      "answer": "AI 处理结果...",
      "conversation_id": "xxx"
    },
    "error_msg": null,
    "created_at": "2024-01-15T10:00:00",
    "processed_at": "2024-01-15T10:00:05"
  },
  "msg": "success"
}
```

### 3. 状态流转说明

| 状态 | 说明 |
|------|------|
| `pending` | 待处理 - 已写入数据库，等待发送到 Kafka |
| `queued` | 已入队 - 已发送到 Kafka 队列 |
| `processing` | 处理中 - 消费者正在调用 Dify |
| `completed` | 已完成 - 成功获取 Dify 结果 |
| `failed` | 失败 - 处理过程中出错 |
| `timeout` | 超时 - Dify 请求超时 |

---

## 接口说明

| 序号 | 接口路径 | 功能说明 |
|------|----------|----------|
| 1 | `/autofill/summary_template/list` | 查询模板列表 |
| 2 | `/autofill/summary_template` | 查询模板详情 |
| 3 | `/autofill/dropdown_options/list` | 查询下拉选项列表 |
| 4 | `/autofill/dropdown_options` | 查询下拉选项详情 |
| 5 | `/autofill/record_fill_data` | 记录填单数据 |
| 6 | `/autofill/get_ai_fill_data` | 获取AI填单数据 |

## 请求方式说明

| 方式 | 适用场景 | 中文处理 |
|------|----------|----------|
| **GET** | 简单参数查询 | 需要 URL 编码或使用 `--data-urlencode` |
| **POST + JSON Body** | 推荐方式，支持复杂数据结构 | 无需编码，直接写中文 |
| **POST + Form 数据** | 传统表单提交 | 使用 `--data-urlencode` 处理中文 |

## 认证方式

所有接口都需要在 Header 中携带 API Key：
```
Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR
```

## 常见问题

**Q: GET 请求中文参数报错？**  
A: URL 中的中文字符需要编码，建议使用：
1. `--data-urlencode` 参数让 curl 自动编码
2. 或者使用 POST + JSON Body 方式（推荐）

**Q: 如何选择请求方式？**  
A: 推荐使用 **POST + JSON Body**，因为：
1. 支持复杂嵌套数据结构
2. 中文无需特殊处理
3. 参数更清晰易读
