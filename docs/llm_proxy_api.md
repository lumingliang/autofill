# LLM 代理接口文档

## 概述

基于 LangChain + LiteLLM 的代理接口，支持动态结构化输出。

## 接口调用流程

```
调用方（传appkey） -> 代理接口 -> 根据appkey查询llm配置（Redis缓存） -> LangChain结构化解析 -> LiteLLM适配调用不同模型 -> 返回JSON
```

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

**请求示例**:

```json
{
  "query": "客户说：我要投诉你们的服务，太糟糕了！",
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
          },
          "confidence": {
            "type": "string",
            "enum": ["高", "中", "低"],
            "description": "分类置信度，若对话信息模糊可标记为低"
          }
        },
        "required": ["scene_name"]
      }
    }
  }
}
```

**响应示例**:

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "scene_name": "投诉处理",
    "confidence": "高"
  }
}
```

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
      "name": "OpenAI GPT-4",
      "provider": "openai",
      "model": "gpt-4"
    }
  }
}
```

## 管理接口（JWT认证）

### LLM配置管理

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

**权限说明**:
- 超管：可以看到所有配置
- 普通用户：只能看到全局配置(tenant_id为null)和自己的租户配置

#### 2. 获取配置详情

**接口地址**: `GET /api/v1/ai/llm_config/get?id={id}`

#### 3. 创建配置

**接口地址**: `POST /api/v1/ai/llm_config/create`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 配置名称 |
| model_provider | string | 是 | 模型提供商 |
| model_name | string | 是 | 模型名称 |
| api_key | string | 是 | API密钥 |
| api_base | string | 否 | API基础URL |
| temperature | float | 否 | 温度参数，默认0.7 |
| max_tokens | int | 否 | 最大token数，默认2048 |
| top_p | float | 否 | Top P采样，默认1.0 |
| is_active | bool | 否 | 是否启用，默认true |
| is_default | bool | 否 | 是否为默认配置，默认false |
| tenant_id | int | 否 | 租户ID，超管可指定，为空表示全局配置 |
| description | string | 否 | 配置描述 |

#### 4. 更新配置

**接口地址**: `POST /api/v1/ai/llm_config/update`

**请求参数**: 同创建配置，需增加 `id` 字段

#### 5. 删除配置

**接口地址**: `DELETE /api/v1/ai/llm_config/delete?id={id}`

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
    {"value": "alibaba", "label": "阿里通义"},
    {"value": "deepseek", "label": "DeepSeek"},
    ...
  ]
}
```

#### 7. 获取默认配置

**接口地址**: `GET /api/v1/ai/llm_config/default`

## 支持的模型提供商

| 提供商 | 标识 | 说明 |
|--------|------|------|
| OpenAI | openai | GPT-3.5, GPT-4 系列 |
| Azure OpenAI | azure | Azure 托管的 OpenAI |
| Anthropic | anthropic | Claude 系列 |
| Google | google | Gemini 系列 |
| 百度文心 | baidu | 文心一言 |
| 阿里通义 | alibaba | 通义千问 |
| 智谱AI | zhipu | ChatGLM |
| DeepSeek | deepseek | DeepSeek 系列 |
| Moonshot | moonshot | Moonshot AI |
| 千帆大模型 | qianfan | 百度千帆 |
| 讯飞星火 | xunfei | 讯飞星火大模型 |
| MiniMax | minimax | MiniMax 系列 |
| 魔搭社区 | modelscope | ModelScope 模型（兼容 OpenAI 格式） |

## 魔搭社区 (ModelScope) 配置示例

魔搭社区提供 OpenAI 兼容的 API 接口，配置方式如下：

| 配置项 | 值 |
|--------|-----|
| 提供商 | `modelscope` |
| 模型名称 | `Qwen/QwQ-32B` |
| API Base URL | `https://api-inference.modelscope.cn/v1/` |
| API Key | `ms-919b1188-52f3-4654-b3bd-c46ab3bcf738` |

**配置说明**:
- 魔搭社区 API 完全兼容 OpenAI 格式，使用 `ChatOpenAI` 类直接调用
- 支持多种开源模型，如 Qwen、Llama、ChatGLM 等
- 通过 ModelScope 平台获取 API Key 和模型名称

## 多租户数据隔离规则

1. **全局配置**: `tenant_id` 为 `null`，由超管创建，所有租户可见
2. **租户配置**: `tenant_id` 不为 `null`，仅该租户可见
3. **默认配置**: 每个租户可以有独立的默认配置，优先使用租户默认配置，不存在时使用全局默认配置

## Redis缓存策略

1. **LLM配置缓存**: `autofill:llm_config:app_key:{api_key}`，缓存1小时
2. **缓存清除**: 配置增删改时自动清除相关缓存

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 认证失败 |
| 403 | 无权限 |
| 404 | 配置不存在 |
| 500 | 服务器内部错误 |
| 503 | LLM服务不可用 |

## 使用示例

### Python调用示例

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
    print(f"置信度: {result['data']['confidence']}")
else:
    print(f"错误: {result['msg']}")
```

### cURL调用示例

```bash
curl -X POST http://localhost:8000/api/llm/proxy \
  -H "Authorization: Bearer your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "客户说：我想预约明天下午3点的保养服务",
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
  }'
```
