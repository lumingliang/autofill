# 系统架构设计文档

## 1. 项目概述

Vue FastAPI Admin 是一个基于 FastAPI + Vue3 的中后台管理系统，支持多租户、RBAC权限管理、智能填单等功能。

## 2. 系统架构

### 2.1 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue3 + TypeScript + Ant Design Vue + Vite |
| 后端 | FastAPI + Tortoise ORM |
| 数据库 | MySQL |
| 缓存 | Redis |
| 消息队列 | Kafka |
| AI/LLM | LangChain + LiteLLM |

### 2.2 目录结构

```
autofill/
├── app/                          # 后端应用
│   ├── api/                      # API路由
│   │   ├── v1/                   # v1版本API
│   │   │   ├── llm_config/       # LLM配置管理接口
│   │   │   └── ...               # 其他模块
│   │   ├── autofill_public.py    # 智能填单公开接口
│   │   └── llm_proxy.py          # LLM代理公开接口
│   ├── controllers/              # 控制器层
│   │   ├── llm_config.py         # LLM配置控制器
│   │   └── ...                   # 其他控制器
│   ├── core/                     # 核心组件
│   │   ├── autofill_auth.py      # API Key认证
│   │   ├── crud.py               # CRUD基类
│   │   ├── redis.py              # Redis客户端
│   │   └── ...                   # 其他核心组件
│   ├── models/                   # 数据模型
│   │   ├── llm_config.py         # LLM配置模型
│   │   ├── autofill.py           # 智能填单模型
│   │   └── admin.py              # 管理员模型
│   ├── schemas/                  # Pydantic Schema
│   │   ├── llm_config.py         # LLM配置Schema
│   │   └── ...                   # 其他Schema
│   └── services/                 # 服务层
│       ├── llm_proxy_service.py  # LLM代理服务
│       └── ai_fill_service.py    # AI填单服务
├── frontend/                     # 前端应用
│   ├── src/
│   │   ├── api/                  # API接口
│   │   ├── views/                # 页面视图
│   │   │   ├── ai/               # AI大模型模块
│   │   │   │   └── llm-config/   # LLM配置页面
│   │   │   └── ...               # 其他模块
│   │   └── ...
│   └── ...
└── docs/                         # 文档
```

## 3. 核心模块设计

### 3.1 多租户架构

```
┌─────────────────────────────────────────────────────────┐
│                      租户隔离层                          │
├─────────────────────────────────────────────────────────┤
│  超管(Superuser)                                         │
│  ├── 可访问所有租户数据                                   │
│  ├── 可创建全局配置(tenant_id=null)                       │
│  └── 可管理所有租户                                       │
│                                                          │
│  普通用户                                                │
│  ├── 只能访问当前租户数据                                 │
│  ├── 可查看全局配置                                       │
│  └── 可管理自己租户的配置                                 │
└─────────────────────────────────────────────────────────┘
```

**数据隔离规则**:
- 全局配置: `tenant_id = null`，所有租户可见
- 租户配置: `tenant_id = {tenant_id}`，仅该租户可见

### 3.2 认证授权体系

```
┌─────────────────────────────────────────────────────────┐
│                      认证方式                            │
├─────────────────────────────────────────────────────────┤
│  1. JWT认证 (后台管理)                                   │
│     - 用于: 后台管理界面、管理API                         │
│     - 方式: Authorization: Bearer {jwt_token}           │
│                                                          │
│  2. API Key认证 (公开接口)                               │
│     - 用于: Dify调用、第三方应用调用                      │
│     - 方式: Authorization: Bearer {api_key}             │
│     - 关联: AppManagement表，包含租户信息                 │
└─────────────────────────────────────────────────────────┘
```

### 3.3 LLM代理架构

```
┌─────────────────────────────────────────────────────────┐
│                    LLM代理调用流程                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  调用方                                                   │
│     │                                                    │
│     │ POST /api/llm/proxy                                │
│     │ Authorization: Bearer {api_key}                    │
│     │ Body: {query, function_schema, context}            │
│     ▼                                                    │
│  ┌─────────────────┐                                     │
│  │  API Key认证     │                                     │
│  │  (APIKeyAuth)   │                                     │
│  └────────┬────────┘                                     │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────┐     缓存未命中     ┌─────────────┐  │
│  │  Redis缓存查询   │ ────────────────> │  数据库查询  │  │
│  │  llm_config:    │                   │  LLMConfig  │  │
│  │  {api_key}      │ <──────────────── │             │  │
│  └────────┬────────┘     缓存写入       └─────────────┘  │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────────────────────────────────────┐    │
│  │              LangChain 结构化输出                 │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  ChatPromptTemplate                     │    │    │
│  │  │       │                                 │    │    │
│  │  │       ▼                                 │    │    │
│  │  │  ChatLiteLLM (with_structured_output)   │    │    │
│  │  │       │                                 │    │    │
│  │  │       ▼                                 │    │    │
│  │  │  Pydantic Model (动态创建)               │    │    │
│  │  │       │                                 │    │    │
│  │  │       ▼                                 │    │    │
│  │  │  JSON Output                            │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────┐                                     │
│  │  LiteLLM适配层   │                                     │
│  │  统一调用多模型  │                                     │
│  │  - OpenAI       │                                     │
│  │  - Azure        │                                     │
│  │  - Anthropic    │                                     │
│  │  - 百度/阿里等   │                                     │
│  └─────────────────┘                                     │
│           │                                              │
│           ▼                                              │
│  返回 JSON 格式数据                                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Fallback机制**:
1. 优先使用租户默认配置
2. 租户配置失败时，自动切换到全局默认配置
3. 全局配置失败时返回错误

### 3.4 缓存架构

```
┌─────────────────────────────────────────────────────────┐
│                      Redis缓存                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Key前缀: autofill:{module}:{identifier}                │
│                                                          │
│  1. LLM配置缓存                                          │
│     Key: autofill:llm_config:app_key:{api_key}          │
│     TTL: 3600秒 (1小时)                                  │
│     触发清除: 配置增删改                                  │
│                                                          │
│  2. API Key缓存 (预留)                                   │
│     Key: autofill:api_key:{api_key}                     │
│     TTL: 3600秒                                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 4. 数据模型设计

### 4.1 LLM配置模型

```python
class LLMConfig(BaseModel, TimestampMixin):
    """LLM 配置表"""
    # 基础信息
    name = fields.CharField(max_length=64)           # 配置名称
    tenant_id = fields.BigIntField(null=True)        # 租户ID，null=全局
    
    # 模型配置
    model_provider = fields.CharField(max_length=32) # 模型提供商
    model_name = fields.CharField(max_length=128)    # 模型名称
    
    # API配置
    api_key = fields.CharField(max_length=255)       # API密钥
    api_base = fields.CharField(max_length=255, null=True)  # API基础URL
    
    # 模型参数
    temperature = fields.FloatField(default=0.7)     # 温度参数
    max_tokens = fields.IntField(default=2048)       # 最大token数
    top_p = fields.FloatField(default=1.0)           # Top P采样
    
    # 功能开关
    is_active = fields.BooleanField(default=True)    # 是否启用
    is_default = fields.BooleanField(default=False)  # 是否为默认配置
    
    # 描述信息
    description = fields.CharField(max_length=500, null=True)  # 配置描述
```

### 4.2 支持的模型提供商

| 提供商 | 标识 | 示例模型 |
|--------|------|----------|
| OpenAI | openai | gpt-4, gpt-3.5-turbo |
| Azure | azure | azure/gpt-4 |
| Anthropic | anthropic | claude-3-opus |
| Google | google | gemini-pro |
| 百度文心 | baidu | ernie-bot |
| 阿里通义 | alibaba | qwen-turbo |
| 智谱AI | zhipu | chatglm_turbo |
| DeepSeek | deepseek | deepseek-chat |
| Moonshot | moonshot | moonshot-v1-8k |
| 千帆 | qianfan | qianfan-chat |
| 讯飞星火 | xunfei | spark-desk |
| MiniMax | minimax | minimax-abab5.5 |

## 5. API设计

### 5.1 接口分类

```
┌─────────────────────────────────────────────────────────┐
│                      API分类                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. 管理接口 (JWT认证)                                    │
│     前缀: /api/v1/                                       │
│     权限: 依赖用户角色和权限                              │
│                                                          │
│     AI大模型模块 (/api/v1/ai/)                           │
│     ├── GET  /llm_config/list      配置列表              │
│     ├── GET  /llm_config/get       配置详情              │
│     ├── POST /llm_config/create    创建配置              │
│     ├── POST /llm_config/update    更新配置              │
│     ├── DELETE /llm_config/delete  删除配置              │
│     ├── GET  /llm_config/providers 提供商列表            │
│     └── GET  /llm_config/default   默认配置              │
│                                                          │
│  2. 公开接口 (API Key认证)                                │
│     前缀: /api/                                          │
│     权限: 验证API Key有效性                               │
│                                                          │
│     LLM代理接口                                          │
│     ├── POST /llm/proxy            结构化输出代理        │
│     └── GET  /llm/proxy/health     健康检查              │
│                                                          │
│     智能填单接口                                         │
│     ├── GET/POST /autofill/summary_template/list         │
│     ├── GET/POST /autofill/summary_template              │
│     ├── GET/POST /autofill/dropdown_options/list         │
│     └── GET/POST /autofill/dropdown_options              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 5.2 LLM代理接口详情

**请求**:
```http
POST /api/llm/proxy
Authorization: Bearer {api_key}
Content-Type: application/json

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
            "description": "分类置信度"
          }
        },
        "required": ["scene_name"]
      }
    }
  },
  "context": "可选的额外上下文信息"
}
```

**响应**:
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

## 6. 前端架构

### 6.1 菜单结构

```
工作台
系统管理
├── 用户管理
├── 角色管理
├── 菜单管理
├── API管理
├── 部门管理
├── 审计日志
└── 租户管理
智能填单
├── 应用管理
├── 总结模板
├── 下拉选项
└── 填单记录
AI大模型 (新增)
└── LLM配置
```

### 6.2 页面组件

| 页面 | 路径 | 功能 |
|------|------|------|
| LLM配置管理 | /ai/llm-config | 配置的增删改查 |

### 6.3 API封装

```typescript
// frontend/src/api/index.ts
export default {
  // AI大模型 - LLM配置管理
  getLLMConfigList: (params: any = {}) => request.get('/ai/llm_config/list', { params }),
  getLLMConfigById: (params: any = {}) => request.get('/ai/llm_config/get', { params }),
  createLLMConfig: (data: any = {}) => request.post('/ai/llm_config/create', data),
  updateLLMConfig: (data: any = {}) => request.post('/ai/llm_config/update', data),
  deleteLLMConfig: (params: any = {}) => request.delete('/ai/llm_config/delete', { params }),
  getLLMProviders: () => request.get('/ai/llm_config/providers'),
  getDefaultLLMConfig: () => request.get('/ai/llm_config/default'),
}
```

## 7. 核心代码实现

### 7.1 动态Pydantic模型创建

```python
def _create_pydantic_model(self, function_schema: dict) -> Type[BaseModel]:
    """根据函数schema动态创建Pydantic模型"""
    function_def = function_schema.get("function", {})
    schema_name = function_def.get("name", "DynamicResponse")
    parameters = function_def.get("parameters", {})
    properties = parameters.get("properties", {})
    required = parameters.get("required", [])

    # 构建字段定义
    fields = {}
    for prop_name, prop_def in properties.items():
        field_type = self._get_field_type(prop_def)
        if prop_name in required:
            fields[prop_name] = (field_type, ...)
        else:
            fields[prop_name] = (Optional[field_type], None)

    # 创建动态模型
    DynamicModel = create_model(schema_name, **fields)
    return DynamicModel
```

### 7.2 LangChain结构化输出调用

```python
async def invoke_structured(
    self,
    query: str,
    function_schema: dict,
    config: LLMConfig,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """调用LLM并返回结构化输出"""
    # 获取chat model
    chat_model = self._get_chat_model(config)

    # 创建动态Pydantic模型
    output_model = self._create_pydantic_model(function_schema)

    # 构建prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt),
    ])

    # 使用with_structured_output
    structured_llm = chat_model.with_structured_output(output_model)
    chain = prompt | structured_llm

    # 调用
    result = await chain.ainvoke({})
    return result.model_dump()
```

## 8. 部署与配置

### 8.1 环境变量

```toml
# config.toml
[database.mysql]
host = "127.0.0.1"
port = 3306
user = "root"
password = "root123456"
database = "autofill"

[redis]
host = "127.0.0.1"
port = 6379
password = ""
db = 0
key_prefix = "autofill"
```

### 8.2 依赖安装

```bash
# requirements.txt 已包含
langchain>=0.2.0
langchain-core>=0.2.0
langchain-openai>=0.1.0
langchain-community>=0.2.0
litellm>=1.40.0
```

## 9. 扩展性设计

### 9.1 新增模型提供商

1. 在 `LLMProvider` 类中添加新的提供商常量
2. 前端提供商选择列表自动更新
3. LiteLLM自动适配新的提供商

### 9.2 新增功能模块

按照现有架构模式：
1. 创建 Model
2. 创建 Schema
3. 创建 Controller
4. 创建 API Router
5. 注册路由
6. 创建前端页面
7. 初始化菜单（如需要）

## 10. 安全设计

### 10.1 认证安全

- JWT Token 有效期: 7天
- API Key 缓存: 1小时
- 密码加密: Argon2

### 10.2 数据安全

- 多租户数据隔离
- API Key 不返回给前端
- 敏感操作记录审计日志

### 10.3 接口安全

- 管理接口: JWT + 权限校验
- 公开接口: API Key 认证
- CORS 配置
- 请求频率限制（可扩展）
