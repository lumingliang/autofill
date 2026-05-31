# 系统管理模块 - 补充测试用例

本文档包含核心功能测试流程中遗漏的重要测试场景。

---

## 补充一：密码相关功能测试

### 1.1 修改密码 - 旧密码错误

**接口**：`POST /api/v1/base/update_password`

**请求头**：`token: <testuser1_token>`

**请求参数**：
```json
{
  "old_password": "wrongpassword",
  "new_password": "newpassword123"
}
```

**预期响应**：
```json
{
  "code": 400,
  "message": "旧密码验证错误！"
}
```

---

### 1.2 重置密码功能

**前置条件**：使用超级管理员账号

**接口**：`POST /api/v1/users/reset_password`

**请求头**：`token: <admin_token>`

**请求参数**：
```json
{
  "user_id": 4
}
```

**预期响应**：
```json
{
  "code": 200,
  "message": "密码已重置为123456"
}
```

**后续验证**：
- 使用重置后的密码 `123456` 登录，应该成功

---

### 1.3 验证新密码生效

**接口**：`POST /api/v1/base/access_token`

**请求参数**：
```json
{
  "username": "testuser1",
  "password": "newpassword123"
}
```

**预期响应**：登录成功

---

## 补充二：租户切换功能测试

### 2.1 多租户用户选择租户

**前置条件**：用户属于多个租户

**步骤**：

1. 创建第二个租户并分配给同一用户
   - 接口：`POST /api/v1/tenants/add_user`
   - 参数：`tenant_id`, `user_id`

2. 用户选择新租户
   - 接口：`POST /api/v1/base/select_tenant`
   - 请求头：`token: <user_token>`
   - 请求参数：
     ```json
     {
       "tenant_id": 2
     }
     ```

3. 验证返回的新token包含正确的租户信息
   - 检查 `current_tenant_id` 是否为 2

4. 验证用户权限是否切换到新租户
   - 接口：`GET /api/v1/base/usermenu`
   - 验证菜单是否更新为新租户的权限

---

## 补充三：菜单管理CRUD测试

### 3.1 创建菜单

**前置条件**：使用超级管理员

**接口**：`POST /api/v1/menus/create`

**请求头**：`token: <admin_token>`

**请求参数**：
```json
{
  "name": "测试菜单",
  "path": "/test-menu",
  "icon": "test-icon",
  "order": 99,
  "parent_id": 0,
  "component": "test/TestMenu.vue",
  "menu_type": "menu"
}
```

**预期响应**：
```json
{
  "code": 200,
  "message": "Created Success"
}
```

**保存**：记录返回的菜单ID

---

### 3.2 更新菜单

**接口**：`POST /api/v1/menus/update`

**请求头**：`token: <admin_token>`

**请求参数**：
```json
{
  "id": <menu_id>,
  "name": "测试菜单-已更新",
  "order": 100
}
```

**预期响应**：
```json
{
  "code": 200,
  "message": "Updated Success"
}
```

---

### 3.3 删除菜单（无子菜单）

**前置条件**：菜单没有子菜单

**接口**：`DELETE /api/v1/menus/delete`

**请求头**：`token: <admin_token>`

**请求参数**：
- `id`: <menu_id>

**预期响应**：
```json
{
  "code": 200,
  "message": "Deleted Success"
}
```

---

## 补充四：权限深度验证测试

### 4.1 普通用户尝试创建角色（应失败）

**前置条件**：使用普通用户账号

**接口**：`POST /api/v1/roles/create`

**请求头**：`token: <testuser1_token>`

**请求参数**：
```json
{
  "name": "非法创建的角色",
  "tenant_id": 1
}
```

**预期响应**：
```json
{
  "code": 403,
  "message": "您没有权限"
}
```

---

### 4.2 普通用户尝试修改其他用户信息（应失败）

**前置条件**：使用普通用户账号

**接口**：`POST /api/v1/users/update`

**请求头**：`token: <testuser1_token>`

**请求参数**：
```json
{
  "id": 3,
  "alias": "尝试修改其他用户"
}
```

**预期响应**：
```json
{
  "code": 403,
  "message": "您没有权限"
}
```

---

### 4.3 普通用户删除其他用户（应失败）

**前置条件**：使用普通用户账号

**接口**：`DELETE /api/v1/users/delete`

**请求头**：`token: <testuser1_token>`

**请求参数**：
- `user_id`: 3 (其他用户ID)

**预期响应**：
```json
{
  "code": 403,
  "message": "您没有权限"
}
```

---

### 4.4 普通用户尝试访问其他租户数据（应失败）

**前置条件**：用户属于租户A

**步骤**：

1. 使用用户token访问租户B的数据
   - 接口：`GET /api/v1/users/list`
   - 请求头：`token: <tenant_a_user_token>`
   - 请求参数：`tenant_id=2`

2. 预期响应：
   ```json
   {
     "code": 403,
     "message": "您没有该租户的权限"
   }
   ```

---

## 补充五：快捷登录功能测试

### 5.1 超管快捷登录到普通用户

**前置条件**：使用超级管理员

**接口**：`POST /api/v1/base/quick_login`

**请求头**：`token: <admin_token>`

**请求参数**：
```json
{
  "target_user_id": 4
}
```

**预期响应**：
```json
{
  "code": 200,
  "data": {
    "access_token": "...",
    "username": "testuser1",
    "tenants": [...],
    "current_tenant_id": 1
  },
  "message": "Success"
}
```

**验证**：使用返回的token，应该能成功调用需要该用户权限的接口

---

### 5.2 快捷登录到超管（应失败）

**前置条件**：使用普通用户或租户管理员

**接口**：`POST /api/v1/base/quick_login`

**请求头**：`token: <tenant_admin_token>`

**请求参数**：
```json
{
  "target_user_id": 1
}
```

**预期响应**：
```json
{
  "code": 403,
  "message": "不能快捷登录到超级管理员账户"
}
```

---

## 补充六：数据一致性验证

### 6.1 创建用户后验证角色绑定

**步骤**：

1. 创建用户时分配角色
2. 调用接口获取用户详情
   - 接口：`GET /api/v1/users/get`
   - 参数：`user_id`
3. 验证返回的用户信息中包含正确的 `roles` 字段

---

### 6.2 创建角色后验证权限分配

**步骤**：

1. 创建角色并分配菜单/API权限
2. 调用接口获取角色权限
   - 接口：`GET /api/v1/roles/authorized`
   - 参数：`id`
3. 验证返回的 `menus` 和 `apis` 数组包含预期的权限

---

### 6.3 删除数据后验证关联清理

**步骤**：

1. 删除用户
   - 接口：`DELETE /api/v1/users/delete`
2. 验证用户角色关联表中的记录已删除
3. 验证 `user_role` 表中该用户的记录已不存在

---

## 补充七：参数格式验证

### 7.1 用户名格式验证

**步骤**：

1. 尝试创建用户名过短的用户
   - 接口：`POST /api/v1/users/create`
   - 参数：`username: "a"`

2. 预期响应：返回参数验证错误（422或其他错误码）

---

### 7.2 邮箱格式验证

**步骤**：

1. 尝试创建邮箱格式错误的用户
   - 接口：`POST /api/v1/users/create`
   - 参数：`email: "invalid-email"`

2. 预期响应：返回参数验证错误

---

### 7.3 重复邮箱验证

**步骤**：

1. 尝试使用已存在的邮箱创建用户
   - 接口：`POST /api/v1/users/create`
   - 参数：`email: "testadmin@test-company-a.com"` (已存在的邮箱)

2. 预期响应：
   ```json
   {
     "code": 400,
     "message": "该邮箱已被注册"
   }
   ```

---

## 补充八：用户状态管理

### 8.1 禁用用户后登录（应失败）

**前置条件**：使用超级管理员

**步骤**：

1. 禁用用户
   - 接口：`POST /api/v1/users/update`
   - 参数：`id: 4, is_active: false`

2. 尝试用该用户登录
   - 接口：`POST /api/v1/base/access_token`
   - 参数：`username: "testuser1", password: "123456"`

3. 预期响应：
   ```json
   {
     "code": 400,
     "message": "用户已被禁用"
   }
   ```

---

### 8.2 启用用户后登录（应成功）

**前置条件**：用户已被禁用

**步骤**：

1. 启用用户
   - 接口：`POST /api/v1/users/update`
   - 参数：`id: 4, is_active: true`

2. 尝试用该用户登录
   - 预期响应：登录成功

---

## 补充九：API刷新功能

### 9.1 刷新API列表

**前置条件**：使用超级管理员

**接口**：`POST /api/v1/apis/refresh`

**请求头**：无token要求（根据实际实现）

**预期响应**：
```json
{
  "code": 200,
  "message": "OK"
}
```

**后续验证**：
- 查看API列表，确认所有API都已正确注册

---

## 测试执行建议

1. **按顺序执行**：按照补充编号顺序执行测试
2. **记录实际响应**：每个测试记录实际返回的响应，与预期对比
3. **环境隔离**：每个测试用例使用独立的测试数据
4. **失败处理**：发现失败的测试用例，详细记录错误信息
5. **回归验证**：修复问题后重新执行失败的测试用例

---

## 优先级建议

| 优先级 | 测试项 | 原因 |
|--------|--------|------|
| 🔴 必须 | 权限深度验证测试 | 确保权限控制无漏洞 |
| 🔴 必须 | 密码相关功能测试 | 账户安全核心功能 |
| 🔴 必须 | 租户切换功能测试 | 多租户核心功能 |
| 🟡 重要 | 数据一致性验证 | 数据完整性保障 |
| 🟡 重要 | 用户状态管理测试 | 账户管理核心功能 |
| 🟢 可选 | 参数格式验证 | 可通过接口文档约束 |
| 🟢 可选 | 快捷登录功能测试 | 辅助功能 |
