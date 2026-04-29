# LLM 模块需求与实施文档

## 一、项目概述

### 1.1 背景
本项目是一个基于 FastAPI + Vue3 的智能填单系统，目前使用 Dify AI 服务进行 AI 填单处理。为了提供更灵活的 LLM 调用能力，需要集成 LangChain 作为核心框架，实现统一的 LLM 管理模块。

### 1.2 技术栈
- **后端**: FastAPI + Tortoise ORM + MySQL + Redis + Kafka
- **前端**: Vue3 + TypeScript + Ant Design Vue + Pinia + Vue Router
- **AI 框架**: LangChain (核心框架)

**架构说明**: 
- **LangChain** 是核心框架，负责所有 LLM 交互、结构化输出、链式调用等
- LangChain 内置支持多种模型提供商（OpenAI、Anthropic、Azure 等）
- 所有 JSON 解析、结构化输出均使用 LangChain 内置能力，不手动处理
- **配置格式统一**: 从配置管理中获取的 LLM 配置信息均为 **OpenAI 兼容格式**，LangChain 的 `ChatOpenAI` 可以直接使用，无需额外适配
- **Redis 缓存**: 使用 Redis 缓存模型配置，减少数据库查询压力，提升响应速度

---

## 二、需求分析

### 2.1 功能需求

#### 2.1.1 大模型配置管理（数据库管理）
| 需求项 | 描述 |
|--------|------|
| 数据库存储 | 大模型配置存储在数据库中，替代 llm.toml 文件配置 |
| 租户隔离 | 支持查询当前 tenant_id 下的模型配置，同时可获取全局（无 tenant_id）的模型配置 |
| 全局配置 | 超级管理员可配置全局模型，供所有租户使用 |
| 唯一标识 | 模型 code **全局唯一**，支持用户自定义，不设置则自动生成（如：gpt-4o、claude-3-sonnet），重复时自动加序号（如：gpt-4o-1、gpt-4o-2） |
| 模型参数配置 | 支持配置 API Key、Base URL、温度、最大 token、超时时间等参数 |
| 加密存储 | API Key 等敏感信息加密存储 |

#### 2.1.2 LLM 交互界面（前端）
| 需求项 | 描述 |
|--------|------|
| 父级菜单 | 新增"AI 大模型"父级菜单 |
| 模型管理页面 | 列表展示、新增、编辑、删除模型配置 |
| Prompt 输入 | 多行文本输入框，支持输入 prompt |
| 模型选择 | 下拉选择框，从数据库加载当前租户+全局的可用模型列表 |
| JSON 输出选项 | 开关选择是否要求 JSON 格式输出 |
| JSON 结构示例 | 当开启 JSON 输出时，可配置 JSON 结构示例，用于引导模型输出格式 |
| 运行按钮 | 点击后调用后端 API 获取模型回复 |
| 结果展示 | 智能判断返回格式，JSON 则格式化展示，否则纯文本展示 |

#### 2.1.3 代理 API 接口（后端）
| 需求项 | 描述 |
|--------|------|
| 统一 Service 层 | 前端 LLM 交互和代理 API 共用同一套 LLMService 服务层 |
| 结构化输出 | **强制使用 LangChain 的结构化输出能力**，不手动解析 JSON |
| 参数支持 | prompt、model_code、json_sample、retry_count、timeout |
| JSON Sample 处理 | 接收 json_sample（JSON 示例数据），使用 LangChain 转换为 Pydantic Model |
| 错误处理 | 支持重试机制和超时控制，由 LangChain 内置机制处理 |
| 输出校验 | **由 LangChain 自动校验输出格式**，无需手动校验 |

---

## 三、系统架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                           前端层 (Vue3)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ LLM 管理页面 │  │ LLM 交互页面│  │ JSON/文本结果展示组件    │  │
│  │ 增删改查    │  │ Prompt+运行 │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          API 网关层 (FastAPI)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ LLM 配置 API│  │ LLM 交互 API│  │ 代理 API                │  │
│  │ /v1/llm/... │  │ /v1/llm/... │  │ /v1/llm/...             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          服务层 (LangChain 核心)                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    LLM Service                          │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │           LangChain Core                        │    │    │
│  │  │  ┌─────────────┐  ┌─────────────────────────┐   │    │    │
│  │  │  │ Chat Model  │  │ Structured Output       │   │    │    │
│  │  │  │ Interface   │  │ (with_structured_output)│   │    │    │
│  │  │  └─────────────┘  └─────────────────────────┘   │    │    │
│  │  │  ┌─────────────┐  ┌─────────────────────────┐   │    │    │
│  │  │  │ Prompt      │  │ Output Parser           │   │    │    │
│  │  │  │ Templates   │  │ (PydanticOutputParser)  │   │    │    │
│  │  │  └─────────────┘  └─────────────────────────┘   │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          数据层                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    llm_config 表                        │    │
│  │  (id, code, name, provider, model, api_key, tenant_id)  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 模块设计

#### 3.2.1 后端模块结构

```
app/
├── core/
│   └── llm/
│       ├── __init__.py
│       ├── factory.py         # LangChain 模型工厂 - 根据配置创建 ChatModel
│       ├── cache.py           # Redis 缓存管理 - 模型配置缓存
│       └── utils.py           # 工具函数（code生成等）
├── services/
│   └── llm_service.py         # LLM 统一业务服务层 - 使用 LangChain 进行所有调用
├── controllers/
│   └── llm.py                 # LLM 配置控制器
├── models/
│   └── llm.py                 # LLM 配置模型
├── api/
│   └── v1/
│       └── llm/
│           ├── __init__.py
│           └── llm.py         # LLM API 路由
└── schemas/
    └── llm.py                 # LLM 请求/响应模型
```

**架构说明**:
1. **LangChain 是核心**: 所有 LLM 调用都通过 LangChain 的接口完成
2. **配置格式统一**: 所有 LLM 配置均采用 **OpenAI 兼容格式**，通过 `ChatOpenAI` 类直接使用
   - `api_key`: API 密钥
   - `base_url`: 自定义 API 地址（如使用第三方代理）
   - `model`: 模型名称（如 gpt-4o、claude-3-sonnet 等）
   - 其他参数（temperature、max_tokens 等）与 OpenAI API 完全一致
3. **Redis 缓存**: 使用 Redis 缓存模型配置，缓存策略如下：
   - 缓存键: `llm:config:{model_code}`
   - 缓存过期: 5 分钟（300 秒）
   - 缓存更新: 配置变更时主动失效缓存
4. **结构化输出**: 强制使用 `with_structured_output()` 方法，不手动解析 JSON
5. **Pydantic 模型**: 从 json_sample 自动生成 Pydantic Model，作为 LangChain 的结构化输出类型

#### 3.2.2 前端模块结构

```
frontend/src/
├── views/
│   └── llm/
│       ├── config/            # 模型配置管理
│       │   └── index.vue
│       └── chat/              # LLM 交互页面
│           └── index.vue
├── api/
│   └── llm.ts                 # LLM API 接口
└── components/
    └── llm/
        ├── ModelForm.vue      # 模型配置表单
        ├── PromptInput.vue    # Prompt 输入组件
        ├── ModelSelector.vue  # 模型选择组件
        ├── JsonSampleInput.vue # JSON 示例输入组件
        └── ResultDisplay.vue  # 结果展示组件
```

---

## 四、详细设计

### 4.1 数据库模型设计

#### 4.1.1 LLM 配置表 (llm_config)

```python
# app/models/llm.py
from tortoise import fields
from app.models.base import BaseModel


class LLMConfig(BaseModel):
    """大模型配置表"""
    
    # 唯一标识，全局唯一，支持用户自定义，不设置则自动生成（如：gpt-4o、claude-3-sonnet、gpt-4o-1）
    code = fields.CharField(max_length=100, unique=True, description="模型唯一标识，全局唯一")
    
    # 显示名称
    name = fields.CharField(max_length=200, description="模型显示名称")
    
    # 提供商（openai、anthropic、azure、ollama等）
    provider = fields.CharField(max_length=50, description="模型提供商")
    
    # 实际模型名称（如：gpt-4o、claude-3-sonnet-20240229）
    model = fields.CharField(max_length=200, description="实际模型名称")
    
    # API Key（加密存储）
    api_key = fields.CharField(max_length=500, null=True, description="API Key")
    
    # Base URL（可选）
    base_url = fields.CharField(max_length=500, null=True, description="自定义API地址")
    
    # 温度参数
    temperature = fields.FloatField(default=0.7, description="温度参数")
    
    # 最大 token 数
    max_tokens = fields.IntField(default=4096, description="最大token数")
    
    # 超时时间（秒）
    timeout = fields.IntField(default=60, description="超时时间(秒)")
    
    # 重试次数
    max_retries = fields.IntField(default=3, description="最大重试次数")
    
    # 租户ID（null 表示全局配置）
    tenant_id = fields.IntField(null=True, description="租户ID，null为全局配置")
    
    # 是否启用
    is_active = fields.BooleanField(default=True, description="是否启用")
    
    # 描述
    description = fields.TextField(null=True, description="模型描述")
    
    class Meta:
        table = "llm_config"
        description = "大模型配置表"
```

#### 4.1.2 Code 生成与校验规则

```python
# app/core/llm/utils.py
import re
from typing import Optional


def generate_model_code(name: str, provider: str) -> str:
    """
    自动生成模型唯一标识 code
    
    规则：
    1. 基于 provider + name 生成基础 code（如：openai-gpt-4o）
    2. 如果已存在（全局范围内），则自动添加序号（如：openai-gpt-4o-1）
    3. code 全局唯一，不区分租户
    
    Args:
        name: 模型显示名称
        provider: 提供商
        
    Returns:
        唯一的 model code
    """
    # 清理名称，只保留字母、数字、下划线、横线
    base_code = f"{provider}-{name}".lower()
    base_code = re.sub(r'[^a-z0-9_-]', '-', base_code)
    base_code = re.sub(r'-+', '-', base_code).strip('-')
    
    # 检查是否已存在（全局范围）
    from app.models.llm import LLMConfig
    
    code = base_code
    counter = 0
    
    while True:
        # code 全局唯一，不区分租户
        exists = await LLMConfig.filter(code=code).exists()
        if not exists:
            return code
            
        counter += 1
        code = f"{base_code}-{counter}"


def validate_model_code(code: str, exclude_id: int = None) -> tuple[bool, str]:
    """
    校验用户自定义的 model code
    
    规则：
    1. 只能包含小写字母、数字、下划线、横线
    2. 必须以字母开头
    3. 长度 3-100 字符
    4. 全局唯一（不区分租户）
    
    Args:
        code: 用户输入的 code
        exclude_id: 排除的 ID（用于更新时排除自身）
        
    Returns:
        (是否有效, 错误信息)
    """
    # 长度校验
    if not code or len(code) < 3 or len(code) > 100:
        return False, "code 长度必须在 3-100 字符之间"
    
    # 格式校验：只能包含小写字母、数字、下划线、横线
    if not re.match(r'^[a-z][a-z0-9_-]*$', code):
        return False, "code 只能以小写字母开头，包含小写字母、数字、下划线、横线"
    
    # 全局唯一性校验
    from app.models.llm import LLMConfig
    
    query = LLMConfig.filter(code=code)
    if exclude_id:
        query = query.exclude(id=exclude_id)
    
    if query.exists():
        return False, f"code '{code}' 已存在，请使用其他名称"
    
    return True, ""


async def get_or_generate_code(
    custom_code: Optional[str], 
    name: str, 
    provider: str,
    exclude_id: int = None
) -> str:
    """
    获取或生成 model code
    
    优先级：
    1. 如果用户提供了 custom_code，校验后使用
    2. 如果未提供，自动生成
    
    Args:
        custom_code: 用户自定义的 code（可选）
        name: 模型显示名称
        provider: 提供商
        exclude_id: 排除的 ID（用于更新时排除自身）
        
    Returns:
        最终的 model code
        
    Raises:
        ValueError: 自定义 code 校验失败
    """
    if custom_code:
        # 用户提供了自定义 code，进行校验
        is_valid, error_msg = validate_model_code(custom_code.strip().lower(), exclude_id)
        if not is_valid:
            raise ValueError(error_msg)
        return custom_code.strip().lower()
    
    # 未提供，自动生成
    return await generate_model_code(name, provider)
```

### 4.2 API 接口设计

#### 4.2.1 模型配置管理接口

**获取模型列表（支持租户隔离）**
```
GET /api/v1/llm/config/list?page=1&page_size=10&include_global=true

Headers:
  Authorization: Bearer {token}

Query:
  - include_global: 是否包含全局配置（默认 true）

Response:
{
  "code": 200,
  "msg": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "code": "openai-gpt-4o",
        "name": "GPT-4o",
        "provider": "openai",
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 4096,
        "is_global": true,           // 是否为全局配置
        "tenant_id": null,
        "is_active": true,
        "description": "OpenAI GPT-4o 模型"
      },
      {
        "id": 2,
        "code": "anthropic-claude-3-sonnet",
        "name": "Claude 3 Sonnet",
        "provider": "anthropic",
        "model": "claude-3-sonnet-20240229",
        "temperature": 0.7,
        "max_tokens": 4096,
        "is_global": false,
        "tenant_id": 1,
        "is_active": true,
        "description": "Anthropic Claude 3"
      }
    ],
    "total": 2
  }
}
```

**创建模型配置**
```
POST /api/v1/llm/config/create

Request:
{
  "code": "my-gpt-4o",           // 可选，用户自定义 code，不设置则自动生成
  "name": "GPT-4o",
  "provider": "openai",
  "model": "gpt-4o",
  "api_key": "sk-xxx",
  "base_url": "https://api.openai.com/v1",
  "temperature": 0.7,
  "max_tokens": 4096,
  "timeout": 60,
  "max_retries": 3,
  "is_active": true,
  "description": "OpenAI GPT-4o"
}

Response:
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": 1,
    "code": "my-gpt-4o",          // 使用用户自定义的 code 或自动生成
    "name": "GPT-4o",
    "provider": "openai",
    "model": "gpt-4o",
    ...
  }
}
```

**更新模型配置**
```
POST /api/v1/llm/config/update

Request:
{
  "id": 1,
  "code": "new-gpt-4o-code",     // 可选，修改 code（需全局唯一）
  "name": "GPT-4o Updated",
  "api_key": "sk-new-key",
  "temperature": 0.5,
  "is_active": true
}

Response:
{
  "code": 200,
  "msg": "success",
  "data": {...}
}
```

**删除模型配置**
```
DELETE /api/v1/llm/config/delete?id=1

Response:
{
  "code": 200,
  "msg": "删除成功"
}
```

**获取模型下拉列表**
```
GET /api/v1/llm/config/select?include_global=true

Response:
{
  "code": 200,
  "msg": "success",
  "data": [
    {"label": "[全局] GPT-4o", "value": "openai-gpt-4o"},
    {"label": "[全局] Claude 3", "value": "anthropic-claude-3"},
    {"label": "DeepSeek Chat", "value": "deepseek-chat"}
  ]
}
```

#### 4.2.2 LLM 对话接口（前端使用）

```
POST /api/v1/llm/chat

Request:
{
  "prompt": "请介绍一下 Python",
  "model_code": "openai-gpt-4o",
  "json_output": true,
  "json_sample": {               // 可选，用于引导 JSON 输出格式
    "language": "Python",
    "features": ["简洁", "易读"],
    "use_cases": ["Web开发", "数据分析"]
  },
  "temperature": 0.7
}

Response:
{
  "code": 200,
  "msg": "success",
  "data": {
    "content": "{\"language\": \"Python\", ...}",
    "model_code": "openai-gpt-4o",
    "is_json": true,
    "parsed_json": {
      "language": "Python",
      "features": ["简洁", "易读"],
      "use_cases": ["Web开发", "数据分析"]
    },
    "usage": {
      "prompt_tokens": 50,
      "completion_tokens": 100,
      "total_tokens": 150
    }
  }
}
```

#### 4.2.3 结构化输出代理接口（第三方调用）

```
POST /api/v1/llm/structured

Request:
{
  "prompt": "从以下文本中提取姓名和年龄：张三今年25岁",
  "model_code": "openai-gpt-4o",
  "json_sample": {               // JSON 示例，后端自动解析为 Pydantic Model
    "name": "张三",
    "age": 25
  },
  "retry_count": 3,
  "timeout": 30
}

Response:
{
  "code": 200,
  "msg": "success",
  "data": {
    "result": {
      "name": "张三",
      "age": 25
    },
    "model_code": "openai-gpt-4o",
    "usage": {
      "prompt_tokens": 50,
      "completion_tokens": 20,
      "total_tokens": 70
    }
  }
}
```

---

## 五、核心实现

### 5.1 Redis 缓存管理

```python
# app/core/llm/cache.py
import json
from typing import Optional, Dict, Any
from datetime import timedelta
from app.core.redis import redis_client


class LLMConfigCache:
    """LLM 配置缓存管理"""
    
    # 缓存键前缀
    CACHE_PREFIX = "llm:config"
    # 默认缓存过期时间（秒）
    DEFAULT_TTL = 300  # 5 分钟
    
    @classmethod
    def _make_key(cls, model_code: str) -> str:
        """生成缓存键"""
        return f"{cls.CACHE_PREFIX}:{model_code}"
    
    @classmethod
    async def get(cls, model_code: str) -> Optional[Dict[str, Any]]:
        """
        从缓存获取模型配置
        
        Args:
            model_code: 模型唯一标识
            
        Returns:
            配置字典或 None
        """
        key = cls._make_key(model_code)
        cached = await redis_client.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    @classmethod
    async def set(
        cls,
        model_code: str,
        config: Dict[str, Any],
        ttl: int = DEFAULT_TTL
    ) -> None:
        """
        将模型配置写入缓存
        
        Args:
            model_code: 模型唯一标识
            config: 配置字典
            ttl: 过期时间（秒）
        """
        key = cls._make_key(model_code)
        await redis_client.setex(key, ttl, json.dumps(config))
    
    @classmethod
    async def delete(cls, model_code: str) -> None:
        """
        删除缓存
        
        Args:
            model_code: 模型唯一标识
        """
        key = cls._make_key(model_code)
        await redis_client.delete(key)
    
    @classmethod
    async def clear_all(cls) -> None:
        """清除所有 LLM 配置缓存"""
        pattern = f"{cls.CACHE_PREFIX}:*"
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
```

### 5.2 LangChain 模型工厂

```python
# app/core/llm/factory.py
from typing import Type, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from app.models.llm import LLMConfig
from app.core.security import encryptor
from app.core.llm.cache import LLMConfigCache


class LangChainModelFactory:
    """
    LangChain 模型工厂 - 根据配置创建 ChatModel
    
    **重要说明**: 
    - 所有 LLM 配置均采用 OpenAI 兼容格式
    - 无论实际调用的是 OpenAI、Anthropic 还是其他提供商的模型
    - 配置参数（api_key、base_url、model、temperature 等）均与 OpenAI API 格式一致
    - 通过 ChatOpenAI 类统一创建，无需针对不同提供商做适配
    """
    
    @classmethod
    async def create_chat_model(
        cls,
        config: LLMConfig,
        temperature: Optional[float] = None,
    ) -> BaseChatModel:
        """
        根据配置创建 LangChain ChatModel
        
        **配置格式说明**:
        从配置管理中获取的配置均为 OpenAI 兼容格式，直接使用 ChatOpenAI 创建：
        - api_key: API 密钥（已解密）
        - base_url: 自定义 API 地址（可选，用于第三方代理）
        - model: 模型名称（如 gpt-4o、claude-3-sonnet 等）
        - temperature: 温度参数（0-2）
        - max_tokens: 最大生成 token 数
        - timeout: 请求超时时间（秒）
        - max_retries: 失败重试次数
        
        Args:
            config: LLM 配置
            temperature: 可选的温度参数，覆盖配置中的值
            
        Returns:
            LangChain ChatModel 实例（ChatOpenAI）
        """
        # 解密 API Key
        api_key = None
        if config.api_key:
            api_key = encryptor.decrypt(config.api_key)
        
        # 构建模型参数（OpenAI 兼容格式）
        model_kwargs = {
            "model": config.model,
            "temperature": temperature if temperature is not None else config.temperature,
            "max_tokens": config.max_tokens,
            "timeout": config.timeout,
            "max_retries": config.max_retries,
        }
        
        # 添加 API Key（如果有）
        if api_key:
            model_kwargs["api_key"] = api_key
        
        # 添加 Base URL（如果有）
        if config.base_url:
            model_kwargs["base_url"] = config.base_url
        
        # 使用 ChatOpenAI 创建模型（OpenAI 兼容格式）
        return ChatOpenAI(**model_kwargs)
    
    @classmethod
    async def create_structured_model(
        cls,
        config: LLMConfig,
        output_schema: Type,
        temperature: Optional[float] = None,
    ):
        """
        创建带结构化输出的模型
        
        Args:
            config: LLM 配置（OpenAI 兼容格式）
            output_schema: Pydantic Model 类，定义输出结构
            temperature: 可选的温度参数
            
        Returns:
            配置了结构化输出的 ChatModel
        """
        # 创建基础模型
        base_model = await cls.create_chat_model(config, temperature)
        
        # **关键**: 使用 LangChain 的 with_structured_output() 方法
        # 这会自动处理 JSON 解析和校验
        structured_model = base_model.with_structured_output(
            output_schema,
            method="function_calling"  # 或 "json_mode"，根据模型支持
        )
        
        return structured_model
```

### 5.3 LLM 统一服务层

```python
# app/services/llm_service.py
from typing import Optional, Type, Any
from pydantic import create_model, BaseModel
from app.core.llm.factory import LangChainModelFactory
from app.core.llm.cache import LLMConfigCache
from app.models.llm import LLMConfig
from app.core.exceptions import BusinessException
from app.core.security import encryptor


class LLMService:
    """
    LLM 统一服务层 - 所有 LLM 调用都通过这里
    
    **缓存策略**:
    - 优先从 Redis 缓存获取配置，减少数据库查询
    - 缓存键: llm:config:{model_code}
    - 缓存过期: 5 分钟
    - 配置变更时主动失效缓存
    """
    
    @staticmethod
    def json_sample_to_pydantic(json_sample: dict, model_name: str = "OutputSchema") -> Type[BaseModel]:
        """
        将 JSON 示例转换为 Pydantic Model
        
        Args:
            json_sample: JSON 示例数据
            model_name: 生成的模型名称
            
        Returns:
            Pydantic Model 类
        """
        # 从 JSON 示例推断字段类型
        fields = {}
        for key, value in json_sample.items():
            field_type = type(value)
            # 处理列表类型
            if field_type == list and value:
                # 使用第一个元素类型作为列表元素类型
                elem_type = type(value[0])
                field_type = list[elem_type]
            fields[key] = (field_type, ...)
        
        # 动态创建 Pydantic Model
        return create_model(model_name, **fields)
    
    @classmethod
    async def chat(
        cls,
        prompt: str,
        model_code: str,
        tenant_id: Optional[int] = None,
        json_output: bool = False,
        json_sample: Optional[dict] = None,
        temperature: Optional[float] = None,
    ) -> dict:
        """
        普通对话接口
        
        Args:
            prompt: 用户输入的 prompt
            model_code: 模型唯一标识
            tenant_id: 当前租户ID
            json_output: 是否要求 JSON 输出
            json_sample: JSON 示例（用于引导输出格式）
            temperature: 温度参数
            
        Returns:
            包含回复内容和元信息的字典
        """
        # 查询模型配置（带缓存，租户隔离 + 全局）
        config = await cls._get_config_with_cache(model_code, tenant_id)
        if not config:
            raise BusinessException(f"模型 '{model_code}' 不存在或未启用")
        
        # 创建模型
        if json_output and json_sample:
            # 结构化输出模式
            output_schema = cls.json_sample_to_pydantic(json_sample)
            model = await LangChainModelFactory.create_structured_model(
                config, output_schema, temperature
            )
            
            # 调用模型
            result = await model.ainvoke(prompt)
            
            return {
                "content": result.json() if hasattr(result, 'json') else str(result),
                "model_code": model_code,
                "is_json": True,
                "parsed_json": result.dict() if hasattr(result, 'dict') else result,
            }
        else:
            # 普通对话模式
            model = await LangChainModelFactory.create_chat_model(config, temperature)
            
            # 调用模型
            from langchain_core.messages import HumanMessage
            result = await model.ainvoke([HumanMessage(content=prompt)])
            
            content = result.content if hasattr(result, 'content') else str(result)
            
            # 尝试解析 JSON
            parsed_json = None
            is_json = False
            if json_output:
                try:
                    import json
                    parsed_json = json.loads(content)
                    is_json = True
                except:
                    pass
            
            return {
                "content": content,
                "model_code": model_code,
                "is_json": is_json,
                "parsed_json": parsed_json,
            }
    
    @classmethod
    async def structured_output(
        cls,
        prompt: str,
        model_code: str,
        json_sample: dict,
        tenant_id: Optional[int] = None,
        retry_count: int = 3,
        timeout: Optional[int] = None,
    ) -> dict:
        """
        结构化输出接口（代理 API 使用）
        
        Args:
            prompt: 用户输入的 prompt
            model_code: 模型唯一标识
            json_sample: JSON 示例，定义输出结构
            tenant_id: 当前租户ID
            retry_count: 重试次数
            timeout: 超时时间（秒）
            
        Returns:
            结构化输出结果
        """
        # 查询模型配置（带缓存）
        config = await cls._get_config_with_cache(model_code, tenant_id)
        if not config:
            raise BusinessException(f"模型 '{model_code}' 不存在或未启用")
        
        # 临时修改配置的重试次数和超时
        original_retries = config.max_retries
        original_timeout = config.timeout
        
        if retry_count is not None:
            config.max_retries = retry_count
        if timeout is not None:
            config.timeout = timeout
        
        try:
            # 创建 Pydantic Model
            output_schema = cls.json_sample_to_pydantic(json_sample)
            
            # 创建结构化输出模型
            model = await LangChainModelFactory.create_structured_model(
                config, output_schema
            )
            
            # 调用模型
            result = await model.ainvoke(prompt)
            
            return {
                "result": result.dict() if hasattr(result, 'dict') else result,
                "model_code": model_code,
            }
        finally:
            # 恢复原始配置
            config.max_retries = original_retries
            config.timeout = original_timeout
    
    @classmethod
    async def _get_config_with_cache(
        cls,
        model_code: str,
        tenant_id: Optional[int] = None
    ) -> Optional[LLMConfig]:
        """
        获取模型配置（带 Redis 缓存，支持租户隔离）
        
        **缓存策略**:
        1. 优先从 Redis 缓存获取
        2. 缓存未命中则从数据库查询并写入缓存
        3. 查询优先级：租户配置 > 全局配置
        
        Args:
            model_code: 模型唯一标识
            tenant_id: 当前租户ID
            
        Returns:
            LLMConfig 或 None
        """
        # 构建缓存键（包含租户信息，确保隔离）
        cache_key = f"{model_code}:t{tenant_id}" if tenant_id else f"{model_code}:global"
        
        # 1. 尝试从缓存获取
        cached_config = await LLMConfigCache.get(cache_key)
        if cached_config:
            # 从缓存重建 LLMConfig 对象
            return cls._dict_to_config(cached_config)
        
        # 2. 缓存未命中，从数据库查询
        config = await cls._get_config_from_db(model_code, tenant_id)
        
        # 3. 写入缓存
        if config:
            config_dict = cls._config_to_dict(config)
            await LLMConfigCache.set(cache_key, config_dict)
        
        return config
    
    @classmethod
    async def _get_config_from_db(
        cls,
        model_code: str,
        tenant_id: Optional[int] = None
    ) -> Optional[LLMConfig]:
        """
        从数据库获取模型配置（支持租户隔离）
        
        查询优先级：
        1. 当前租户的配置
        2. 全局配置（tenant_id 为 null）
        
        Args:
            model_code: 模型唯一标识
            tenant_id: 当前租户ID
            
        Returns:
            LLMConfig 或 None
        """
        # 先查询租户专属配置
        if tenant_id:
            config = await LLMConfig.filter(
                code=model_code,
                tenant_id=tenant_id,
                is_active=True
            ).first()
            if config:
                return config
        
        # 查询全局配置
        config = await LLMConfig.filter(
            code=model_code,
            tenant_id__isnull=True,
            is_active=True
        ).first()
        
        return config
    
    @classmethod
    def _config_to_dict(cls, config: LLMConfig) -> dict:
        """将 LLMConfig 对象转换为字典（用于缓存）"""
        return {
            "id": config.id,
            "code": config.code,
            "name": config.name,
            "provider": config.provider,
            "model": config.model,
            "api_key": config.api_key,  # 已加密的 API Key
            "base_url": config.base_url,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "timeout": config.timeout,
            "max_retries": config.max_retries,
            "tenant_id": config.tenant_id,
            "is_active": config.is_active,
        }
    
    @classmethod
    def _dict_to_config(cls, data: dict) -> LLMConfig:
        """从字典重建 LLMConfig 对象（从缓存读取）"""
        config = LLMConfig()
        for key, value in data.items():
            setattr(config, key, value)
        return config
    
    @classmethod
    async def invalidate_cache(cls, model_code: str, tenant_id: Optional[int] = None) -> None:
        """
        失效模型配置缓存
        
        在以下场景调用：
        - 更新模型配置后
        - 删除模型配置后
        - 切换模型启停状态后
        
        Args:
            model_code: 模型唯一标识
            tenant_id: 租户ID（None 表示全局配置）
        """
        # 失效租户配置缓存
        if tenant_id:
            await LLMConfigCache.delete(f"{model_code}:t{tenant_id}")
        # 失效全局配置缓存
        await LLMConfigCache.delete(f"{model_code}:global")
```

### 5.4 API Key 加密存储

```python
# app/core/security.py
from cryptography.fernet import Fernet
from app.settings.config import settings


class Encryptor:
    """加密工具类"""
    
    _instance = None
    _cipher = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 使用 SECRET_KEY 生成加密密钥
            key = Fernet.generate_key()
            cls._cipher = Fernet(key)
        return cls._instance
    
    def encrypt(self, text: str) -> str:
        """加密文本"""
        if not text:
            return ""
        return self._cipher.encrypt(text.encode()).decode()
    
    def decrypt(self, encrypted_text: str) -> str:
        """解密文本"""
        if not encrypted_text:
            return ""
        return self._cipher.decrypt(encrypted_text.encode()).decode()


encryptor = Encryptor()
```

### 5.5 前端结果展示组件

```vue
<!-- frontend/src/components/llm/ResultDisplay.vue -->
<template>
  <div class="result-display">
    <div v-if="loading" class="loading">
      <a-spin tip="AI 思考中..." />
    </div>
    <div v-else-if="error" class="error">
      <a-alert :message="error" type="error" show-icon />
    </div>
    <div v-else-if="content" class="content">
      <!-- JSON 格式展示 -->
      <div v-if="isJson" class="json-content">
        <vue-json-pretty :data="parsedJson" />
      </div>
      <!-- 纯文本展示 -->
      <div v-else class="text-content">
        <pre>{{ content }}</pre>
      </div>
    </div>
    <div v-else class="empty">
      <a-empty description="暂无结果" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VueJsonPretty from 'vue-json-pretty'
import 'vue-json-pretty/lib/styles.css'

interface Props {
  content?: string
  loading?: boolean
  error?: string
  forceJson?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  content: '',
  loading: false,
  error: '',
  forceJson: false,
})

// 判断是否为 JSON
const isJson = computed(() => {
  if (props.forceJson) return true
  if (!props.content) return false
  try {
    JSON.parse(props.content)
    return true
  } catch {
    return false
  }
})

// 解析 JSON
const parsedJson = computed(() => {
  try {
    return JSON.parse(props.content || '{}')
  } catch {
    return {}
  }
})
</script>

<style scoped>
.result-display {
  min-height: 200px;
  padding: 16px;
  background: #f6f8fa;
  border-radius: 8px;
}

.json-content {
  background: #fff;
  padding: 16px;
  border-radius: 4px;
}

.text-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
}
</style>
```

---

## 六、依赖清单

### 6.1 Python 依赖

```txt
# requirements.txt 新增
# LangChain 核心框架
langchain>=0.2.0
langchain-core>=0.2.0

# 特定提供商支持（可选，根据需求安装）
langchain-openai>=0.1.0
langchain-anthropic>=0.1.0

# 加密
pydantic>=2.0.0
cryptography>=42.0.0
```

### 6.2 Node 依赖

```json
// package.json 新增
{
  "dependencies": {
    "vue-json-pretty": "^2.4.0"
  }
}
```

---

## 七、配置说明

### 7.1 环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| LLM_ENCRYPTION_KEY | API Key 加密密钥 | 自动生成 |

### 7.2 数据库配置项

| 配置项 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| code | string | 是 | 模型唯一标识（**全局唯一**，支持自定义，不设置则自动生成） |
| name | string | 是 | 模型显示名称 |
| provider | string | 是 | 提供商（openai/anthropic/ollama等） |
| model | string | 是 | 实际模型名称 |
| api_key | string | 条件 | API Key（加密存储） |
| base_url | string | 否 | 自定义 API 地址 |
| temperature | float | 否 | 温度参数（0-2） |
| max_tokens | int | 否 | 最大生成 token 数 |
| timeout | int | 否 | 超时时间（秒） |
| max_retries | int | 否 | 最大重试次数 |
| tenant_id | int | 否 | 租户ID（null为全局配置） |
| is_active | bool | 否 | 是否启用 |
| description | string | 否 | 模型描述 |

**code 规则说明**:
- **全局唯一**: 不区分租户，整个系统唯一
- **自定义**: 用户可自定义，需符合格式规范（小写字母开头，只能包含小写字母、数字、下划线、横线，3-100字符）
- **自动生成**: 未提供时基于 `provider-name` 自动生成，重复时自动添加序号

---

## 八、架构对比说明

### 8.1 旧架构 vs 新架构

| 方面 | 旧架构 | 新架构（LangChain 核心） |
|------|--------|--------------------------|
| **核心框架** | 手动解析 | **LangChain 为核心** |
| **结构化输出** | 手动解析 JSON | **with_structured_output()** |
| **JSON 校验** | 手动校验 | **Pydantic 自动校验** |
| **重试机制** | 手动实现 | **LangChain 内置** |
| **模型适配** | 直接调用 | **LangChain 内置多提供商支持** |
| **代码复杂度** | 高（需处理解析逻辑） | **低（LangChain 处理所有细节）** |

### 8.2 关键改进点

1. **强制使用 LangChain**: 所有 LLM 调用都通过 LangChain 接口完成
2. **结构化输出标准化**: 使用 `with_structured_output()` 方法，不手动解析 JSON
3. **Pydantic 类型安全**: 从 json_sample 自动生成 Pydantic Model，类型安全

---

## 九、风险评估

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| API Key 加密安全性 | 高 | 使用强加密算法，定期更换密钥 |
| 模型 code 重复 | 中 | 全局唯一校验，自动生成时自动添加序号 |
| 租户配置隔离 | 高 | 查询时严格过滤 tenant_id |
| LangChain 版本兼容性 | 中 | 锁定版本，测试后升级 |
| 模型响应超时 | 中 | 配置合理的超时时间和重试机制 |
| 自定义 code 格式错误 | 低 | 后端校验格式，前端实时校验提示 |

---

## 十、附录

### 10.1 参考资料

- [LangChain Documentation](https://python.langchain.com/) - **核心参考**
- [LangChain Structured Output](https://python.langchain.com/docs/how_to/structured_output/) - **结构化输出指南**
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vue3 Documentation](https://vuejs.org/)
- [Tortoise ORM Documentation](https://tortoise.github.io/)

### 10.2 术语表

| 术语 | 说明 |
|------|------|
| **LangChain** | **LLM 应用开发框架，本项目核心** |
| with_structured_output() | **LangChain 结构化输出方法** |
| Pydantic Model | 数据模型，用于定义输出结构 |
| JSON Sample | JSON 示例数据，用于引导模型输出格式 |
| Structured Output | 结构化输出，确保 LLM 返回指定格式的数据 |
| Prompt | 提示词，给 LLM 的输入指令 |
| Temperature | 温度参数，控制输出的随机性 |
| Code | 模型唯一标识，用于系统内部引用 |

### 10.3 模型 Code 生成示例

| 提供商 | 模型名称 | 生成 Code |
|--------|----------|-----------|
| openai | gpt-4o | openai-gpt-4o |
| openai | gpt-4o | openai-gpt-4o-1（重复时） |
| anthropic | claude-3-sonnet | anthropic-claude-3-sonnet |
| deepseek | deepseek-chat | deepseek-deepseek-chat |
| ollama | llama3 | ollama-llama3 |

---

**文档版本**: v3.1  
**更新日期**: 2026-04-27  
**更新说明**: 移除 LiteLLM 依赖，直接使用 LangChain 内置功能  
**作者**: AI Assistant
