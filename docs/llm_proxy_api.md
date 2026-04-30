# LLM 代理接口文档

## 概述

基于 **LiteLLM 网关 + LangChain** 的代理接口架构。

### 架构设计

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   调用方        │────▶│   后端服务        │────▶│  LiteLLM 网关   │
│  (传 appkey)   │     │  (LangChain)     │     │  (统一模型网关)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌──────────────┐          ┌──────────────┐
                        │    MySQL     │          │  各模型提供商 │
                        │  LLM配置管理  │          │ OpenAI/Azure │
                        └──────────────┘          │ Anthropic等  │
                                                  └──────────────┘
```

### 组件职责

| 组件 | 职责 |
|------|------|
| **LiteLLM 网关** | 独立服务，统一管理所有模型调用，提供 OpenAI 兼容接口 |
| **后端服务** | 管理模型配置、租户隔离、调用 LiteLLM 网关、结构化输出处理 |
| **MySQL** | 存储模型配置、租户信息、应用配置 |

### 调用流程

```
调用方（传 appkey）
    ↓
后端服务：验证 appkey → 查询租户配置 → 获取模型配置
    ↓
后端服务：LangChain 结构化输出处理
    ↓
后端服务：调用 LiteLLM 网关（OpenAI 兼容接口）
    ↓
LiteLLM 网关：路由到具体模型提供商
    ↓
返回结构化 JSON
```

## 配置管理

### 后端服务配置（config.toml）

后端服务通过 `config.toml` 配置 LiteLLM 网关连接和结构化输出参数：

```toml
[litellm]
# LiteLLM 网关地址
base_url = "http://localhost:4000"
# LiteLLM 网关 API Key（用于管理接口）
master_key = "sk-litellm-master-key"
# 默认超时时间（秒）
timeout = 60

[structured_output]
# 方法失败阈值，达到此值后自动标记为不支持
failed_threshold = 2
# 是否自动更新模型能力状态
auto_update_capabilities = true
# 默认方法优先级（可被请求参数覆盖）
default_method_priority = [
    "with_structured_output",
    "bind_tools_stream",
    "custom_fc_non_stream",
    "custom_fc_stream",
    "pydantic_parser",
    "json_parser"
]
# 是否启用方法降级
enable_fallback = true
# 最大尝试方法数（防止无限循环）
max_attempt_methods = 6
```

**配置项说明**:

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `litellm.base_url` | string | - | LiteLLM 网关服务地址 |
| `litellm.master_key` | string | - | LiteLLM 管理接口密钥 |
| `litellm.timeout` | int | 60 | 调用 LiteLLM 的超时时间（秒）|
| `structured_output.failed_threshold` | int | 2 | 方法失败次数阈值，超过则标记为不支持 |
| `structured_output.auto_update_capabilities` | bool | true | 是否自动更新模型能力状态 |
| `structured_output.default_method_priority` | array | 见上 | 默认方法优先级列表 |
| `structured_output.enable_fallback` | bool | true | 是否启用自动降级 |
| `structured_output.max_attempt_methods` | int | 6 | 最大尝试方法数 |

### 模型配置数据结构

后端服务管理的模型配置存储在 MySQL 中，与 LiteLLM 的 `litellm_params` 对齐：

```json
{
  "model_name": "gpt-4",           // 对外显示名称
  "litellm_params": {
    "model": "openai/gpt-4",       // LiteLLM 格式：provider/model
    "api_key": "sk-xxx",           // 模型提供商 API Key
    "api_base": "https://api.openai.com/v1",  // 可选，自定义 base_url
    "timeout": 60,                 // 超时时间（秒）
    "stream_timeout": 300,         // 流式超时（秒）
    "max_retries": 3,              // 最大重试次数
    "retry_strategy": "exponential_backoff",
    "organization": "org-xxx",     // OpenAI 组织 ID
    "headers": {                   // 自定义请求头
      "X-Custom-Header": "value"
    },
    "rpm_limit": 60,               // 每分钟请求限制
    "tpm_limit": 100000,           // 每分钟 token 限制
    "cooldown_time": 30,           // 失败后冷却时间（秒）
    "region_name": "us-east-1",    // AWS/GCP 区域
    "vertex_project": "project-id", // Vertex AI 项目
    "vertex_location": "us-central1"
  },
  "model_info": {
    "id": "gpt-4-001",
    "mode": "chat",                // chat/completion/embedding/image
    "input_cost_per_token": 0.00003,
    "output_cost_per_token": 0.00006,
    "max_tokens": 8192,
    "supports_function_calling": true,
    "supports_vision": false,
    "supports_response_schema": true
  },
  "capabilities": {                // 结构化输出方法支持状态（JSON字段）
    "structured_output_methods": {
      "with_structured_output": {
        "supported": true,         // 是否支持该方法
        "failed_count": 0,         // 失败次数计数
        "last_error": null,        // 最后一次错误信息
        "last_attempt": null       // 最后尝试时间
      },
      "bind_tools_stream": {
        "supported": true,
        "failed_count": 0,
        "last_error": null,
        "last_attempt": null
      },
      "custom_fc_non_stream": {
        "supported": true,
        "failed_count": 0,
        "last_error": null,
        "last_attempt": null
      },
      "custom_fc_stream": {
        "supported": true,
        "failed_count": 0,
        "last_error": null,
        "last_attempt": null
      },
      "pydantic_parser": {
        "supported": true,
        "failed_count": 0,
        "last_error": null,
        "last_attempt": null
      },
      "json_parser": {
        "supported": true,
        "failed_count": 0,
        "last_error": null,
        "last_attempt": null
      }
    }
  },
  "tenant_id": 1,                  // 租户隔离
  "app_name": "customer-service",  // 应用名称
  "is_active": true,
  "is_default": false
}
```

**capabilities 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `structured_output_methods` | object | 结构化输出方法支持状态集合 |
| `*.supported` | boolean | 该方法是否被标记为支持 |
| `*.failed_count` | int | 该方法连续失败次数 |
| `*.last_error` | string/null | 最后一次失败的错误信息 |
| `*.last_attempt` | string/null | 最后尝试时间（ISO 8601格式）|

**初始化规则**:
- 新创建的模型配置，`capabilities` 中所有方法的 `supported` 默认为 `true`
- 失败阈值在 TOML 配置中设置，默认 `failed_threshold = 2`
- 当 `failed_count >= failed_threshold` 时，自动设置 `supported = false`

## 公开接口（API Key认证）

### 1. LLM结构化输出代理接口

**接口地址**: `POST /api/llm/proxy`

**认证方式**: `Authorization: Bearer {api_key}`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 用户输入或上下文 |
| function_schema | object | 是 | 函数调用参数schema（OpenAI Function Calling格式） |
| context | string | 否 | 额外上下文信息 |
| preferred_methods | array | 否 | 结构化输出方法优先级列表 |

**结构化输出方法**:

| 优先级 | 方法标识 | 来源 | 原理 | 优点 | 缺点 | 适用场景 |
|--------|----------|------|------|------|------|----------|
| 1 | `with_structured_output` | LangChain 官方 | 调用模型原生 Function Calling API | 最可靠，利用模型原生FC能力 | 需要API支持FC，部分模型不支持 | GPT-4、Claude、DeepSeek等标准模型 |
| 2 | `bind_tools_stream` | LangChain 官方 | bind_tools + 流式收集 tool_calls | 支持流式，利用模型FC能力 | 实现复杂，需手动组装 | 支持FC但需要流式处理的场景 |
| 3 | `custom_fc_non_stream` | 自定义实现 | 直接调用 LiteLLM/OpenAI API，手动解析 tool_calls | 兼容性好，绕过LangChain解析问题 | 非标准实现，维护成本高 | 部分支持FC但LangChain适配不佳的模型（如QwQ-32B） |
| 4 | `custom_fc_stream` | 自定义实现 | 流式调用 API，手动组装 tool_calls | 流式输出，绕过LangChain解析问题 | 实现复杂，非标准 | 需要流式且LangChain适配不佳的模型 |
| 5 | `pydantic_parser` | LangChain 官方 | Prompt + PydanticOutputParser 解析 | 通用性最强，支持所有模型 | 依赖模型指令遵循能力 | 通用兜底方案，推荐优先使用 |
| 6 | `json_parser` | LangChain 官方 | Prompt + JsonOutputParser 解析 | 最灵活，容错性最强 | 无严格类型验证 | 最终兜底方案 |

**方法来源说明**:

- **LangChain 官方方法**: `with_structured_output`、`bind_tools_stream`、`pydantic_parser`、`json_parser` 均为 LangChain 框架内置方法
- **自定义实现方法**: `custom_fc_non_stream`、`custom_fc_stream` 为项目自定义实现，直接调用 LiteLLM/OpenAI API，手动处理 tool_calls 解析，用于解决部分模型与 LangChain 适配不佳的问题

**自动方法选择逻辑**:

```
调用代理接口
    ↓
读取模型的 capabilities 字段
    ↓
按优先级顺序检查方法支持状态:
    1. with_structured_output (supported=true?) → 尝试 → 成功返回 / 失败计数+1
    2. bind_tools_stream (supported=true?) → 尝试 → 成功返回 / 失败计数+1
    3. custom_fc_non_stream → 尝试 → 成功返回 / 失败计数+1
    4. custom_fc_stream → 尝试 → 成功返回 / 失败计数+1
    5. pydantic_parser → 尝试 → 成功返回 / 失败计数+1
    6. json_parser → 尝试 → 成功返回 / 失败计数+1
    ↓
所有方法都失败 → 返回错误
```

**失败阈值机制**:
- 每个方法独立维护 `failed_count` 计数器
- 当 `failed_count >= threshold`（在 TOML 配置中设置，默认2次）时，自动将 `supported` 标记为 `false`
- 标记为 `false` 的方法在后续调用中会被跳过，不再尝试
- 可通过管理接口手动重置方法状态

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| system_prompt | string | 否 | 系统提示词，定义AI角色和任务 |
| query | string | 是 | 用户输入/对话内容 |
| tools | array | 是 | 工具/函数定义列表（OpenAI Function Calling 标准格式） |
| tool_choice | string/object | 否 | 工具选择策略，默认 "auto" |
| preferred_methods | array | 否 | 手动指定方法优先级列表（覆盖自动选择）|

**请求示例**:

```json
{
  "system_prompt": "你是一个专业的客服场景分类助手。请根据对话内容识别业务场景。",
  "query": "客户说：我要投诉你们的服务，太糟糕了！",
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "classify_scene",
        "description": "根据客服对话内容，识别当前工单所属的业务场景",
        "parameters": {
          "type": "object",
          "properties": {
            "scene_name": {
              "type": "string",
              "enum": ["投诉处理", "业务咨询", "预约进店", "道路救援", "配件查询"],
              "description": "只能从上述选项中选择一个最匹配的场景名称"
            },
            "confidence": {
              "type": "string",
              "enum": ["高", "中", "低"],
              "description": "分类置信度"
            }
          },
          "required": ["scene_name"]
        }
      }
    }
  ],
  "tool_choice": "auto",
  "preferred_methods": ["pydantic_parser", "json_parser"]
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `messages` | array | 是 | 对话消息列表，遵循 OpenAI Chat Completions API 标准格式 |
| `messages[].role` | string | 是 | 消息角色：`system`/`user`/`assistant`/`tool` |
| `messages[].content` | string | 是 | 消息内容 |
| `tools` | array | 是 | 工具/函数定义列表，遵循 OpenAI Function Calling 标准 |
| `tools[].type` | string | 是 | 工具类型，固定为 `"function"` |
| `tools[].function` | object | 是 | 函数定义，包含 name/description/parameters |
| `tool_choice` | string/object | 否 | 工具选择策略：`"auto"`/`"none"`/`{"type": "function", "function": {"name": "xxx"}}` |
| `context` | string | 否 | 额外上下文，会自动添加到 messages 开头作为 system message |
| `preferred_methods` | array | 否 | 手动指定结构化输出方法优先级 |

**响应示例**:

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "scene_name": "投诉处理",
    "confidence": "高",
    "_meta": {
      "method_used": "with_structured_output",
      "model": "gpt-4",
      "latency_ms": 1250,
      "prompt_tokens": 150,
      "completion_tokens": 50
    }
  }
}
```

**响应说明**:

响应直接返回提取的结构化数据（即 `tool_calls[0].function.arguments` 解析后的 JSON 对象），包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `...` | any | 根据 `tools` 中定义的函数参数 schema 返回对应的结构化数据字段 |
| `_meta` | object | 元信息，包含实际使用的方法、模型、延迟和 token 消耗 |
| `_meta.method_used` | string | 实际使用的结构化输出方法 |
| `_meta.model` | string | 使用的模型名称 |
| `_meta.latency_ms` | int | 请求延迟（毫秒）|
| `_meta.prompt_tokens` | int | 输入 token 数 |
| `_meta.completion_tokens` | int | 输出 token 数 |

### 2. 健康检查接口

**接口地址**: `GET /api/llm/proxy/health`

**认证方式**: `Authorization: Bearer {api_key}`

**响应示例**:

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "status": "healthy",
    "tenant_id": 1,
    "app_name": "test_app",
    "llm_config": {
      "name": "GPT-4",
      "model": "openai/gpt-4"
    }
  }
}
```

## 管理接口（JWT认证）

### LLM 模型配置管理

基于项目标准的 CRUD 接口设计，符合前端 `useCRUD` 组合式函数规范。

#### 1. 获取配置列表

**接口地址**: `GET /api/v1/ai/llm_config/list`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认10 |
| name | string | 否 | 配置名称模糊查询 |
| model_provider | string | 否 | 模型提供商筛选 |
| is_active | bool | 否 | 是否启用筛选 |
| tenant_id | int | 否 | 租户ID筛选（超管可用）|

**响应示例**:

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "GPT-4",
        "model_provider": "openai",
        "litellm_params": {
          "model": "openai/gpt-4",
          "timeout": 60
        },
        "is_active": true,
        "is_default": true,
        "tenant_id": null,
        "app_name": null,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10
  }
}
```

#### 2. 获取配置详情

**接口地址**: `GET /api/v1/ai/llm_config/get?id={id}`

**响应示例**:

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "id": 1,
    "name": "GPT-4",
    "model_provider": "openai",
    "litellm_params": {
      "model": "openai/gpt-4",
      "api_key": "sk-xxx",
      "timeout": 60,
      "max_retries": 2
    },
    "model_info": {
      "mode": "chat",
      "max_tokens": 8192,
      "supports_function_calling": true
    },
    "capabilities": {
      "structured_output_methods": {
        "with_structured_output": {"supported": true, "failed_count": 0},
        "bind_tools_stream": {"supported": true, "failed_count": 0},
        "custom_fc_non_stream": {"supported": true, "failed_count": 0},
        "custom_fc_stream": {"supported": true, "failed_count": 0},
        "pydantic_parser": {"supported": true, "failed_count": 0},
        "json_parser": {"supported": true, "failed_count": 0}
      }
    },
    "tenant_id": null,
    "app_name": null,
    "is_active": true,
    "is_default": true,
    "description": "OpenAI GPT-4 模型",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
  }
}
```

#### 3. 创建配置

**接口地址**: `POST /api/v1/ai/llm_config/create`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 配置名称 |
| model_provider | string | 是 | 模型提供商 |
| litellm_params | object | 是 | LiteLLM 参数 |
| model_info | object | 否 | 模型元信息 |
| tenant_id | int | 否 | 租户ID，超管可指定 |
| app_name | string | 否 | 应用名称 |
| is_active | bool | 否 | 是否启用，默认true |
| is_default | bool | 否 | 是否为默认配置，默认false |
| description | string | 否 | 配置描述 |

**请求示例**:

```json
{
  "name": "GPT-4",
  "model_provider": "openai",
  "litellm_params": {
    "model": "openai/gpt-4",
    "api_key": "sk-xxx",
    "timeout": 60,
    "max_retries": 2
  },
  "model_info": {
    "mode": "chat",
    "max_tokens": 8192
  },
  "is_active": true,
  "is_default": false,
  "description": "OpenAI GPT-4 模型"
}
```

**创建时同步到 LiteLLM**:

后端服务会在创建配置时自动调用 LiteLLM 的 `/model/new` 接口，将配置同步到 LiteLLM 网关。

#### 4. 更新配置

**接口地址**: `POST /api/v1/ai/llm_config/update`

**请求参数**: 同创建配置，需增加 `id` 字段

**说明**: 更新配置后自动同步到 LiteLLM 网关（调用 `/model/update` 接口）

#### 5. 删除配置

**接口地址**: `DELETE /api/v1/ai/llm_config/delete?id={id}`

**说明**: 删除配置后自动从 LiteLLM 网关移除（调用 `/model/delete` 接口）

#### 6. 获取模型提供商列表

**接口地址**: `GET /api/v1/ai/llm_config/providers`

**响应示例**:

```json
{
  "code": 200,
  "msg": "OK",
  "data": [
    {"value": "openai", "label": "OpenAI"},
    {"value": "azure", "label": "Azure OpenAI"},
    {"value": "anthropic", "label": "Anthropic"},
    {"value": "vertex_ai", "label": "Google Vertex AI"},
    {"value": "bedrock", "label": "AWS Bedrock"},
    {"value": "ollama", "label": "Ollama"},
    {"value": "deepseek", "label": "DeepSeek"},
    {"value": "openrouter", "label": "OpenRouter"}
  ]
}
```

#### 7. 测试配置连通性

**接口地址**: `POST /api/v1/ai/llm_config/test`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | int | 是 | 配置ID |

**响应示例**:

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "status": "success",
    "latency_ms": 450,
    "model_response": "Hello! How can I help you today?"
  }
}
```

#### 8. 获取 LiteLLM 网关状态

**接口地址**: `GET /api/v1/ai/llm_config/gateway/status`

**响应示例**:

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "status": "healthy",
    "version": "1.40.0",
    "models_loaded": 12,
    "active_connections": 5
  }
}
```

#### 9. 重置模型方法状态

**接口地址**: `POST /api/v1/ai/llm_config/reset_methods`

**说明**: 手动重置指定模型的结构化输出方法状态

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | int | 是 | 配置ID |
| methods | array | 否 | 指定重置的方法列表，不传则重置所有方法 |

**请求示例**:

```json
{
  "id": 1,
  "methods": ["with_structured_output", "bind_tools_stream"]
}
```

#### 10. 获取模型方法状态

**接口地址**: `GET /api/v1/ai/llm_config/methods?id={id}`

**说明**: 获取指定模型的结构化输出方法支持状态

**响应示例**:

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "model_id": 1,
    "model_name": "gpt-4",
    "capabilities": {
      "structured_output_methods": {
        "with_structured_output": {
          "supported": true,
          "failed_count": 0,
          "last_error": null,
          "last_attempt": "2024-01-15T10:30:00Z"
        },
        "bind_tools_stream": {
          "supported": false,
          "failed_count": 2,
          "last_error": "Tool calling not supported",
          "last_attempt": "2024-01-15T10:25:00Z"
        }
      }
    }
  }
}
```

---

## 前端实现指南

基于项目 `frontend` 目录下的 Vue3 + TypeScript + Ant Design Vue 技术栈。

### 1. API 接口定义

在 `frontend/src/api/index.ts` 中添加：

```typescript
// LLM 配置管理
getLLMConfigList: (params: any = {}) => request.get('/ai/llm_config/list', { params }),
getLLMConfigById: (params: any = {}) => request.get('/ai/llm_config/get', { params }),
createLLMConfig: (data: any = {}) => request.post('/ai/llm_config/create', data),
updateLLMConfig: (data: any = {}) => request.post('/ai/llm_config/update', data),
deleteLLMConfig: (params: any = {}) => request.delete('/ai/llm_config/delete', { params }),
getLLMProviders: () => request.get('/ai/llm_config/providers'),
testLLMConfig: (data: any = {}) => request.post('/ai/llm_config/test', data),
getLLMGatewayStatus: () => request.get('/ai/llm_config/gateway/status'),
getLLMMethods: (params: any = {}) => request.get('/ai/llm_config/methods', { params }),
resetLLMMethods: (data: any = {}) => request.post('/ai/llm_config/reset_methods', data),
```

### 2. 页面实现

页面已存在：`frontend/src/views/ai/llm-config/index.vue`

**需要更新的内容**：

1. **API 接口字段调整**：将原有的 `model_name`, `api_key`, `api_base`, `temperature` 等字段改为 `litellm_params` 对象
2. **表单增加 JSON 编辑器**：用于编辑 `litellm_params` 和 `model_info`
3. **增加测试按钮**：调用 `testLLMConfig` 接口测试配置连通性

**关键修改点**：

```typescript
// 表单字段调整
const modalForm = reactive({
  name: '',
  model_provider: undefined,
  // 改为 litellm_params 对象
  litellm_params: {
    model: '',           // 原 model_name
    api_key: '',         // 原 api_key
    api_base: '',        // 原 api_base
    timeout: 60,
    max_retries: 2,
    headers: {},
  },
  model_info: {
    mode: 'chat',
    max_tokens: 8192,
    supports_function_calling: true,
  },
  is_active: true,
  is_default: false,
  tenant_id: undefined,
  description: '',
})

// 表格列调整 - 显示 litellm_params.model
const columns = [
  { title: '配置名称', dataIndex: 'name', key: 'name', width: 150 },
  { title: '提供商', dataIndex: 'model_provider', key: 'model_provider', width: 120 },
  { title: '模型', key: 'model', width: 200,
    render: (record: any) => record.litellm_params?.model || '-'
  },
  // ... 其他列
]
```

### 3. 路由配置

路由已存在：`frontend/src/router/routes.ts`

```typescript
{
  path: '/ai',
  name: 'AI管理',
  component: Layout,
  meta: { title: 'AI管理', icon: 'RobotOutlined' },
  children: [
    {
      path: 'llm-config',
      name: 'LLM模型配置',
      component: () => import('@/views/ai/llm-config/index.vue'),
      meta: { title: 'LLM模型配置', icon: 'DatabaseOutlined' }
    }
  ]
}
```

## 支持的模型提供商

LiteLLM 支持 100+ 模型提供商，常用包括：

| 提供商 | LiteLLM 前缀 | 说明 |
|--------|-------------|------|
| OpenAI | `openai/` | GPT-3.5, GPT-4, GPT-4o |
| Azure OpenAI | `azure/` | Azure 托管的 OpenAI |
| Anthropic | `anthropic/` | Claude 3 系列 |
| Google Vertex AI | `vertex_ai/` | Gemini 系列 |
| AWS Bedrock | `bedrock/` | Claude, Llama 等 |
| Cohere | `cohere/` | Command 系列 |
| Mistral AI | `mistral/` | Mistral 系列 |
| DeepSeek | `deepseek/` | DeepSeek 系列 |
| Ollama | `ollama/` | 本地模型 |
| OpenRouter | `openrouter/` | 聚合平台 |
| Groq | `groq/` | 高速推理 |
| Perplexity | `perplexity/` | pplx 系列 |

## 多租户数据隔离规则

1. **全局配置**: `tenant_id` 为 `null`，由超管创建，所有租户可见
2. **租户配置**: `tenant_id` 不为 `null`，仅该租户可见
3. **应用隔离**: 通过 `app_name` 进一步细分，不同应用可使用不同模型配置
4. **默认配置**: 每个租户可以有独立的默认配置

## Redis 缓存策略

1. **LLM配置缓存**: `autofill:llm_config:app_key:{api_key}`，缓存1小时
2. **LiteLLM 模型列表缓存**: `autofill:litellm:models`，缓存5分钟
3. **缓存清除**: 配置增删改时自动清除相关缓存

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 认证失败 |
| 403 | 无权限 |
| 404 | 配置不存在 |
| 500 | 服务器内部错误 |
| 502 | LiteLLM 网关错误 |
| 503 | LLM服务不可用 |

## 使用示例

### Python 调用示例

```python
import requests

# 配置
api_key = "your_api_key_here"
base_url = "http://localhost:8000"

# 请求数据
payload = {
    "query": "客户说：我的车在路上抛锚了，需要紧急救援！",
    "function_schema": {
        "type": "function",
        "function": {
            "name": "classify_scene",
            "description": "根据客服对话内容，识别当前工单所属的业务场景",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_name": {
                        "type": "string",
                        "enum": ["投诉处理", "业务咨询", "预约进店", "道路救援", "配件查询"],
                        "description": "只能从上述选项中选择一个最匹配的场景名称"
                    }
                },
                "required": ["scene_name"]
            }
        }
    }
}

# 发送请求
response = requests.post(
    f"{base_url}/api/llm/proxy",
    json=payload,
    headers={"Authorization": f"Bearer {api_key}"}
)

# 解析响应
result = response.json()
if result["code"] == 200:
    print(f"场景: {result['data']['scene_name']}")
else:
    print(f"错误: {result['msg']}")
```

### cURL 调用示例

```bash
curl -X POST http://localhost:8000/api/llm/proxy \
  -H "Authorization: Bearer your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "system_prompt": "你是一个专业的客服场景分类助手。请根据对话内容识别业务场景。",
    "query": "客户说：我想预约明天下午3点的保养服务",
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "classify_scene",
          "description": "根据客服对话内容，识别当前工单所属的业务场景",
          "parameters": {
            "type": "object",
            "properties": {
              "scene_name": {
                "type": "string",
                "enum": ["投诉处理", "业务咨询", "预约进店", "道路救援", "配件查询"]
              }
            },
            "required": ["scene_name"]
          }
        }
      }
    ],
    "tool_choice": "auto"
  }'
```

## 部署架构

### 独立 LiteLLM 网关部署

LiteLLM 作为独立服务部署在 `litellm/` 目录下，使用项目现有的 MySQL 和 Redis。

```bash
cd /Users/lu/code/code/py/autofill/litellm
docker-compose up -d
```

详见 [litellm/README.md](../litellm/README.md)
