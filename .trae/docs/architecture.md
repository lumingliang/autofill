# Vue FastAPI Admin 架构文档

## 1. 项目概述

Vue FastAPI Admin 是一个基于 Vue 3 + FastAPI 的 RBAC（基于角色的访问控制）后台管理系统，支持多租户架构。

### 1.1 项目结构

```
autofill/
├── frontend/          # 前端项目 (Vue 3 + TypeScript) - 当前活跃使用
├── app/               # 后端项目 (FastAPI + Python)
├── web/               # 【已废弃】额外的前端目录，仅作参考保留
├── requirements.txt   # Python 依赖
└── pyproject.toml     # Python 项目配置
```

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
│   └── HelloWorld.vue
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
│   ├── error/             # 错误页面
│   ├── login/             # 登录页
│   ├── profile/           # 个人中心
│   ├── system/            # 系统管理
│   │   ├── api/           # API 管理
│   │   ├── auditlog/      # 审计日志
│   │   ├── dept/          # 部门管理
│   │   ├── menu/          # 菜单管理
│   │   ├── role/          # 角色管理
│   │   ├── tenant/        # 租户管理
│   │   └── user/          # 用户管理
│   ├── top-menu/          # 顶部菜单
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

### 2.4 关键配置

#### Vite 配置

```typescript
// vite.config.ts 关键配置
- 端口: 3200
- 代理: /api -> http://127.0.0.1:9999
- 路径别名: @ -> src
- 插件: Vue, UnoCSS, 自动组件导入
```

#### TypeScript 配置

```typescript
// tsconfig.app.json 关键配置
- strict: true
- moduleResolution: bundler
- 路径映射: @/* -> src/*
```

---

## 3. 后端架构

### 3.1 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | FastAPI | 0.111.0 | Web 框架 |
| 语言 | Python | >=3.11 | 编程语言 |
| ORM | Tortoise ORM | 0.23.0 | 异步 ORM |
| 数据库 | MySQL | - | 主数据库 |
| 迁移工具 | Aerich | 0.8.1 | 数据库迁移 |
| 认证 | PyJWT | 2.10.1 | JWT Token |
| 密码加密 | Argon2 | 23.1.0 | 密码哈希 |
| 数据验证 | Pydantic | 2.10.5 | 数据模型验证 |
| 配置管理 | pydantic-settings | 2.7.1 | 环境配置 |
| 日志 | loguru | 0.7.3 | 日志记录 |
| 代码格式化 | black | 24.10.0 | 代码格式化 |
| 代码检查 | ruff | 0.9.1 | 代码检查 |

### 3.2 目录结构

```
app/
├── api/                    # API 路由层
│   └── v1/                # API 版本 1
│       ├── apis/          # API 管理接口
│       ├── auditlog/      # 审计日志接口
│       ├── base/          # 基础接口（登录等）
│       ├── depts/         # 部门接口
│       ├── menus/         # 菜单接口
│       ├── roles/         # 角色接口
│       ├── tenants/       # 租户接口
│       ├── upload/        # 文件上传接口
│       ├── users/         # 用户接口
│       └── __init__.py    # 路由聚合
├── controllers/            # 控制器层（业务逻辑）
│   ├── api.py             # API 控制器
│   ├── dept.py            # 部门控制器
│   ├── menu.py            # 菜单控制器
│   ├── role.py            # 角色控制器
│   ├── tenant.py          # 租户控制器
│   └── user.py            # 用户控制器
├── core/                   # 核心模块
│   ├── bgtask.py          # 后台任务
│   ├── crud.py            # CRUD 基类
│   ├── ctx.py             # 上下文管理
│   ├── dependency.py      # 依赖注入（认证、权限）
│   ├── exceptions.py      # 异常处理
│   ├── init_app.py        # 应用初始化
│   ├── middlewares.py     # 中间件
│   └── relation.py        # 关联查询工具
├── log/                    # 日志模块
│   └── log.py             # 日志配置
├── models/                 # 数据模型层
│   ├── admin.py           # 业务模型（用户、角色等）
│   ├── base.py            # 基础模型
│   └── enums.py           # 枚举定义
├── schemas/                # Pydantic 数据模型
│   ├── apis.py            # API 模型
│   ├── base.py            # 基础响应模型
│   ├── depts.py           # 部门模型
│   ├── login.py           # 登录模型
│   ├── menus.py           # 菜单模型
│   ├── roles.py           # 角色模型
│   ├── tenants.py         # 租户模型
│   └── users.py           # 用户模型
├── services/               # 服务层
│   └── file_service.py    # 文件服务
├── settings/               # 配置管理
│   └── config.py          # 应用配置
├── utils/                  # 工具函数
│   ├── jwt_utils.py       # JWT 工具
│   └── password.py        # 密码工具
└── __init__.py
```

### 3.3 核心架构模式

#### 3.3.1 分层架构

```
API Layer (api/)
    ↓
Controller Layer (controllers/)
    ↓
Service Layer (services/)
    ↓
Model Layer (models/)
```

#### 3.3.2 CRUD 基类模式

```python
# core/crud.py
class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, id: int) -> ModelType
    async def list(self, page, page_size, search, order) -> Tuple[Total, List[ModelType]]
    async def create(self, obj_in: CreateSchemaType) -> ModelType
    async def update(self, id: int, obj_in: UpdateSchemaType) -> ModelType
    async def remove(self, id: int) -> None
```

#### 3.3.3 关联查询模式

```python
# core/relation.py
class RelationQuery:
    """所有多对多/一对多关系查询统一走这里"""

    # 用户-角色关联
    @staticmethod
    async def get_role_ids_by_user_id(user_id: int) -> List[int]
    @staticmethod
    async def replace_user_roles(user_id: int, role_ids: List[int]) -> None

    # 角色-菜单关联
    @staticmethod
    async def get_menu_ids_by_role_id(role_id: int) -> List[int]

    # 角色-API 关联
    @staticmethod
    async def get_api_ids_by_role_id(role_id: int) -> List[int]
```

#### 3.3.4 依赖注入模式

```python
# core/dependency.py
class AuthControl:
    @classmethod
    async def is_authed(cls, token: str = Header(...)) -> Optional["User"]

class PermissionControl:
    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed))

DependAuth = Depends(AuthControl.is_authed)
DependPermission = Depends(PermissionControl.has_permission)
```

### 3.4 数据模型

#### 3.4.1 核心实体

```
User (用户)
├── id, username, email, password
├── is_active, is_superuser
├── dept_id (部门)
├── current_tenant_id (当前租户)
└── 关联: roles, tenants

Role (角色)
├── id, name, desc
├── tenant_id (所属租户)
└── 关联: users, menus, apis

Tenant (租户)
├── id, name, domain
└── 关联: users, roles

Menu (菜单)
├── id, name, path, component
├── menu_type (catalog/menu)
├── parent_id, order
└── 关联: roles

Api (接口)
├── id, path, method, summary, tags
└── 关联: roles

Dept (部门)
├── id, name, parent_id
└── 关联: users

AuditLog (审计日志)
├── user_id, username, module
├── method, path, status
└── request_args, response_body
```

#### 3.4.2 关联表

```
UserRole: user_id <-> role_id
RoleMenu: role_id <-> menu_id
RoleApi: role_id <-> api_id
UserTenant: user_id <-> tenant_id
DeptClosure: ancestor <-> descendant (部门层级)
```

### 3.5 中间件栈

```python
# 中间件执行顺序（从上到下）
1. CORSMiddleware          # 跨域处理
2. RequestIdMiddleware     # 请求 ID 追踪
3. RequestLoggingMiddleware # 请求日志
4. BackGroundTaskMiddleware # 后台任务
5. HttpAuditLogMiddleware  # 审计日志
```

---

## 4. 前后端交互

### 4.1 API 规范

#### 4.1.1 响应格式

```typescript
// 成功响应
{
  code: 200,
  msg: "success",
  data: T
}

// 列表响应
{
  code: 200,
  msg: "success",
  data: T[],
  total: number,
  page: number,
  page_size: number
}

// 错误响应
{
  code: 400 | 401 | 403 | 404 | 500,
  msg: "错误信息",
  error?: any
}
```

#### 4.1.2 认证方式

```
Header: token=<JWT_TOKEN>
```

#### 4.1.3 核心 API 列表

```
# 认证
POST /api/v1/base/access_token        # 登录
POST /api/v1/base/select_tenant       # 切换租户
GET  /api/v1/base/userinfo            # 获取用户信息
GET  /api/v1/base/usermenu            # 获取用户菜单
GET  /api/v1/base/userapi             # 获取用户 API 权限

# 用户管理
GET    /api/v1/user/list              # 用户列表
GET    /api/v1/user/get               # 用户详情
POST   /api/v1/user/create            # 创建用户
POST   /api/v1/user/update            # 更新用户
DELETE /api/v1/user/delete            # 删除用户
POST   /api/v1/user/reset_password    # 重置密码

# 角色管理
GET    /api/v1/role/list              # 角色列表
POST   /api/v1/role/create            # 创建角色
POST   /api/v1/role/update            # 更新角色
DELETE /api/v1/role/delete            # 删除角色
POST   /api/v1/role/authorized        # 授权菜单/API

# 菜单管理
GET    /api/v1/menu/list              # 菜单列表
POST   /api/v1/menu/create            # 创建菜单
POST   /api/v1/menu/update            # 更新菜单
DELETE /api/v1/menu/delete            # 删除菜单

# API 管理
GET    /api/v1/api/list               # API 列表
POST   /api/v1/api/create             # 创建 API
POST   /api/v1/api/update             # 更新 API
DELETE /api/v1/api/delete             # 删除 API
POST   /api/v1/api/refresh            # 刷新 API

# 部门管理
GET    /api/v1/dept/list              # 部门列表
POST   /api/v1/dept/create            # 创建部门
POST   /api/v1/dept/update            # 更新部门
DELETE /api/v1/dept/delete            # 删除部门

# 租户管理
GET    /api/v1/tenant/list            # 租户列表
POST   /api/v1/tenant/create          # 创建租户
POST   /api/v1/tenant/update          # 更新租户
DELETE /api/v1/tenant/delete          # 删除租户

# 审计日志
GET    /api/v1/auditlog/list          # 日志列表
```

### 4.2 数据流

#### 4.2.1 登录流程

```
1. 前端: POST /base/access_token {username, password}
2. 后端: 验证密码 -> 生成 JWT Token
3. 前端: 存储 Token -> 获取用户信息 -> 获取菜单 -> 生成动态路由
4. 前端: 跳转至工作台
```

#### 4.2.2 页面访问流程

```
1. 路由守卫检查 Token
2. 有 Token: 加载动态路由 -> 渲染页面
3. 无 Token: 跳转登录页
4. 页面渲染: 检查 API 权限 (v-permission)
```

#### 4.2.3 CRUD 操作流程

```
列表页:
1. 加载页面 -> 调用 API 获取列表数据
2. 渲染表格 -> 支持分页、筛选、排序
3. 操作: 新增/编辑/删除

表单页:
1. 打开弹窗 -> 表单验证
2. 提交 -> API 调用
3. 刷新列表
```

---

## 5. 多租户架构

### 5.1 租户模型

```
- 超级管理员: is_superuser = true, 可访问所有租户数据
- 租户管理员: role.code = 'tenant_admin', 管理单个租户
- 普通用户: 只能访问所属租户的数据
```

### 5.2 数据隔离

```python
# 后端数据隔离逻辑
if not is_superuser(current_user):
    tenant_user_ids = await RelationQuery.get_user_ids_by_tenant_id(current_user.current_tenant_id)
    q &= Q(id__in=tenant_user_ids)
```

### 5.3 租户切换

```
1. 用户登录后获取所属租户列表
2. 选择租户 -> POST /base/select_tenant
3. 后端生成新的 Token（包含 current_tenant_id）
4. 前端刷新页面，加载新租户的数据
```

---

## 6. 安全架构

### 6.1 认证机制

- **JWT Token**: HS256 算法，有效期 7 天
- **Token 内容**: user_id, current_tenant_id, tenant_domain
- **Token 存储**: 前端 localStorage

### 6.2 权限控制

- **超级管理员**: 绕过所有权限检查
- **角色权限**: 通过 Role-Menu、Role-Api 关联控制
- **前端权限**: v-permission 指令控制按钮显示
- **后端权限**: PermissionControl 中间件控制接口访问

### 6.3 密码安全

- **哈希算法**: Argon2
- **默认密码**: 123456（重置密码时使用）

### 6.4 审计日志

- **记录内容**: 用户、模块、请求方法、路径、参数、响应
- **排除路径**: /base/access_token, /docs, /uploads

---

## 7. 扩展点

### 7.1 前端扩展

```typescript
// 1. 新增页面
// views/{module}/{page}/index.vue

// 2. 新增 API
// api/index.ts 中添加接口定义

// 3. 新增组件
// components/{ComponentName}/index.vue

// 4. 新增 Store
// store/modules/{module}.ts
```

### 7.2 后端扩展

```python
# 1. 新增模型
# models/admin.py 中定义模型

# 2. 新增 Schema
# schemas/{name}.py 中定义 Pydantic 模型

# 3. 新增控制器
# controllers/{name}.py 继承 CRUDBase

# 4. 新增 API
# api/v1/{name}/{name}.py 定义路由

# 5. 注册路由
# api/v1/__init__.py 中导入路由
```

---

## 8. 部署架构

### 8.1 开发环境

```
前端: npm run dev (port 3200)
后端: uvicorn main:app --reload (port 9999)
数据库: MySQL (port 3306)
```

### 8.2 生产环境

```
前端: nginx 静态资源服务
后端: uvicorn + gunicorn
数据库: MySQL
```

---

## 9. 附录

### 9.1 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 前端组件 | PascalCase | UserManagement.vue |
| 前端文件 | camelCase | userManagement.ts |
| 后端文件 | snake_case | user_management.py |
| 后端类 | PascalCase | UserController |
| 后端函数 | snake_case | get_user_list |
| 数据库表 | snake_case | user_role |
| API 路径 | snake_case | /user/list |

### 9.2 代码风格

- **Python**: black (line-length: 120), ruff
- **TypeScript**: 严格模式，类型推断优先
