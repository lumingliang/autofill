# 登录流程设计文档

## 概述

本文档描述了 Vue FastAPI Admin 系统的两种登录流程：
1. **标准登录** - 用户输入账号密码登录
2. **快捷登录** - 具有权限的用户可以快速切换到其他用户账号

## 核心设计思想

### 统一的数据格式

所有登录流程（标准登录、快捷登录、返回原用户）都使用统一的 `pending_auth` 数据格式：

```typescript
interface PendingAuth {
  token: string;              // access_token
  tenants: Tenant[];          // 租户列表
  needSelectTenant: boolean;  // 是否需要选择租户
  currentTenantId: number;    // 当前租户ID
  isQuickLogin: boolean;      // 是否是快捷登录
  targetUser?: string;        // 快捷登录目标用户（可选）
}
```

### 统一的处理入口

登录页面通过检查 `localStorage` 中的 `pending_auth` 来统一处理所有登录场景。

---

## 标准登录流程

### 流程图

```
┌─────────────────┐
│   访问登录页面   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     有      ┌─────────────────┐
│ 检查pending_auth │────────────▶│ handlePendingAuth│
└────────┬────────┘             └─────────────────┘
         │ 无
         ▼
┌─────────────────┐
│  显示登录表单    │
│ 等待用户输入     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  用户点击登录    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   API: login    │
│ 获取token和租户  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 需要选择租户?    │────是────┐
└────────┬────────┘          │
         │ 否                ▼
         │           ┌─────────────────┐
         │           │ 显示租户选择弹窗  │
         │           │ 等待用户选择     │
         │           └────────┬────────┘
         │                    │
         │           ┌────────▼────────┐
         │           │ API: selectTenant│
         │           │ 获取新token     │
         │           └────────┬────────┘
         │                    │
         └────────────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  completeLogin  │
                 │  设置token      │
                 │  加载动态路由   │
                 │  跳转到首页     │
                 └─────────────────┘
```

### 代码实现

#### 登录页面 (login/index.vue)

```javascript
// 页面加载时检查是否有待处理的登录
onMounted(() => {
  const pendingAuth = lStorage.get('pending_auth')
  if (pendingAuth) {
    handlePendingAuth(pendingAuth)
  }
})

// 标准登录
async function handleLogin() {
  const { username, password } = loginInfo.value
  if (!username || !password) {
    $message.warning('请输入用户名和密码')
    return
  }
  
  loading.value = true
  const res = await api.login({ username, password: password.toString() })
  lStorage.set('loginInfo', { username, password })
  
  const { access_token, tenants, need_select_tenant, current_tenant_id } = res.data
  
  // 检查是否需要选择租户
  if (need_select_tenant && tenants?.length > 1 && !current_tenant_id) {
    pendingToken.value = access_token
    tenantOptions.value = tenants
    showTenantModal.value = true
    loading.value = false
    return
  }
  
  await completeLogin(access_token)
}

// 选择租户后完成登录
async function handleSelectTenant() {
  if (!selectedTenantId.value) {
    $message.warning('请选择租户')
    return false
  }
  
  loading.value = true
  setToken(pendingToken.value)
  const res = await api.selectTenant({ tenant_id: selectedTenantId.value })
  await completeLogin(res.data.access_token)
}

// 统一完成登录
async function completeLogin(token) {
  setToken(token)
  $message.success('登录成功')
  await addDynamicRoutes()
  router.push('/')
}
```

### API 接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/base/login` | POST | 用户登录，返回 token 和租户信息 |
| `/base/select_tenant` | POST | 选择租户后获取新的 token |

### 登录响应数据

```json
{
  "code": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "tenants": [
      { "id": 1, "name": "测试租户A" },
      { "id": 2, "name": "测试租户B" }
    ],
    "need_select_tenant": true,
    "current_tenant_id": null
  }
}
```

---

## 快捷登录流程

### 流程图

```
┌─────────────────┐
│  用户管理页面    │
│ 点击快捷登录按钮 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API: quickLogin │
│ 获取目标用户token │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 保存original_token│
│ 用于返回原用户   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 构建pending_auth │
│ 保存到localStorage│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ logoutWithoutRedirect│
│ 清除当前登录状态 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  跳转到登录页面  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 登录页自动检测   │
│ pending_auth    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ handlePendingAuth│
│ 设置快捷登录标记 │
│ 处理租户选择     │
│ 完成登录         │
└─────────────────┘
```

### 代码实现

#### 用户管理页面 (system/user/index.vue)

```javascript
async function handleQuickLogin(row) {
  const userStore = useUserStore()

  // 不能快捷登录到自己
  if (userStore.userId === row.id) {
    $message.error('不能快捷登录到当前用户！')
    return
  }

  const res = await api.quickLogin({ target_user_id: row.id })

  if (res.code === 200) {
    const { access_token, tenants, need_select_tenant, current_tenant_id } = res.data

    // 保存原始用户的token（用于返回）
    const originalToken = lStorage.get('access_token')
    lStorage.set('original_token', originalToken)

    // 构建待验证的登录信息
    const pendingAuth = {
      token: access_token,
      tenants,
      needSelectTenant: need_select_tenant,
      currentTenantId: current_tenant_id,
      isQuickLogin: true,
      targetUser: row.username
    }
    lStorage.set('pending_auth', JSON.stringify(pendingAuth))

    // 触发退出登录
    await userStore.logoutWithoutRedirect()

    // 跳转到登录页
    router.push('/login')
  }
}
```

#### 登录页面处理 (login/index.vue)

```javascript
async function handlePendingAuth(authData) {
  loading.value = true
  const { token, tenants, needSelectTenant, currentTenantId, isQuickLogin, targetUser } = JSON.parse(authData)
  
  // 清除待验证数据
  lStorage.remove('pending_auth')
  
  // 标记快捷登录模式
  if (isQuickLogin) {
    lStorage.set('quick_login_mode', 'true')
    lStorage.set('quick_login_target', targetUser)
  }
  
  // 检查是否需要选择租户
  if (needSelectTenant && tenants?.length > 1 && !currentTenantId) {
    pendingToken.value = token
    tenantOptions.value = tenants
    showTenantModal.value = true
    loading.value = false
    return
  }
  
  // 直接完成登录
  await completeLogin(token)
}
```

#### Header 组件显示快捷登录状态 (layout/components/header/index.vue)

```javascript
const isQuickLoginMode = ref(false)
const quickLoginTarget = ref('')

onMounted(() => {
  // 检查是否处于快捷登录模式
  const quickLoginMode = lStorage.get('quick_login_mode')
  const target = lStorage.get('quick_login_target')
  if (quickLoginMode === 'true' && target) {
    isQuickLoginMode.value = true
    quickLoginTarget.value = target
  }
})
```

### 返回原用户流程

```javascript
async function handleReturnToOriginal() {
  const originalToken = lStorage.get('original_token')
  if (!originalToken) {
    $message.error('无法返回原用户，请重新登录')
    router.push('/login')
    return
  }

  // 获取原用户信息（用于判断是否需要选择租户）
  setToken(originalToken)
  const res = await api.getUserInfo()

  // 构建待验证的登录信息
  const pendingAuth = {
    token: originalToken,
    tenants: res.data.tenants,
    needSelectTenant: res.data.tenants?.length > 1 && !res.data.current_tenant_id,
    currentTenantId: res.data.current_tenant_id,
    isQuickLogin: false
  }
  lStorage.set('pending_auth', JSON.stringify(pendingAuth))

  // 清除快捷登录标记
  lStorage.remove('quick_login_mode')
  lStorage.remove('quick_login_target')
  lStorage.remove('original_token')

  // 触发退出登录
  await userStore.logoutWithoutRedirect()

  // 跳转到登录页
  router.push('/login')
}
```

### API 接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/users/quick_login` | POST | 快捷登录到指定用户 |
| `/users/info` | GET | 获取当前用户信息 |

### 快捷登录响应数据

```json
{
  "code": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "tenants": [
      { "id": 1, "name": "测试租户A" },
      { "id": 2, "name": "测试租户B" }
    ],
    "need_select_tenant": true,
    "current_tenant_id": null
  }
}
```

---

## LocalStorage 数据管理

### 使用的 Key

| Key | 用途 | 生命周期 |
|-----|------|----------|
| `access_token` | 当前登录用户的 token | 登录期间持续存在 |
| `loginInfo` | 保存用户名密码（记住密码） | 长期保存 |
| `pending_auth` | 待处理的登录信息 | 登录处理完成后删除 |
| `original_token` | 原用户的 token（快捷登录用） | 快捷登录期间存在 |
| `quick_login_mode` | 标记是否处于快捷登录模式 | 快捷登录期间存在 |
| `quick_login_target` | 快捷登录目标用户名 | 快捷登录期间存在 |

### 数据清理

- `pending_auth`：在 `handlePendingAuth` 处理完成后立即删除
- `quick_login_mode`、`quick_login_target`、`original_token`：在返回原用户时删除

---

## 安全性考虑

1. **Token 安全**：所有 token 都存储在 localStorage 中，需要配合 HTTPS 使用
2. **权限校验**：快捷登录接口需要校验用户是否有权限进行快捷登录
3. **租户隔离**：切换租户后重新生成 token，确保数据隔离
4. **快捷登录标记**：使用 `quick_login_mode` 标记快捷登录状态，防止误操作

---

## 文件结构

```
web/src/
├── views/
│   └── login/
│       └── index.vue          # 登录页面（统一处理所有登录场景）
├── views/system/
│   └── user/
│       └── index.vue          # 用户管理（快捷登录按钮）
├── layout/components/
│   └── header/
│       └── index.vue          # Header（快捷登录状态、返回原用户）
├── store/modules/
│   └── user/
│       └── index.js           # User Store（登录状态管理）
└── api/
    └── index.js               # API 封装
```

---

## 总结

### 设计优点

1. **统一入口**：所有登录场景都通过 `pending_auth` 统一处理
2. **代码复用**：租户选择逻辑只需实现一次
3. **流程清晰**：标准登录和快捷登录流程分离但共享核心逻辑
4. **易于维护**：新增登录场景只需构建 `pending_auth` 数据

### 核心函数

| 函数 | 位置 | 职责 |
|------|------|------|
| `handlePendingAuth` | login/index.vue | 统一处理所有登录场景 |
| `handleLogin` | login/index.vue | 标准登录流程 |
| `handleSelectTenant` | login/index.vue | 租户选择后完成登录 |
| `completeLogin` | login/index.vue | 统一完成登录 |
| `handleQuickLogin` | system/user/index.vue | 触发快捷登录 |
| `handleReturnToOriginal` | layout/header/index.vue | 返回原用户 |
| `logoutWithoutRedirect` | store/user/index.js | 退出登录不跳转 |
