# Query Agent 使用文档

## 快速开始

### 1. 基础使用

```python
from app.services.query_agent import QueryAgent

# 创建 Agent
agent = QueryAgent()

# 执行查询
result = agent.run(
    query="查找深圳南山区的星巴克门店",
    curl="""
    curl -X POST 'https://api.example.com/stores/search' \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer YOUR_TOKEN' \
    -d '{
        "keyword": "{{keyword}}",
        "city": "{{city}}",
        "district": "{{district}}"
    }'
    """,
    system_prompt="""
    查询目标是找到符合用户需求的门店。
    匹配标准：
    1. 门店名称或品牌应与用户查询的关键词匹配
    2. 城市应与用户指定的城市一致
    3. 区域（如果有指定）应与用户指定的区域一致
    """
)

if result.success:
    print(f"找到结果: {result.data}")
else:
    print(f"未找到满意结果，尝试了 {result.attempts} 次")
```

### 2. 使用自定义参数

```python
result = agent.run(
    query="查找2024年1月在上海举办的技术会议",
    curl="""
    curl -X POST 'https://api.example.com/events/search' \
    -H 'Content-Type: application/json' \
    -d '{
        "keyword": "{{keyword}}",
        "city": "{{city}}",
        "start_date": "{{start_date}}",
        "end_date": "{{end_date}}",
        "category": "{{category}}"
    }'
    """,
    system_prompt="查找会议活动信息",
    max_attempts=3,                    # 最多尝试3次
    timeout=60,                        # HTTP 超时60秒
    llm_model="gpt-4o-mini",           # 使用轻量级模型
    llm_temperature=0.2,               # 稍微增加一点创造性
    return_raw_response=True,          # 返回原始响应
    result_selector="data.items"       # 提取 data.items 字段
)
```

### 3. 使用输入对象

```python
from app.services.query_agent import QueryAgent, QueryAgentInput

agent = QueryAgent()

input_data = QueryAgentInput(
    query="查找北京朝阳区的餐厅",
    curl="curl ...",
    system_prompt="查找餐厅信息",
    max_attempts=5,
    timeout=30,
    result_selector="data.list"
)

result = agent.run_with_input(input_data)
```

## Curl 模板规范

### 占位符格式

使用 `{{field_name}}` 格式定义可搜索字段：

```bash
curl -X POST 'https://api.example.com/search' \
-H 'Content-Type: application/json' \
-d '{
    "keyword": "{{keyword}}",
    "city": "{{city}}",
    "category": "{{category}}",
    "start_date": "{{start_date}}",
    "end_date": "{{end_date}}"
}'
```

### 支持的字段类型

- `{{keyword}}` - 通用搜索关键词
- `{{city}}` - 城市名称
- `{{district}}` - 区域/区县
- `{{category}}` - 分类/类型
- `{{start_date}}` / `{{end_date}}` - 日期范围
- `{{status}}` - 状态
- 其他自定义字段

## 配置参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | str | 必填 | 用户查询语句 |
| `curl` | str | 必填 | curl 请求模板 |
| `system_prompt` | str | 必填 | 系统提示词，定义查询目标 |
| `max_attempts` | int | 5 | 最大搜索尝试次数 |
| `timeout` | int | 30 | HTTP 请求超时时间（秒） |
| `llm_model` | str | "gpt-4o" | LLM 模型名称 |
| `llm_temperature` | float | 0.0 | LLM 温度参数（0-2） |
| `return_raw_response` | bool | False | 是否返回原始接口响应 |
| `result_selector` | str | None | 结果选择器（JSONPath 或点号路径） |

## 返回结果结构

```python
class QueryAgentOutput:
    success: bool              # 是否找到满意结果
    data: Any                  # 最终选中的数据（与原接口结构一致）
    raw_response: Dict         # 原始接口完整响应（可选）
    attempts: int              # 实际尝试次数
    history: List[SearchAttempt]  # 搜索历史记录
    reasoning: str             # 结果选择的推理说明
    final_parameters: Dict     # 最终使用的搜索参数
    is_satisfied: bool         # 是否满足查询条件
```

## 结果选择器

使用 `result_selector` 提取特定字段：

### 点号路径
```python
# 提取 data.items
result_selector="data.items"

# 提取嵌套字段
result_selector="data.user.name"

# 提取数组元素
result_selector="data.items.0"
```

### JSONPath
```python
# 提取数组第一个元素
result_selector="$.data.items[0]"

# 提取所有匹配项
result_selector="$.data.items[*].name"
```

## 完整示例

```python
from app.services.query_agent import QueryAgent

agent = QueryAgent()

# 场景：查找门店信息
result = agent.run(
    query="帮我找深圳南山区的 Apple Store",
    curl="""
    curl -X POST 'https://api.example.com/v1/stores/search' \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer xxx' \
    -d '{
        "keyword": "{{keyword}}",
        "city": "{{city}}",
        "district": "{{district}}",
        "pageSize": 20
    }'
    """,
    system_prompt="""
    查询目标是找到符合用户需求的门店。

    匹配标准：
    1. 门店名称或品牌应与用户查询的关键词匹配（如 "Apple Store"、"苹果"）
    2. 城市应与用户指定的城市一致
    3. 区域（如果有指定）应与用户指定的区域一致
    4. 优先返回最匹配的一条记录

    如果找不到完全匹配的，可以返回部分匹配的结果。
    """,
    max_attempts=3,
    timeout=30,
    return_raw_response=True,
    result_selector="data.items"
)

print(f"查询成功: {result.success}")
print(f"尝试次数: {result.attempts}")
print(f"推理: {result.reasoning}")

if result.success:
    print(f"找到 {len(result.data)} 条记录")
    for item in result.data:
        print(f"  - {item['name']}: {item['address']}")

    # 访问原始响应
    if result.raw_response:
        print(f"总记录数: {result.raw_response.get('total', 0)}")
```

## 错误处理

```python
from app.services.query_agent import CurlParseError, QueryAgentError

try:
    result = agent.run(
        query="测试查询",
        curl="invalid curl command",
        system_prompt="测试"
    )
except CurlParseError as e:
    print(f"Curl 解析错误: {e}")
except QueryAgentError as e:
    print(f"Agent 错误: {e}")
except Exception as e:
    print(f"其他错误: {e}")
```

## 依赖安装

```bash
# 安装 curl-session 库（curl 解析和 HTTP 请求）
pip install curl-session

# 可选：安装 jsonpath-ng（用于 JSONPath 选择器）
pip install jsonpath-ng

# 可选：安装 httpx（curl-session 依赖）
pip install httpx
```

## 技术实现

### Curl 解析

Query Agent 使用 [curl-session](https://pypi.org/project/curl-session/) 库来解析 curl 命令：

- 自动提取 URL、Method、Headers、Body 等信息
- 支持复杂的 curl 命令（包括 cookies、auth、proxies 等）
- 使用 `httpx` 作为底层 HTTP 客户端

### 占位符处理

- 使用正则表达式 `\{\{(\w+)\}\}` 提取占位符字段
- 支持递归替换嵌套数据结构中的占位符
- 未匹配的占位符保留原样

### HTTP 请求执行

1. 使用 curl-session 解析 curl 模板
2. 替换模板中的占位符为实际参数
3. 使用 curl-session 创建 `httpx.Client` 会话
4. 发送 HTTP 请求并获取响应

## 注意事项

1. **Curl 格式**：curl 命令必须以 `curl` 开头，不能有空格
2. **占位符**：使用 `{{field}}` 格式，Agent 会自动提取并填充
3. **API Key**：确保设置了 `OPENAI_API_KEY` 环境变量
4. **超时设置**：根据目标接口的响应速度调整 `timeout` 参数
5. **成本控制**：可以通过 `max_attempts` 和 `llm_model` 控制成本
6. **Curl 命令**：curl-session 支持大部分常用 curl 选项（headers、data、cookies、auth 等）
