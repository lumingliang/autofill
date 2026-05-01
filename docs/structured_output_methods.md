# LangChain 结构化输出方法对比与动态优先级方案

本文档介绍 LangChain 提供的几种结构化输出方法，以及系统的动态优先级管理方案。

## 方法概述

### 1. `with_structured_output()`

**原理：**

- 使用 OpenAI 的 Function Calling API
- 将 Pydantic 模型转换为 OpenAI 工具格式
- 调用模型时传入 `tools` 参数，模型返回 `tool_calls`
- 自动解析 `tool_calls` 中的参数并验证

**底层流程：**

```
Pydantic Model -> OpenAI Tool Schema -> API Call (tools) -> Parse tool_calls -> Validate
```

**优点：**

- 最可靠的结构化输出方式
- 模型明确知道需要调用函数
- 支持 `strict=True` 强制约束
- 错误处理完善

**缺点：**

- 需要模型和 API 支持 Function Calling
- 魔搭社区等部分 API 非流式调用返回 null
- 不支持流式输出

**适用场景：**

- 标准 OpenAI API
- 完全兼容 OpenAI 的第三方 API

***

### 2. `bind_tools()` + 流式收集

**原理：**

- 使用 `bind_tools()` 绑定工具定义
- 通过流式输出收集 `tool_calls`
- 手动组装分段返回的参数

**底层流程：**

```
Tool Schema -> bind_tools -> Stream -> Collect tool_calls chunks -> Assemble -> Parse -> Validate
```

**优点：**

- 支持流式输出
- 利用模型的 Function Calling 能力
- 比纯文本生成更可靠

**缺点：**

- 实现复杂，需要手动处理流式 chunks
- 参数可能分段返回，需要组装
- 部分模型（如 QwQ-32B）不支持 `tool_choice`

**适用场景：**

- 需要流式输出的同时利用 FC 能力
- API 支持流式工具调用

***

### 3. `custom_fc_non_stream` (自定义 FC 非流式)

**原理：**

- 手动构造 Function Calling 格式的请求
- 非流式调用 API
- 解析响应中的 `tool_calls`

**底层流程：**

```
Pydantic Model -> Tool Schema -> Manual API Call -> Parse tool_calls -> Validate
```

**优点：**

- 更灵活的控制
- 可以处理特殊的 API 格式
- 支持自定义错误处理和重试

**缺点：**

- 实现复杂
- 需要手动处理各种边界情况

**适用场景：**

- 标准方法不支持的 API
- 需要特殊处理的模型

***

### 4. `custom_fc_stream` (自定义 FC 流式)

**原理：**

- 手动构造 Function Calling 格式的请求
- 流式调用 API
- 流式解析响应中的 `tool_calls`

**底层流程：**

```
Pydantic Model -> Tool Schema -> Manual Stream API Call -> Parse tool_calls chunks -> Assemble -> Validate
```

**优点：**

- 更灵活的控制
- 可以处理特殊的 API 格式
- 支持流式响应

**缺点：**

- 实现复杂
- 需要手动处理各种边界情况

**适用场景：**

- 标准方法不支持的 API
- 需要特殊处理的模型
- API 只支持流式输出

***

### 5. `PydanticOutputParser`

**原理：**

- 在 Prompt 中插入格式说明（通过 `get_format_instructions()`）
- 模型根据说明生成 JSON 格式的文本
- 使用 Pydantic 模型验证和解析输出

**底层流程：**

```
Pydantic Model -> Format Instructions -> Prompt -> Model -> JSON Text -> Parse -> Validate
```

**优点：**

- 通用性强，支持所有模型
- 支持流式输出
- 不依赖特定的 API 功能
- 提示模板自动生成

**缺点：**

- 依赖模型的指令遵循能力
- 可能出现格式不严格的情况
- 需要处理 markdown 代码块等额外格式

**适用场景：**

- 通用场景，特别是 API 限制较多的情况
- 魔搭社区等只支持流式输出的 API

***

### 6. `JsonOutputParser`

**原理：**

- 与 `PydanticOutputParser` 类似，但只返回字典
- 不强制验证字段类型
- 支持部分解析（partial parsing）

**底层流程：**

```
Pydantic Model -> Format Instructions -> Prompt -> Model -> JSON Text -> Parse
```

**优点：**

- 更灵活，容错性更强
- 支持流式输出
- 可以处理不完整的 JSON

**缺点：**

- 没有严格的类型验证
- 可能返回不符合预期的字段

**适用场景：**

- 需要灵活解析的场景
- 字段可能不固定的动态 schema

***

## 方法对比表

| 特性            | with\_structured\_output | bind\_tools + Stream | custom\_fc\_non\_stream | custom\_fc\_stream | PydanticOutputParser | JsonOutputParser |
| ------------- | ------------------------ | -------------------- | ----------------------- | ------------------ | -------------------- | ---------------- |
| **依赖 API 功能** | Function Calling         | Function Calling     | Function Calling        | Function Calling   | 无                    | 无                |
| **支持流式**      | ❌                        | ✅                    | ❌                       | ✅                  | ✅                    | ✅                |
| **类型验证**      | ✅ 严格                     | ✅ 手动                 | ✅ 手动                    | ✅ 手动               | ✅ 严格                 | ❌ 宽松             |
| **实现复杂度**     | 低                        | 高                    | 高                       | 高                  | 低                    | 低                |
| **可靠性**       | ⭐⭐⭐⭐⭐                    | ⭐⭐⭐⭐                 | ⭐⭐⭐⭐                    | ⭐⭐⭐⭐               | ⭐⭐⭐⭐                 | ⭐⭐⭐              |
| **通用性**       | ⭐⭐⭐                      | ⭐⭐⭐⭐                 | ⭐⭐⭐⭐                    | ⭐⭐⭐⭐               | ⭐⭐⭐⭐⭐                | ⭐⭐⭐⭐⭐            |
| **魔搭社区支持**    | ❌                        | ⚠️ 部分支持              | ⚠️ 部分支持                 | ✅                  | ✅                    | ✅                |

***

## 动态优先级管理方案

### 全局优先级（从高到低）

```
with_structured_output > bind_tools_stream > custom_fc_non_stream > custom_fc_stream > pydantic_parser > json_parser
```

### 数据库设计

使用 JSON 字段 `model_capabilities` 存储模型能力配置：

```json
{
  "structured_output_methods": {
    "with_structured_output": {"supported": true, "failed_count": 0},
    "bind_tools_stream": {"supported": true, "failed_count": 0},
    "custom_fc_non_stream": {"supported": true, "failed_count": 0},
    "custom_fc_stream": {"supported": true, "failed_count": 0},
    "pydantic_parser": {"supported": true, "failed_count": 0},
    "json_parser": {"supported": true, "failed_count": 0}
  }
}
```

### 动态调整机制

系统通过以下机制动态管理方法优先级：

#### 1. 方法支持状态跟踪

每个 LLM 配置在数据库中使用 JSON 字段维护方法状态：

```sql
-- 模型能力配置（JSON 格式）
model_capabilities JSON
```

#### 2. 自动降级逻辑

当某个方法失败时：

1. **增加失败计数**：`failed_count += 1`
2. **检查阈值**：如果 `failed_count >= 3`，标记为不支持
3. **更新数据库**：保存新的支持状态和失败计数到 JSON 字段
4. **下次调用**：自动跳过标记为不支持的方法

#### 3. 动态优先级计算

```python
# 获取支持的方法列表
supported_methods = [
    method for method in GLOBAL_PRIORITY
    if get_method_info(config, method)["supported"] == True
]

# 如果请求方指定了优先级，按指定顺序过滤
if preferred_methods:
    result = [
        method for method in preferred_methods
        if method in supported_methods
    ]
else:
    # 使用全局优先级
    result = supported_methods
```

### 降级流程示例

**场景：QwQ-32B 模型首次调用**

```
初始状态：所有方法都标记为支持

第1次调用：
  尝试 with_structured_output → 失败（API 返回 null）
  记录失败：failed_count = 1
  降级到 bind_tools_stream → 失败（不支持 tool_choice）
  记录失败：failed_count = 1
  降级到 custom_fc_non_stream → 失败
  记录失败：failed_count = 1
  降级到 custom_fc_stream → 失败
  记录失败：failed_count = 1
  降级到 pydantic_parser → 成功 ✓
  返回结果

第2次调用：
  尝试 with_structured_output → 失败
  记录失败：failed_count = 2
  降级到 bind_tools_stream → 失败
  记录失败：failed_count = 2
  降级到 custom_fc_non_stream → 失败
  记录失败：failed_count = 2
  降级到 custom_fc_stream → 失败
  记录失败：failed_count = 2
  降级到 pydantic_parser → 成功 ✓

第3次调用：
  尝试 with_structured_output → 失败
  记录失败：failed_count = 3 ≥ 阈值
  标记为不支持：supported = False
  降级到 bind_tools_stream → 失败
  记录失败：failed_count = 3 ≥ 阈值
  标记为不支持：supported = False
  降级到 custom_fc_non_stream → 失败
  记录失败：failed_count = 3 ≥ 阈值
  标记为不支持：supported = False
  降级到 custom_fc_stream → 失败
  记录失败：failed_count = 3 ≥ 阈值
  标记为不支持：supported = False
  降级到 pydantic_parser → 成功 ✓

第4次及以后调用：
  跳过 with_structured_output、bind_tools_stream、custom_fc_non_stream、custom_fc_stream
  直接使用 pydantic_parser → 成功 ✓
```

***

## API 使用说明

### 请求参数

```json
{
  "query": "用户输入文本",
  "function_schema": {...},
  "app_key": "your_api_key",
  "context": "可选的上下文",
  "preferred_methods": ["pydantic_parser", "json_parser"]  // 可选，指定优先级
}
```

### 响应结果

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "result": {
      "customer_name": "张三",
      "vehicle_model": "2024款极越01",
      "issue": "充电到80%就停了"
    },
    "method_used": "pydantic_parser",
    "model": "Qwen/QwQ-32B"
  }
}
```

### 指定方法优先级

请求方可以通过 `preferred_methods` 参数指定优先级：

```json
{
  "query": "...",
  "function_schema": {...},
  "preferred_methods": [
    "with_structured_output",
    "pydantic_parser",
    "json_parser"
  ]
}
```

系统会：

1. 按指定顺序尝试方法
2. 跳过标记为不支持的方法
3. 记录失败并自动降级

***

## 管理接口

### 获取模型方法状态

```python
from app.services.llm_method_priority_manager import method_priority_manager

status = method_priority_manager.get_method_status(config)
print(status)
# {
#   "model_name": "Qwen/QwQ-32B",
#   "methods": {
#     "with_structured_output": {"supported": false, "failed_count": 3},
#     "bind_tools_stream": {"supported": false, "failed_count": 3},
#     "custom_fc_non_stream": {"supported": false, "failed_count": 3},
#     "custom_fc_stream": {"supported": false, "failed_count": 3},
#     "pydantic_parser": {"supported": true, "failed_count": 0},
#     "json_parser": {"supported": true, "failed_count": 0}
#   }
# }
```

### 重置方法状态

```python
# 重置所有方法
await method_priority_manager.reset_method_status(config)

# 重置特定方法
from app.services.llm_method_priority_manager import StructuredOutputMethod
await method_priority_manager.reset_method_status(
    config,
    method=StructuredOutputMethod.WITH_STRUCTURED_OUTPUT
)
```

***

## 配置建议

### 新模型初始化

新创建的模型配置默认所有方法都支持。系统会在实际调用过程中自动检测并调整。

### 手动配置

对于已知不支持某些方法的模型，可以在数据库中直接设置：

```sql
-- QwQ-32B 已知不支持 with_structured_output
UPDATE llm_config
SET model_capabilities = JSON_SET(
    model_capabilities,
    '$.structured_output_methods.with_structured_output.supported',
    false
)
WHERE model_name = 'Qwen/QwQ-32B';
```

### 阈值调整

默认失败阈值为 3 次，可以通过修改代码调整：

```python
# app/services/llm_method_priority_manager.py
FAILED_THRESHOLD = 3  # 修改此值
```

***

## 最佳实践

1. **首次使用新模型**：不指定 `preferred_methods`，让系统自动检测
2. **已知模型**：可以在数据库中预设不支持的方法，避免不必要的尝试
3. **监控**：定期检查日志，了解各模型的方法支持情况
4. **重置**：如果模型 API 升级支持了新功能，手动重置方法状态

