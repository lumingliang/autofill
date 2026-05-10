# Vue FastAPI Admin 架构文档

> 本文档描述系统的整体架构设计，包括前端、后端、数据流和关键功能模块。
> 最后更新: 2026-05-02

---

## 1. 项目概述

Vue FastAPI Admin 是一个基于 Vue 3 + FastAPI 的 RBAC（基于角色的访问控制）后台管理系统，支持多租户架构。系统核心功能是**智能填单**，通过 AI 辅助完成各类业务表单的自动填写。

### 1.1 项目结构

```
autofill/
├── frontend/          # 前端项目 (Vue 3 + TypeScript)
├── app/               # 后端项目 (FastAPI + Python)
├── tests/             # 测试目录
├── litellm/           # LiteLLM 网关配置
├── scripts/           # 管理脚本
├── docs/              # 文档目录
├── .trae/             # AI 配置和约束
│   ├── docs/          # 技术约束文档
│   └── skills/        # AI Skills
└── pyproject.toml     # Python 项目配置
```

### 1.2 核心功能模块

| 模块 | 描述 | 状态 |
|------|------|------|
| RBAC 权限系统 | 基于角色的访问控制 | ✅ 已完成 |
| 多租户架构 | 数据隔离的租户系统 | ✅ 已完成 |
| 智能填单 | AI 辅助表单自动填写 | ✅ 已完成 |
| LLM 代理 | 统一的 LLM 调用接口 | ✅ 已完成 |
| Query Agent | 智能查询 Agent | ✅ 已完成 |
| BYD 经销商查询 | 比亚迪门店查询服务 | ✅ 已完成 |
| LiteLLM 网关 | 模型管理和代理 | ✅ 已完成 |
| 全局异常处理 | 统一的错误处理 | ✅ 已完成 |
| 结构化日志 | 完整的日志记录 | ✅ 已完成 |

---

## 2. 前端架构

### 2.1 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Vue | 3.5.32 | 核心框架 |
| 语言 | TypeScript | 6.0.2 | 类型安全 |
| 构建工具 | Vite | 8.0.10 | 开发服务器和构建 |
| UI 组件库 | Ant Design Vue | 4.2.6 | 组件库 |
| 状态管理 | Pinia | 3.0.2 | 全局状态管理 |
| 路由 | Vue Router | 4.5.1 | 客户端路由 |
| HTTP 客户端 | Axios | 1.9.0 | API 请求 |
| CSS 框架 | UnoCSS | 66.1.0-beta.12 | 原子化 CSS |
| 图标 | @ant-design/icons-vue | 7.0.1 | 图标库 |
| 工具库 | @vueuse/core | 13.2.0 | Vue 组合式函数 |
| 日期处理 | dayjs | 1.11.13 | 日期时间处理 |
| 工具函数 | lodash-es | 4.17.21 | 工具函数库 |

### 2.2 目录结构

```
frontend/src/
├── api/                    # API 接口定义
│   └── index.ts           # 统一导出所有 API
├── assets/                 # 静态资源
├── components/             # 公共组件
│   ├── CrudTable/         # CRUD 表格组件
│   ├── FilterForm/        # 筛选表单组件
│   ├── JsonViewer/        # JSON 查看器
│   └── IconSelector/      # 图标选择器
├── core/                   # 核心配置
│   └── ant-design/        # Ant Design 配置
├── directives/             # 自定义指令
│   ├── index.ts           # 指令注册
│   └── permission.ts      # 权限指令 v-permission
├── layout/                 # 布局组件
│   ├── components/        # 布局子组件
│   │   ├── Breadcrumb.vue
│   │   ├── LayoutHeader.vue
│   │   ├── LayoutMenu.vue
│   │   └── LayoutTags.vue
│   └── index.vue          # 主布局
├── router/                 # 路由配置
│   ├── index.ts           # 路由初始化和守卫
│   └── routes.ts          # 静态路由定义
├── store/                  # Pinia 状态管理
│   ├── modules/           # 状态模块
│   │   ├── app.ts         # 应用状态
│   │   ├── permission.ts  # 权限状态
│   │   ├── tags.ts        # 标签页状态
│   │   └── user.ts        # 用户状态
│   └── index.ts           # Store 初始化
├── styles/                 # 全局样式
│   ├── crud.less          # CRUD 页面样式
│   ├── index.less         # 入口样式
│   └── reset.less         # 重置样式
├── utils/                  # 工具函数
│   ├── auth.ts            # 认证相关
│   ├── common.ts          # 通用工具
│   ├── index.ts           # 统一导出
│   ├── request.ts         # Axios 封装
│   └── storage.ts         # 本地存储
├── views/                  # 页面视图
│   ├── autofill/          # 智能填单模块
│   │   ├── app/           # 应用管理
│   │   ├── dropdown/      # 下拉选项管理
│   │   ├── field_group/   # 字段分组管理
│   │   ├── field_spec/    # 字段规格管理
│   │   ├── page/          # 页面配置
│   │   ├── record/        # 填单记录
│   │   └── template/      # 模板管理
│   ├── error/             # 错误页面
│   ├── login/             # 登录页
│   ├── profile/           # 个人中心
│   ├── system/            # 系统管理
│   │   ├── api/           # API 管理
│   │   ├── auditlog/      # 审计日志
│   │   ├── dept/          # 部门管理
│   │   ├── llm_config/    # LLM 配置
│   │   ├── menu/          # 菜单管理
│   │   ├── role/          # 角色管理
│   │   ├── tenant/        # 租户管理
│   │   └── user/          # 用户管理
│   └── workbench/         # 工作台
├── App.vue                 # 根组件
├── main.ts                 # 入口文件
└── style.css               # 全局 CSS
```

### 2.3 核心架构模式

#### 2.3.1 组件化架构

- **布局组件**: `Layout` 提供整体页面结构（侧边栏 + 头部 + 内容区）
- **业务组件**: `CrudTable` 封装通用 CRUD 表格逻辑
- **视图组件**: 每个页面对应一个视图组件

#### 2.3.2 状态管理 (Pinia)

```typescript
// Store 模块划分
- appStore: 应用级状态（侧边栏折叠、主题等）
- userStore: 用户状态（用户信息、租户、权限）
- permissionStore: 权限状态（动态路由、API 权限）
- tagsStore: 标签页状态
```

#### 2.3.3 路由架构

- **静态路由**: 登录、404、403 等固定路由
- **动态路由**: 从后端获取菜单数据动态生成
- **路由守卫**: 认证检查、动态路由加载

#### 2.3.4 权限控制

- **指令级权限**: `v-permission="'post/api/v1/user/create'"`
- **路由级权限**: 动态路由过滤
- **API 级权限**: 后端接口权限校验

---

## 3. 后端架构

### 3.1 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | FastAPI | 0.111.0 | Web 框架 |
| 语言 | Python | >=3.11 | 编程语言 |
| ORM | Tortoise ORM | 0.23.0 | 异步 ORM |
| 数据库 | MySQL | 8.0+ | 主数据库 |
| 缓存 | Redis | - | 缓存和消息队列 |
| 消息队列 | Kafka | - | 异步任务 |
| 迁移工具 | Aerich | 0.8.1 | 数据库迁移 |
| 认证 | PyJWT | 2.10.1 | JWT Token |
| 密码加密 | Argon2 | 23.1.0 | 密码哈希 |
| 数据验证 | Pydantic | 2.10.5 | 数据模型验证 |
| 配置管理 | pydantic-settings | 2.7.1 | 环境配置 |
| 日志 | loguru | 0.7.3 | 日志记录 |
| LLM 网关 | LiteLLM | - | 模型代理 |
| Agent 框架 | LangGraph | - | 查询 Agent |

### 3.2 目录结构

```
app/
├── api/                    # API 路由层
│   ├── __init__.py        # 路由聚合
│   ├── public/            # 公开接口 (API Key 认证)
│   │   ├── __init__.py
│   │   ├── autofill.py    # 智能填单公开接口
│   │   ├── llm_proxy.py   # LLM 代理公开接口
│   │   └── query_agent.py # Query Agent 接口
│   └── v1/                # API 版本 1 (JWT 认证)
│       ├── __init__.py
│       ├── ai/            # AI 配置接口
│       ├── apis/          # API 管理接口
│       ├── auditlog/      # 审计日志接口
│       ├── autofill/      # 智能填单接口
│       ├── base/          # 基础接口（登录等）
│       ├── depts/         # 部门接口
│       ├── menus/         # 菜单接口
│       ├── roles/         # 角色接口
│       ├── tenants/       # 租户接口
│       ├── upload/        # 文件上传接口
│       └── users/         # 用户接口
├── controllers/           # 控制器层（业务逻辑）
│   ├── api.py             # API 控制器
│   ├── autofill.py        # 智能填单控制器
│   ├── dept.py            # 部门控制器
│   ├── llm_config.py      # LLM 配置控制器
│   ├── menu.py            # 菜单控制器
│   ├── role.py            # 角色控制器
│   ├── tenant.py          # 租户控制器
│   └── user.py            # 用户控制器
├── core/                  # 核心模块
│   ├── kafka/             # Kafka 消息队列
│   ├── autofill_auth.py   # 智能填单认证
│   ├── bgtask.py          # 后台任务
│   ├── crud.py            # CRUD 基类
│   ├── ctx.py             # 上下文管理
│   ├── dependency.py      # 依赖注入
│   ├── exceptions.py      # 异常处理
│   ├── init_app.py        # 应用初始化
│   ├── menu_config.py     # 菜单配置
│   ├── menu_registry.py   # 菜单注册
│   ├── middlewares.py     # 中间件
│   ├── redis.py           # Redis 连接
│   ├── relation.py        # 关系处理
│   └── request_parser.py  # 请求解析
├── log/                   # 日志模块
│   ├── __init__.py
│   └── log.py             # 日志配置和工具
├── models/                # 数据模型层
│   ├── __init__.py
│   ├── admin.py           # 管理员模型
│   ├── autofill.py        # 智能填单模型
│   ├── base.py            # 基础模型
│   ├── byd_dealer.py      # BYD 经销商模型
│   ├── enums.py           # 枚举定义
│   └── llm_config.py      # LLM 配置模型
├── schemas/               # Pydantic 模型
│   ├── __init__.py
│   ├── apis.py            # API 相关模型
│   ├── autofill.py        # 智能填单模型
│   ├── base.py            # 基础模型
│   ├── byd_dealer.py      # BYD 经销商模型
│   ├── depts.py           # 部门模型
│   ├── fill_page.py       # 填单页面模型
│   ├── llm_config.py      # LLM 配置模型
│   ├── login.py           # 登录模型
│   ├── menus.py           # 菜单模型
│   ├── roles.py           # 角色模型
│   ├── tenants.py         # 租户模型
│   └── users.py           # 用户模型
├── services/              # 服务层
│   ├── query_agent/       # Query Agent 服务
│   │   ├── __init__.py
│   │   ├── agent.py       # Agent 核心
│   │   ├── nodes.py       # 节点定义
│   │   ├── parser.py      # Curl 解析
│   │   ├── prompts.py     # 提示词
│   │   ├── types.py       # 类型定义
│   │   └── utils.py       # 工具函数
│   ├── ai_fill_service.py # AI 填单服务
│   ├── byd_dealer_service.py # BYD 经销商服务
│   ├── file_service.py    # 文件服务
│   ├── litellm_sync_service.py # LiteLLM 同步
│   ├── llm_proxy_service.py # LLM 代理服务
│   ├── prompt_service.py  # 提示词服务
│   └── structured_output.py # 结构化输出
├── settings/              # 配置
│   ├── __init__.py
│   └── config.py          # 应用配置
├── utils/                 # 工具函数
│   ├── jwt_utils.py       # JWT 工具
│   └── password.py        # 密码工具
└── __init__.py
```

### 3.3 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                        API 路由层                            │
│  (FastAPI Router - 参数校验、路由分发、认证授权)               │
├─────────────────────────────────────────────────────────────┤
│                       控制器层                               │
│  (Controllers - 业务逻辑编排、数据转换)                        │
├─────────────────────────────────────────────────────────────┤
│                       服务层                                 │
│  (Services - 核心业务逻辑、外部服务调用)                       │
├─────────────────────────────────────────────────────────────┤
│                       数据层                                 │
│  (Models - 数据访问、ORM 操作)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 核心功能模块详解

### 4.1 RBAC 权限系统

#### 4.1.1 权限模型

```
用户 (User) ──┬── 角色 (Role) ──┬── 菜单 (Menu)
              │                 └── API 权限 (API)
              └── 租户 (Tenant)
```

#### 4.1.2 权限控制层级

1. **菜单级权限**: 控制页面访问
2. **按钮级权限**: 控制操作权限（v-permission 指令）
3. **API 级权限**: 控制接口访问
4. **数据级权限**: 多租户数据隔离

### 4.2 多租户架构

#### 4.2.1 数据隔离策略

- **逻辑隔离**: 所有表包含 `tenant_id` 字段
- **超级管理员**: 可查看所有租户数据
- **普通用户**: 只能查看当前租户数据
- **公开接口**: 通过 API Key 识别租户

#### 4.2.2 租户识别方式

| 接口类型 | 认证方式 | 租户识别 |
|---------|---------|---------|
| 管理后台 | JWT Token | `current_user.current_tenant_id` |
| 公开接口 | API Key | `auth_info["tenant_id"]` |

### 4.3 智能填单系统

#### 4.3.1 核心概念

- **应用 (App)**: 填单业务的容器，包含独立的配置和数据
- **模板 (Template)**: 填单的表单结构定义
- **下拉选项 (Dropdown)**: 表单中的选择字段配置
- **填单记录 (Record)**: 用户填写的数据记录

#### 4.3.1a 字段模型设计

**唯一索引设计**

字段表 (`FieldSpec`) 的唯一索引为 `field_name + tenant_id + app_name`，这意味着：
- 在同一租户、同一应用内，字段名不能重复
- 不同租户或不同应用可以有相同的字段名
- `FieldGroupFieldSpec` 中间表仅用于管理字段组和字段的映射关系，不做唯一性约束

```python
# FieldSpec 模型核心字段
class FieldSpec:
    field_name: str      # 字段英文名（唯一索引部分）
    field_label: str     # 字段显示名称
    tenant_id: int       # 租户ID（唯一索引部分）
    app_name: str        # 应用名称（唯一索引部分）
    # ... 其他字段
```

**查询策略优化**

基于上述设计，字段查询分为两种情况：

1. **指定字段名查询**（情况1）
   - 适用场景：`group_fields = {"default": ["field1", "field2"]}`
   - 查询方式：直接用 `field_name + tenant_id + app_name` IN 查询
   - SQL示例：`SELECT * FROM field_spec WHERE tenant_id=? AND app_name=? AND field_name IN (?, ?)`

2. **通过字段组查询全量**（情况2）
   - 适用场景：`group_fields = {"default": []}`（空列表表示查该组所有字段）
   - 查询方式：
     - 步骤1：通过 `field_group_id` 查询 `FieldGroupFieldSpec` 获取所有 `field_spec_id`
     - 步骤2：通过 `field_spec_id` IN 查询 `FieldSpec` 获取字段明细
   - SQL示例：
     ```sql
     -- 步骤1
     SELECT field_spec_id FROM field_group_field_spec WHERE field_group_id IN (?)
     -- 步骤2
     SELECT * FROM field_spec WHERE id IN (?, ?, ...)
     ```

3. **混合查询**（情况1 + 情况2同时存在）
   - 适用场景：多个字段组，部分指定字段名，部分查全量
   - 查询方式：分别执行情况1和情况2的查询，然后合并结果
   - 合并策略：使用字典去重，以 `field_name` 为 key

**性能优势**

- 指定字段名查询直接命中唯一索引，性能最优
- 避免 N+1 查询问题，使用 IN 查询批量获取数据
- 中间表仅用于关系校验，不承载字段明细数据

#### 4.3.2 数据流

```
用户输入 → AI 解析 → 字段匹配 → 数据填充 → 结果返回
                ↓
            LLM 代理服务
                ↓
            结构化输出
```

#### 4.3.3 对外接口

| 接口 | 描述 | 认证 |
|------|------|------|
| `/api/public/autofill/fill` | 智能填单 | API Key |
| `/api/public/autofill/template/list` | 查询模板列表 | API Key |
| `/api/public/autofill/dropdown/list` | 查询下拉选项 | API Key |

### 4.4 LLM 代理服务

#### 4.4.1 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     LLM Proxy Service                        │
├─────────────────────────────────────────────────────────────┤
│  统一接口层  │  支持多种模型：OpenAI、Azure、Claude、本地模型  │
├─────────────────────────────────────────────────────────────┤
│  配置管理层  │  动态加载模型配置，支持多租户隔离              │
├─────────────────────────────────────────────────────────────┤
│  LiteLLM   │  统一的 LLM 调用网关                          │
└─────────────────────────────────────────────────────────────┘
```

#### 4.4.2 配置管理

- **LLMConfig 模型**: 存储模型配置参数
- **动态同步**: 自动同步配置到 LiteLLM
- **多租户支持**: 不同租户使用不同模型配置

### 4.5 Query Agent

#### 4.5.1 功能概述

基于 LangGraph 的智能查询 Agent，通过 HTTP 接口查询数据。支持：
- 动态解析 curl 请求
- 自动识别可搜索字段
- 智能多次尝试直到找到满意结果
- 结果提取和格式化

#### 4.5.2 核心组件

```python
# QueryAgent 核心组件
- CurlParser: 解析 curl 命令，提取 URL、方法、Headers
- Agent: LangGraph 状态机，管理查询流程
- Nodes: 各阶段处理节点（参数提取、请求执行、结果判断）
- Prompts: LLM 提示词模板
```

#### 4.5.3 工作流程

```
1. 解析 curl 模板，识别占位符
2. 分析用户 query，提取搜索参数
3. 执行 HTTP 请求
4. 判断结果是否满意
5. 不满意则调整参数，重复 3-4
6. 返回最终结果
```

### 4.6 BYD 经销商查询

#### 4.6.1 功能描述

Query Agent 的具体应用场景，用于查询比亚迪门店信息。

#### 4.6.2 数据模型

```python
class BYDDealer:
    id: int                    # 主键
    name: str                  # 门店名称
    city: str                  # 城市
    address: str               # 地址
    phone: str                 # 电话
    tenant_id: int             # 租户ID
```

#### 4.6.3 查询接口

```
POST /api/public/byd-dealers/search
Body: {"query": "上海门店", "city": "上海"}
```

---

## 5. 基础设施

### 5.1 日志系统

#### 5.1.1 架构设计

```
标准库 logging ──→ InterceptHandler ──→ loguru ──→ 文件/控制台
                              ↓
                        结构化 JSON 日志
```

#### 5.1.2 日志类型

| 类型 | 描述 | 位置 |
|------|------|------|
| 访问日志 | HTTP 请求/响应 | `logs/access/` |
| 错误日志 | 异常和错误 | `logs/error/` |
| 应用日志 | 业务日志 | `logs/app/` |

#### 5.1.3 特性

- **请求追踪**: 每个请求有唯一的 `request_id`
- **敏感数据脱敏**: 自动过滤密码、Token 等
- **结构化输出**: JSON 格式便于分析
- **自动轮转**: 按天分割日志文件

### 5.2 异常处理

#### 5.2.1 异常体系

```
Exception
├── BusinessException          # 业务异常基类
│   ├── ValidationException    # 参数验证异常
│   ├── NotFoundException      # 资源不存在
│   └── PermissionDeniedException # 权限不足
└── SystemException            # 系统异常
```

#### 5.2.2 全局异常处理器

- 捕获所有未处理的异常
- 统一错误响应格式
- 自动记录错误日志（含堆栈信息）
- 生产环境隐藏敏感信息

### 5.3 LiteLLM 网关

#### 5.3.1 功能

- 统一的 LLM 调用接口
- 多模型管理（OpenAI、Azure、Claude 等）
- 请求路由和负载均衡
- 使用统计和监控

#### 5.3.2 管理脚本

```bash
./scripts/litellm-gateway.sh start    # 启动
./scripts/litellm-gateway.sh stop     # 停止
./scripts/litellm-gateway.sh restart  # 重启
./scripts/litellm-gateway.sh status   # 状态
./scripts/litellm-gateway.sh logs     # 日志
```

---

## 6. 数据流图

### 6.1 智能填单流程

```
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────┐
│  用户   │───→│  前端页面   │───→│  AI 填单接口 │───→│ LLM 代理 │
└─────────┘    └─────────────┘    └─────────────┘    └────┬────┘
                                                           │
                              ┌────────────────────────────┘
                              ↓
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────┐
│  结果   │←───│  数据存储   │←───│  结构化输出 │←───│  LLM    │
└─────────┘    └─────────────┘    └─────────────┘    └─────────┘
```

### 6.2 Query Agent 流程

```
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────┐
│  查询   │───→│  QueryAgent │───→│  参数提取   │───→│ 执行请求 │
│  请求   │    │    接口     │    │  (LLM)      │    │         │
└─────────┘    └─────────────┘    └─────────────┘    └────┬────┘
                                                           │
                              ┌────────────────────────────┘
                              ↓
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────┐
│  结果   │←───│  结果提取   │←───│  结果判断   │←───│  响应   │
│  返回   │    │  (LLM)      │    │  (满意?)    │    │         │
└─────────┘    └─────────────┘    └──────┬──────┘    └─────────┘
                                         │
                              不满意 ─────┘
                              (循环最多5次)
```

---

## 7. 部署架构

### 7.1 开发环境

```
┌─────────────────────────────────────────────────────────────┐
│                        开发机器                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Frontend    │  │   Backend    │  │   LiteLLM    │       │
│  │   :3200      │  │    :9999     │  │    :4000     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                           │                                 │
│                    ┌──────┴──────┐                          │
│                    │   MySQL     │                          │
│                    │   :3306     │                          │
│                    └─────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 生产环境（建议）

```
┌─────────────────────────────────────────────────────────────┐
│                      负载均衡器 (Nginx)                       │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Frontend    │    │   Backend    │    │   LiteLLM    │
│   (多实例)    │    │   (多实例)    │    │   (多实例)    │
└──────────────┘    └──────────────┘    └──────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   MySQL      │    │    Redis     │    │    Kafka     │
│  (主从复制)   │    │  (哨兵模式)   │    │  (集群模式)   │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 8. 扩展性设计

### 8.1 水平扩展

- **无状态服务**: Backend 服务无状态，可水平扩展
- **负载均衡**: Nginx 反向代理分发请求
- **数据库**: MySQL 主从复制，读写分离
- **缓存**: Redis 集群模式

### 8.2 功能扩展

#### 8.2.1 新增模块步骤

1. **模型层**: 在 `app/models/` 添加数据模型
2. **Schema 层**: 在 `app/schemas/` 添加 Pydantic 模型
3. **控制器层**: 在 `app/controllers/` 添加业务逻辑
4. **API 层**: 在 `app/api/v1/` 添加接口路由
5. **前端页面**: 在 `frontend/src/views/` 添加页面

#### 8.2.2 新增公开接口

1. 在 `app/api/public/` 创建新的路由文件
2. 使用 `APIKeyAuth.authenticate` 进行认证
3. 从 `auth_info` 获取 `tenant_id`
4. 在 `app/api/__init__.py` 注册路由

---

## 9. 监控与运维

### 9.1 日志监控

- **日志收集**: 结构化 JSON 日志便于收集
- **日志分析**: 可按 `request_id` 追踪完整请求链路
- **错误告警**: 错误日志自动告警

### 9.2 性能监控

- **接口耗时**: 中间件记录请求处理时间
- **数据库性能**: Tortoise ORM 慢查询日志
- **LLM 调用**: LiteLLM 内置监控

### 9.3 健康检查

```
GET /health
Response: {"status": "healthy"}
```

---

## 10. 开发规范

### 10.1 代码规范

- **格式化**: black
- **代码检查**: ruff
- **类型检查**: mypy（推荐）
- **文档**: 所有公共函数必须有 docstring

### 10.2 Git 规范

- **分支**: `main` (生产), `dev` (开发), `feature/*` (功能)
- **提交信息**: 遵循 Conventional Commits
- **代码审查**: 所有提交需经过审查

### 10.3 测试规范

- **单元测试**: `tests/unit/`
- **集成测试**: `tests/integration/`
- **端到端测试**: `tests/e2e/`
- **测试脚本**: `tests/scripts/`

---

## 11. 相关文档

| 文档 | 描述 |
|------|------|
| [tech-constraints.md](./tech-constraints.md) | 技术约束和规范 |
| [autofill.md](../../docs/architecture/autofill.md) | 智能填单设计 |
| [query_agent_design.md](../../docs/autofill/agent/query_agent_design.md) | Query Agent 设计 |
| [kafka_ai_fill_design.md](../../docs/architecture/kafka_ai_fill_design.md) | Kafka 异步填单设计 |

---

## 12. 更新记录

| 日期 | 版本 | 更新内容 |
|------|------|---------|
| 2026-05-02 | v2.0 | 重构架构文档，添加 Query Agent、LiteLLM 网关、全局异常处理、结构化日志等模块 |
| 2024-XX-XX | v1.0 | 初始版本 |
