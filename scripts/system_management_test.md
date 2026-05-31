# 系统管理模块 API 测试流程文档

## 概述

本文档描述了系统管理模块的完整 API 测试流程，包括：
1. 超管初始化租户和分配管理员权限
2. 租户管理员管理租户内角色和用户
3. 权限验证和功能测试

## 测试环境准备

1. 确保后端服务正常运行
2. 准备测试数据
3. 获取超级管理员账号（默认：admin/123456）

---

## 第一部分：超级管理员操作

### 1.1 超级管理员登录

**接口**：`POST /api/v1/base/access_token`

**请求参数**：
```json
{
  "username": "admin",
  "password": "123456"
}
```

**预期响应**：
```json
{
  "code": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "username": "admin",
    "tenants": [],
    "need_select_tenant": false,
    "current_tenant_id": 0
  },
  "message": "Success"
}
```

**保存**：保存返回的 `access_token` 用于后续请求。

---

### 1.2 创建新租户

**接口**：`POST /api/v1/tenants/create`

**请求头**：`token: <access_token>`

**请求参数**：
```json
{
  "name": "测试公司A",
  "domain": "test-company-a.com",
  "description": "测试租户A"
}
```

**预期响应**：
```json
{
  "code": 200,
  "data": {
    "tenant": {
      "id": 1,
      "name": "测试公司A",
      "domain": "test-company-a.com",
      "is_active": true,
      "description": "测试租户A",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    },
    "admin_role_id": 2,
    "message": "租户创建成功，已自动创建管理员角色：测试公司A管理员"
  },
  "message": "创建成功"
}
```

**重要说明**：创建租户时，系统会自动：
1. 创建租户记录
2. 自动创建该租户的管理员角色（命名为"租户名+管理员"）
3. 自动为该管理员角色分配所有菜单和API权限
4. 该角色标记为系统角色（is_system=True）

**保存**：记录返回的 `tenant.id` 和 `admin_role_id`。

---

### 1.3 查看租户列表

**接口**：`GET /api/v1/tenants/list`

**请求头**：`token: <access_token>`

**请求参数**：
- `page`: 1
- `page_size`: 10
- `name`: (可选) 租户名称搜索
- `domain`: (可选) 租户域名搜索

**预期响应**：
```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "测试公司A",
      "domain": "test-company-a.com",
      "is_active": true,
      "description": "测试租户A"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "message": "Success"
}
```

---

### 1.4 创建租户管理员用户

**接口**：`POST /api/v1/users/create`

**请求头**：`token: <access_token>`

**请求参数**：
```json
{
  "username": "testadmin",
  "email": "testadmin@test-company-a.com",
  "password": "123456",
  "alias": "测试管理员",
  "role_ids": [2],
  "tenant_id": 1
}
```

**预期响应**：
```json
{
  "code": 200,
  "message": "创建成功"
}
```

---

### 1.5 查看角色权限

**接口**：`GET /api/v1/roles/authorized`

**请求头**：`token: <access_token>`

**请求参数**：
- `id`: 2 (刚才创建的管理员角色ID)

**预期响应**：
```json
{
  "code": 200,
  "data": {
    "id": 2,
    "name": "测试公司A管理员",
    "desc": "测试公司A租户的管理员角色，拥有所有权限",
    "tenant_id": 1,
    "is_system": true,
    "menus": [/* 所有菜单 */],
    "apis": [/* 所有API */]
  },
  "message": "Success"
}
```

---

### 1.6 验证超级管理员其他功能

#### 1.6.1 更新租户信息

**接口**：`POST /api/v1/tenants/update`

**请求参数**：
```json
{
  "id": 1,
  "name": "测试公司A-已更新",
  "description": "更新后的描述"
}
```

#### 1.6.2 查看菜单列表

**接口**：`GET /api/v1/menus/list`

**请求参数**：
- `page`: 1
- `page_size`: 100

#### 1.6.3 查看API列表

**接口**：`GET /api/v1/apis/list`

**请求参数**：
- `page`: 1
- `page_size`: 100

---

## 第二部分：租户管理员操作

### 2.1 租户管理员登录

**接口**：`POST /api/v1/base/access_token`

**请求参数**：
```json
{
  "username": "testadmin",
  "password": "123456"
}
```

**预期响应**：
```json
{
  "code": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "username": "testadmin",
    "tenants": [
      {
        "id": 1,
        "name": "测试公司A-已更新",
        "domain": "test-company-a.com"
      }
    ],
    "need_select_tenant": false,
    "current_tenant_id": 1
  },
  "message": "Success"
}
```

**保存**：保存新的 `access_token`。

---

### 2.2 获取用户信息和菜单

#### 2.2.1 获取用户信息

**接口**：`GET /api/v1/base/userinfo`

**请求头**：`token: <tenant_admin_token>`

**预期响应**：包含用户信息、租户列表、当前租户ID。

#### 2.2.2 获取用户菜单

**接口**：`GET /api/v1/base/usermenu`

**请求头**：`token: <tenant_admin_token>`

**预期响应**：返回该租户管理员有权限的菜单树结构。

#### 2.2.3 获取用户API权限

**接口**：`GET /api/v1/base/userapi`

**请求头**：`token: <tenant_admin_token>`

**预期响应**：返回该租户管理员有权限的API列表。

---

### 2.3 创建租户内自定义角色

**接口**：`POST /api/v1/roles/create`

**请求头**：`token: <tenant_admin_token>`

**请求参数**：
```json
{
  "name": "普通用户",
  "desc": "租户内普通用户角色",
  "tenant_id": 1
}
```

**预期响应**：
```json
{
  "code": 200,
  "message": "创建成功"
}
```

---

### 2.4 查看菜单和API列表（租户管理员视角）

#### 2.4.1 查看菜单列表

**接口**：`GET /api/v1/menus/list`

**请求头**：`token: <tenant_admin_token>`

**预期响应**：租户管理员只能看到自己有权限的菜单。

#### 2.4.2 查看API列表

**接口**：`GET /api/v1/apis/list`

**请求头**：`token: <tenant_admin_token>`

**预期响应**：租户管理员只能看到自己有权限的API。

**保存**：记录一些菜单ID和API code，用于后续权限分配。

---

### 2.5 给新角色分配菜单和API权限

**接口**：`POST /api/v1/roles/authorized`

**请求头**：`token: <tenant_admin_token>`

**请求参数**：
```json
{
  "id": 3, // 刚才创建的"普通用户"角色ID
  "menu_ids": [1, 2, 3], // 选择一些菜单ID
  "api_codes": [
    "get/api/v1/base/userinfo",
    "get/api/v1/base/usermenu"
  ] // 选择一些API code
}
```

**预期响应**：
```json
{
  "code": 200,
  "message": "更新成功"
}
```

---

### 2.6 验证角色权限

**接口**：`GET /api/v1/roles/authorized`

**请求头**：`token: <tenant_admin_token>`

**请求参数**：
- `id`: 3

**预期响应**：确认菜单和API权限已正确分配。

---

### 2.7 创建租户内普通用户

**接口**：`POST /api/v1/users/create`

**请求头**：`token: <tenant_admin_token>`

**请求参数**：
```json
{
  "username": "testuser1",
  "email": "testuser1@test-company-a.com",
  "password": "123456",
  "alias": "测试用户1",
  "role_ids": [3],
  "tenant_id": 1
}
```

**预期响应**：
```json
{
  "code": 200,
  "message": "创建成功"
}
```

---

### 2.8 查看用户列表

**接口**：`GET /api/v1/users/list`

**请求头**：`token: <tenant_admin_token>`

**请求参数**：
- `page`: 1
- `page_size`: 10

**预期响应**：
```json
{
  "code": 200,
  "data": [
    {
      "id": 3,
      "username": "testadmin",
      "alias": "测试管理员",
      "email": "testadmin@test-company-a.com",
      "roles": [/* 角色信息 */]
    },
    {
      "id": 4,
      "username": "testuser1",
      "alias": "测试用户1",
      "email": "testuser1@test-company-a.com",
      "roles": [/* 角色信息 */]
    }
  ],
  "total": 2,
  "message": "Success"
}
```

---

### 2.9 更新用户角色（可选）

**接口**：`POST /api/v1/users/update_tenant_roles`

**请求头**：`token: <tenant_admin_token>`

**请求参数**：
```json
{
  "user_id": 4,
  "role_ids": [3, 2], // 可同时分配多个角色
  "tenant_id": 1
}
```

---

### 2.10 验证租户管理员其他功能

#### 2.10.1 更新用户信息

**接口**：`POST /api/v1/users/update`

**请求参数**：
```json
{
  "id": 4,
  "alias": "测试用户1-已更新",
  "phone": "13800138000"
}
```

#### 2.10.2 查看角色列表

**接口**：`GET /api/v1/roles/list`

**请求参数**：
- `page`: 1
- `page_size`: 10

---

## 第三部分：租户普通用户操作

### 3.1 普通用户登录

**接口**：`POST /api/v1/base/access_token`

**请求参数**：
```json
{
  "username": "testuser1",
  "password": "123456"
}
```

**保存**：保存返回的 `access_token`。

---

### 3.2 验证权限

#### 3.2.1 获取用户信息（应该有权限）

**接口**：`GET /api/v1/base/userinfo`

**请求头**：`token: <testuser1_token>`

**预期响应**：成功返回用户信息。

#### 3.2.2 获取用户菜单（应该有权限）

**接口**：`GET /api/v1/base/usermenu`

**请求头**：`token: <testuser1_token>`

**预期响应**：返回分配的菜单。

#### 3.2.3 尝试访问未授权的接口（应该失败）

**接口**：`GET /api/v1/users/list`

**请求头**：`token: <testuser1_token>`

**预期响应**：返回 403 错误或权限不足。

---

### 3.3 修改密码

**接口**：`POST /api/v1/base/update_password`

**请求头**：`token: <testuser1_token>`

**请求参数**：
```json
{
  "old_password": "123456",
  "new_password": "newpassword123"
}
```

**预期响应**：
```json
{
  "code": 200,
  "message": "密码修改成功"
}
```

---

## 第四部分：高级测试场景

### 4.1 验证权限隔离

1. 创建第二个租户"测试公司B"
2. 为第二个租户创建管理员用户
3. 用第二个租户管理员登录，验证无法看到第一个租户的信息
4. 验证角色、用户等数据的租户隔离

---

### 4.2 多角色权限叠加测试

1. 为一个用户分配多个角色
2. 验证用户拥有所有角色权限的并集

---

### 4.3 权限缓存测试

1. 更新用户角色权限
2. 验证用户权限是否实时更新（检查权限缓存服务是否正常工作）

---

### 4.4 边界测试

#### 4.4.1 创建重复租户域名

**接口**：`POST /api/v1/tenants/create`

**请求参数**：使用已存在的域名

**预期响应**：返回错误，提示域名已存在。

#### 4.4.2 创建重复用户名

**接口**：`POST /api/v1/users/create`

**请求参数**：使用已存在的用户名

**预期响应**：返回错误。

#### 4.4.3 删除有子菜单的菜单

**接口**：`DELETE /api/v1/menus/delete`

**请求参数**：删除有子菜单的菜单ID

**预期响应**：返回错误，提示不能删除有子菜单的菜单。

---

### 4.5 清理测试数据

测试完成后，按照以下顺序清理测试数据：

#### 4.5.1 租户管理员清理租户内数据

**前提**：使用租户管理员账号登录

**步骤**：

1. **删除租户内普通用户**：
   - 接口：`DELETE /api/v1/users/delete`
   - 参数：`user_id` 为测试用户ID

2. **删除租户内自定义角色**（非系统角色）：
   - 接口：`DELETE /api/v1/roles/delete`
   - 参数：`id` 为自定义角色ID
   - 注意：不能删除系统自动创建的租户管理员角色（is_system=True）

3. **验证清理结果**：
   - 查看用户列表，确认普通用户已删除
   - 查看角色列表，确认自定义角色已删除

---

#### 4.5.2 超级管理员删除租户

**前提**：使用超级管理员账号登录

**步骤**：

1. **查看租户下的所有用户**：
   - 接口：`GET /api/v1/tenants/users`
   - 参数：`tenant_id`

2. **移除租户下的所有用户**：
   - 接口：`POST /api/v1/tenants/remove_user`
   - 参数：`tenant_id` 和 `user_id`
   - 对每个租户用户执行此操作

3. **删除租户**：
   - 接口：`DELETE /api/v1/tenants/delete`
   - 参数：`tenant_id`
   - 注意：删除租户会级联删除该租户下的所有角色（包括系统自动创建的管理员角色）

4. **验证清理结果**：
   - 查看租户列表，确认测试租户已删除

---

## 附录：API 参考汇总

### 租户管理
- `GET /api/v1/tenants/list` - 查看租户列表
- `GET /api/v1/tenants/get` - 查看租户详情
- `POST /api/v1/tenants/create` - 创建租户
- `POST /api/v1/tenants/update` - 更新租户
- `DELETE /api/v1/tenants/delete` - 删除租户
- `GET /api/v1/tenants/users` - 获取租户用户
- `POST /api/v1/tenants/add_user` - 添加用户到租户
- `POST /api/v1/tenants/remove_user` - 从租户移除用户

### 用户管理
- `GET /api/v1/users/list` - 查看用户列表
- `GET /api/v1/users/get` - 查看用户详情
- `POST /api/v1/users/create` - 创建用户
- `POST /api/v1/users/update` - 更新用户
- `DELETE /api/v1/users/delete` - 删除用户
- `POST /api/v1/users/reset_password` - 重置密码
- `GET /api/v1/users/my_tenants` - 获取我的租户
- `POST /api/v1/users/select_tenant` - 选择租户
- `GET /api/v1/users/tenant_roles` - 获取租户角色
- `GET /api/v1/users/tenant_assigned_roles` - 获取用户在租户的角色
- `POST /api/v1/users/update_tenant_roles` - 更新用户租户角色

### 角色管理
- `GET /api/v1/roles/list` - 查看角色列表
- `GET /api/v1/roles/get` - 查看角色详情
- `POST /api/v1/roles/create` - 创建角色
- `POST /api/v1/roles/update` - 更新角色
- `DELETE /api/v1/roles/delete` - 删除角色
- `GET /api/v1/roles/authorized` - 查看角色权限
- `POST /api/v1/roles/authorized` - 更新角色权限
- `GET /api/v1/roles/users` - 获取角色用户
- `GET /api/v1/roles/available_users` - 获取可分配用户
- `POST /api/v1/roles/assign_users` - 分配用户给角色

### 菜单管理
- `GET /api/v1/menus/list` - 查看菜单列表
- `GET /api/v1/menus/get` - 查看菜单详情
- `POST /api/v1/menus/create` - 创建菜单
- `POST /api/v1/menus/update` - 更新菜单
- `DELETE /api/v1/menus/delete` - 删除菜单

### API 管理
- `GET /api/v1/apis/list` - 查看 API 列表
- `GET /api/v1/apis/get` - 查看 API 详情
- `POST /api/v1/apis/create` - 创建 API
- `POST /api/v1/apis/update` - 更新 API
- `DELETE /api/v1/apis/delete` - 删除 API
- `POST /api/v1/apis/refresh` - 刷新 API 列表

### 基础功能
- `POST /api/v1/base/access_token` - 登录获取 token
- `POST /api/v1/base/select_tenant` - 选择租户获取 token
- `GET /api/v1/base/userinfo` - 获取用户信息
- `GET /api/v1/base/usermenu` - 获取用户菜单
- `GET /api/v1/base/userapi` - 获取用户 API
- `POST /api/v1/base/update_password` - 修改密码
- `POST /api/v1/base/quick_login` - 快捷登录
