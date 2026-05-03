# Agent 模拟客服查询经销商测试文档

## 场景说明

模拟 400 客服场景，用户通过自然语言询问经销商信息，Agent 需要：
1. 从聊天记录中识别查询意图
2. 提取查询参数（name、city、address）
3. 调用经销商搜索接口
4. 验证结果是否匹配用户需求
5. 如不匹配，自动调整参数重新查询

---

## 模拟客服聊天记录

### 场景 1：用户询问重庆地区的门店

```
用户: 你好，我想问一下重庆有没有比亚迪的4S店？
客服: 您好，重庆有多家比亚迪门店，请问您在重庆哪个区呢？
用户: 我在沙坪坝区，想看看海洋网系列的
客服: 好的，我帮您查询一下重庆沙坪坝区的海洋网门店...
```

**Agent 识别结果**:
- 城市: 重庆
- 地址: 沙坪坝
- 门店名称关键词: 海洋网

---

### 场景 2：用户询问特定街道的门店

```
用户: 我想找一家在海珠区的比亚迪店
客服: 您好，广州海珠区有比亚迪门店，您是想看王朝网还是海洋网呢？
用户: 都可以，只要有现车就行
客服: 好的，我帮您查询广州海珠区的比亚迪门店...
```

**Agent 识别结果**:
- 城市: 广州
- 地址: 海珠

---

### 场景 3：用户只知道门店名称的一部分

```
用户: 我记得有家叫王朝网的店，在哪个城市来着？
客服: 比亚迪王朝网多个城市都有，您记得大概位置吗？
用户: 好像在南方，挺热的城市
客服: 可能是广州或厦门，我帮您查询一下...
```

**Agent 识别结果**:
- 门店名称关键词: 王朝网
- 可能城市: 广州、厦门（需要多次查询验证）

---

## Agent 接口调用

### 接口信息

- **URL**: `POST /api/v1/agent/query`
- **认证方式**: API Key (Header: `Authorization: Bearer {api_key}`)
- **Content-Type**: `application/json`

### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 用户查询语句（聊天记录） |
| curl | string | 是 | 经销商搜索接口的 curl 命令 |
| system_prompt | string | 否 | 指导 Agent 如何提取参数 |
| expected_result | string | 否 | 期望结果描述 |
| max_attempts | integer | 否 | 最大尝试次数，默认 5 |
| timeout | integer | 否 | 超时时间，默认 30 秒 |

---

## 测试用例

### 测试 1：查询重庆沙坪坝海洋网门店

```bash
curl -X POST "http://localhost:9999/api/v1/agent/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -d '{
    "query": "用户: 你好，我想问一下重庆有没有比亚迪的4S店？\n客服: 您好，重庆有多家比亚迪门店，请问您在重庆哪个区呢？\n用户: 我在沙坪坝区，想看看海洋网系列的\n客服: 好的，我帮您查询一下重庆沙坪坝区的海洋网门店...",
    "curl": "curl -X POST '"'"'http://localhost:9999/api/byd-dealers/search'"'"' -H '"'"'Content-Type: application/json'"'"' -H '"'"'Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR'"'"' -d '"'"'{\"app_key\": \"af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR\", \"name\": \"\", \"city\": \"\", \"address\": \"\", \"limit\": 10}'"'"'",
    "system_prompt": "从客服与用户的对话记录中提取经销商查询参数。需要识别：1) 城市名称（如重庆、广州等）；2) 区域/地址关键词（如沙坪坝、海珠等）；3) 门店名称关键词（如海洋网、王朝网等）。将提取的参数填充到 curl 的 name、city、address 字段中。如果某个参数未提及，保留为空字符串。",
    "expected_result": "返回匹配用户需求的比亚迪经销商门店列表，包含门店名称、地址、电话等信息",
    "max_attempts": 3,
    "timeout": 30
  }'
```

**预期执行流程**:
1. Agent 分析聊天记录，识别出：城市=重庆，地址=沙坪坝，名称=海洋网
2. 填充 curl 参数：`"name": "海洋网", "city": "重庆", "address": "沙坪坝"`
3. 调用经销商搜索接口
4. 验证返回结果是否包含"重庆沙坪坝区的海洋网门店"
5. 如果匹配，返回成功；如果不匹配，调整参数重试

---

### 测试 2：查询广州海珠区门店

```bash
curl -X POST "http://localhost:9999/api/v1/agent/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -d '{
    "query": "用户: 我想找一家在海珠区的比亚迪店\n客服: 您好，广州海珠区有比亚迪门店，您是想看王朝网还是海洋网呢？\n用户: 都可以，只要有现车就行\n客服: 好的，我帮您查询广州海珠区的比亚迪门店...",
    "curl": "curl -X POST '"'"'http://localhost:9999/api/byd-dealers/search'"'"' -H '"'"'Content-Type: application/json'"'"' -H '"'"'Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR'"'"' -d '"'"'{\"app_key\": \"af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR\", \"name\": \"\", \"city\": \"\", \"address\": \"\", \"limit\": 10}'"'"'",
    "system_prompt": "从客服与用户的对话记录中提取经销商查询参数。需要识别：1) 城市名称；2) 区域/地址关键词；3) 门店名称关键词。将提取的参数填充到 curl 的 name、city、address 字段中。",
    "expected_result": "返回广州海珠区的比亚迪经销商门店",
    "max_attempts": 3
  }'
```

---

### 测试 3：模糊查询（只知道门店名称）

```bash
curl -X POST "http://localhost:9999/api/v1/agent/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -d '{
    "query": "用户: 我记得有家叫王朝网的店，在哪个城市来着？\n客服: 比亚迪王朝网多个城市都有，您记得大概位置吗？\n用户: 好像在南方，挺热的城市\n客服: 可能是广州或厦门，我帮您查询一下...",
    "curl": "curl -X POST '"'"'http://localhost:9999/api/byd-dealers/search'"'"' -H '"'"'Content-Type: application/json'"'"' -H '"'"'Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR'"'"' -d '"'"'{\"app_key\": \"af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR\", \"name\": \"\", \"city\": \"\", \"address\": \"\", \"limit\": 10}'"'"'",
    "system_prompt": "从对话中提取查询参数。用户只记得门店名称包含'王朝网'，不确定城市。先按名称查询所有王朝网门店，如果结果太多，根据'南方、热'的线索，优先尝试广州、厦门等城市。需要多次尝试直到找到用户记忆中的门店。",
    "expected_result": "返回用户记忆中的王朝网门店信息",
    "max_attempts": 5
  }'
```

**预期执行流程**:
1. 第一次尝试：只传 name="王朝网"，查询所有王朝网门店
2. 如果结果太多，第二次尝试：name="王朝网", city="广州"
3. 如果未找到，第三次尝试：name="王朝网", city="厦门"
4. 直到找到匹配结果或达到最大尝试次数

---

## 预期响应

### 成功响应示例

```json
{
  "success": true,
  "status": "completed",
  "data": {
    "dealers": [
      {
        "id": 6,
        "name": "比亚迪重庆海洋网2号店",
        "city": "重庆",
        "district": "沙坪坝区",
        "address": "重庆市重庆沙坪坝区新华路689号",
        "phone": "023-12345678",
        "dealer_type": "旗舰店"
      }
    ],
    "search_params": {
      "name": "海洋网",
      "city": "重庆",
      "address": "沙坪坝"
    },
    "matched_keywords": ["海洋网", "重庆", "沙坪坝"]
  },
  "total_attempts": 1,
  "execution_time_ms": 1250
}
```

### 多次尝试后成功

```json
{
  "success": true,
  "status": "completed_after_retry",
  "data": {
    "dealers": [...],
    "attempts_history": [
      {"attempt": 1, "params": {"name": "王朝网"}, "result_count": 5},
      {"attempt": 2, "params": {"name": "王朝网", "city": "广州"}, "result_count": 1}
    ]
  },
  "total_attempts": 2,
  "execution_time_ms": 2800
}
```

### 失败响应

```json
{
  "success": false,
  "status": "failed",
  "error": "未找到匹配的经销商门店",
  "data": null,
  "total_attempts": 3,
  "execution_time_ms": 4500
}
```

---

## 数据库测试数据参考

| 门店名称 | 城市 | 区县 | 地址 | 类型 |
|---------|------|------|------|------|
| 比亚迪重庆服务中心 | 重庆 | 渝北区 | 重庆市重庆渝北区中山大道252号 | 专营店 |
| 比亚迪重庆海洋网2号店 | 重庆 | 沙坪坝区 | 重庆市重庆沙坪坝区新华路689号 | 旗舰店 |
| 比亚迪广州王朝网 | 广州 | 海珠区 | 广东省广州海珠区人民街365号 | 专营店 |
| 比亚迪青岛服务中心 | 青岛 | 崂山区 | 山东省青岛崂山区新华路71号 | 体验中心 |
| 比亚迪厦门4S店 | 厦门 | 同安区 | 福建省厦门同安区解放中路645号 | 城市展厅 |
| 比亚迪哈尔滨服务中心 | 哈尔滨 | 平房区 | 黑龙江省哈尔滨平房区中山街264号 | 体验中心 |

---

## 测试脚本

### Python 测试脚本

```python
import requests
import json

API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
BASE_URL = "http://localhost:9999"

def test_agent_query():
    """测试 Agent 查询经销商"""
    
    # 模拟客服聊天记录
    chat_history = """用户: 你好，我想问一下重庆有没有比亚迪的4S店？
客服: 您好，重庆有多家比亚迪门店，请问您在重庆哪个区呢？
用户: 我在沙坪坝区，想看看海洋网系列的
客服: 好的，我帮您查询一下重庆沙坪坝区的海洋网门店..."""
    
    # curl 模板（参数留空，由 Agent 填充）
    curl_template = f"""curl -X POST 'http://localhost:9999/api/byd-dealers/search' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer {API_KEY}' \
  -d '{{"app_key": "{API_KEY}", "name": "", "city": "", "address": "", "limit": 10}}'"""
    
    payload = {
        "query": chat_history,
        "curl": curl_template,
        "system_prompt": "从客服与用户的对话记录中提取经销商查询参数。需要识别：1) 城市名称；2) 区域/地址关键词；3) 门店名称关键词。将提取的参数填充到 curl 的 name、city、address 字段中。",
        "expected_result": "返回匹配用户需求的比亚迪经销商门店列表",
        "max_attempts": 3,
        "timeout": 30
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/agent/query",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        },
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    test_agent_query()
```

---

## 更新记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-05-02 | v1.0 | 创建 Agent 模拟客服查询经销商测试文档 |
