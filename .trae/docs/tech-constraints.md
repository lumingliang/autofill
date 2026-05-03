# Vue FastAPI Admin 技术约束文档

> 本文档用于指导 AI 自动生成代码，必须严格遵守以下约束。

---

## 1. 前端技术约束

### 1.1 框架约束

#### Vue 3 组合式 API 规范

```typescript
// ✅ 正确：使用 <script setup> 语法
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

// 组件名定义
defineOptions({ name: '组件名称' })

// Props 定义
const props = withDefaults(defineProps<{
  title: string
  visible?: boolean
}>(), {
  visible: false
})

// Emits 定义
const emit = defineEmits<{
  update: [value: string]
  submit: []
}>()

// 响应式数据
const loading = ref(false)
const formData = reactive<FormType>({ name: '' })

// 计算属性
const displayTitle = computed(() => props.title || '默认标题')

// 生命周期
onMounted(() => {
  initData()
})

// 方法
async function initData() {
  // 实现
}
</script>
```

#### 禁止使用

```typescript
// ❌ 错误：Options API
export default {
  data() { return {} },
  methods: {}
}

// ❌ 错误：不使用 TypeScript
<script setup>

// ❌ 错误：不使用类型定义
const data = ref({})
```

### 1.2 状态管理约束

#### Pinia Store 规范

```typescript
// ✅ 正确：使用 Setup Store 语法
// store/modules/{module}.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  // State
  const userInfo = ref<Record<string, any>>({})
  
  // Getters
  const isSuperUser = computed(() => userInfo.value?.is_superuser)
  
  // Actions
  async function getUserInfo() {
    // 实现
  }
  
  return {
    userInfo,
    isSuperUser,
    getUserInfo
  }
})
```

#### Store 使用规范

```typescript
// ✅ 正确：在组件中使用
<script setup lang="ts">
import { useUserStore, usePermissionStore } from '@/store'

const userStore = useUserStore()
const permissionStore = usePermissionStore()

// 访问 state
console.log(userStore.userInfo)

// 访问 getter
console.log(userStore.isSuperUser)

// 调用 action
await userStore.getUserInfo()
</script>
```

### 1.3 组件约束

#### 组件文件结构

```vue
<template>
  <!-- 模板内容 -->
</template>

<script setup lang="ts">
// 1. 导入（按顺序：Vue/Pinia/第三方/本地）
// 2. defineOptions
// 3. Props/Emits 定义
// 4. 注入（store、router 等）
// 5. 响应式数据
// 6. 计算属性
// 7. 监听
// 8. 生命周期
// 9. 方法
</script>

<style scoped lang="less">
/* 样式 */
</style>
```

#### 组件 Props 约束

```typescript
// ✅ 正确：使用接口定义复杂 Props
interface UserInfo {
  id: number
  name: string
  email?: string
}

const props = withDefaults(defineProps<{
  user: UserInfo
  loading?: boolean
  size?: 'small' | 'middle' | 'large'
}>(), {
  loading: false,
  size: 'middle'
})
```

### 1.4 API 调用约束

#### 统一 API 封装

```typescript
// ✅ 正确：使用封装的 request
import request from '@/utils/request'

// 所有 API 定义在 api/index.ts
export default {
  getUserList: (params: any = {}) => request.get('/user/list', { params }),
  createUser: (data: any = {}) => request.post('/user/create', data),
  updateUser: (data: any = {}) => request.post('/user/update', data),
  deleteUser: (params: any = {}) => request.delete('/user/delete', { params }),
}
```

#### 请求响应处理

```typescript
// ✅ 正确：统一错误处理在 request.ts 拦截器中
// 组件中只需处理业务逻辑
async function fetchData() {
  loading.value = true
  try {
    const res: any = await api.getUserList(queryParams)
    tableData.value = res.data
    pagination.total = res.total
  } finally {
    loading.value = false
  }
}
```

### 1.5 样式约束

#### 使用 UnoCSS

```vue
<template>
  <!-- ✅ 正确：使用 UnoCSS 原子类 -->
  <div class="flex items-center justify-between p-4 bg-white rounded">
    <span class="text-lg font-bold text-gray-800">标题</span>
    <a-button type="primary">按钮</a-button>
  </div>
</template>
```

#### Less 样式规范

```less
// ✅ 正确：使用 scoped + less
<style scoped lang="less">
.user-page {
  padding: 16px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 16px;
  }
}
</style>
```

### 1.6 权限指令约束

```vue
<template>
  <!-- ✅ 正确：使用 v-permission 指令 -->
  <a-button v-permission="'post/api/v1/user/create'" type="primary">
    新增用户
  </a-button>
  
  <!-- 权限格式: {method}/{api_path} -->
  <!-- GET -> get, POST -> post, DELETE -> delete -->
</template>
```

### 1.7 路由约束

#### 静态路由

```typescript
// router/routes.ts
export const routes: RouteRecordRaw[] = [
  {
    path: '/system/user',
    name: '用户管理',
    component: markRaw(Layout),
    meta: { 
      title: '用户管理', 
      icon: 'icon-park-outline:user',
      order: 1 
    },
    children: [
      {
        path: '',
        name: '用户管理Default',
        component: () => import('@/views/system/user/index.vue'),
        meta: { 
          title: '用户管理',
          keepAlive: true 
        },
      },
    ],
  },
]
```

#### 动态路由组件路径

```typescript
// ✅ 正确：组件路径映射规则
// 后端返回: { component: '/system/user' }
// 前端映射: /src/views/system/user/index.vue

const componentPath = `/src/views${child.component}/index.vue`
```

---

## 2. 后端技术约束

### 2.1 Python 代码规范

#### 基础规范

```python
# ✅ 正确：使用 black 格式化 (line-length: 120)
# ✅ 正确：使用 ruff 检查

# 导入顺序
import os  # 标准库
from typing import List, Optional  # 类型提示

from fastapi import APIRouter  # 第三方库
from tortoise import fields

from app.models import User  # 本地模块
from app.schemas.users import UserCreate
```

#### 类型注解强制使用

```python
# ✅ 正确：所有函数参数和返回值必须加类型注解
async def get_user_by_id(user_id: int) -> Optional[User]:
    return await User.filter(id=user_id).first()

# ✅ 正确：复杂类型使用 typing
from typing import List, Dict, Tuple

async def list_users(
    page: int, 
    page_size: int
) -> Tuple[int, List[User]]:
    total = await User.all().count()
    users = await User.all().offset((page - 1) * page_size).limit(page_size)
    return total, users
```

### 2.2 模型约束

#### Tortoise ORM 模型规范

> **⚠️ 重要约束**: 禁止使用 Tortoise ORM 的隐式关系查询（如 `user.roles`、`role.users` 等）。
> 所有一对多、多对多关系查询必须通过显式定义的 `RelationQuery` 类方法进行。

```python
# models/admin.py
from tortoise import fields
from app.models.base import BaseModel, TimestampMixin

class User(BaseModel, TimestampMixin):
    """用户模型"""
    username = fields.CharField(max_length=20, unique=True, description="用户名称", index=True)
    email = fields.CharField(max_length=255, unique=True, description="邮箱", index=True)
    is_active = fields.BooleanField(default=True, description="是否激活", index=True)
    
    # ❌ 禁止定义隐式关系字段
    # roles: fields.ManyToManyRelation["Role"]  # 禁止！
    
    class Meta:
        table = "user"  # 表名使用单数小写
```

#### 关系查询规范

```python
# ✅ 正确：使用 RelationQuery 进行显式关联查询
from app.core.relation import RelationQuery

# 获取用户的角色ID列表
role_ids = await RelationQuery.get_role_ids_by_user_id(user_id)

# 获取角色的用户ID列表
user_ids = await RelationQuery.get_user_ids_by_role_id(role_id)

# 更新关联关系
await RelationQuery.replace_user_roles(user_id, role_ids)

# ❌ 错误：禁止使用隐式关系查询
user = await User.get(id=user_id)
roles = await user.roles  # 禁止！
for role in await user.roles.all():  # 禁止！
    pass
```

#### 模型基类

```python
# models/base.py
from tortoise.models import Model
from tortoise import fields

class BaseModel(Model):
    """基础模型"""
    id = fields.IntField(pk=True, description="主键ID")
    
    class Meta:
        abstract = True

class TimestampMixin:
    """时间戳混入类"""
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
```

### 2.3 Schema 约束

#### Pydantic Schema 规范

```python
# schemas/users.py
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

class UserCreate(BaseModel):
    """创建用户请求模型"""
    email: EmailStr = Field(example="admin@qq.com")
    username: str = Field(example="admin")
    password: str = Field(example="123456")
    is_active: Optional[bool] = True
    role_ids: Optional[List[int]] = []
    
    def create_dict(self):
        return self.model_dump(exclude_unset=True, exclude={"role_ids"})

class UserUpdate(BaseModel):
    """更新用户请求模型"""
    id: int
    email: EmailStr
    username: str
    role_ids: Optional[List[int]] = []

class UserOut(BaseModel):
    """用户响应模型"""
    id: int
    email: Optional[str] = None
    username: Optional[str] = None
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None
```

### 2.4 控制器约束

#### CRUD 控制器规范

```python
# controllers/user.py
from app.core.crud import CRUDBase
from app.models.admin import User
from app.schemas.users import UserCreate, UserUpdate
from app.core.relation import RelationQuery

class UserController(CRUDBase[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(model=User)
    
    async def create_user(self, obj_in: UserCreate) -> User:
        # 密码加密
        obj_in.password = get_password_hash(password=obj_in.password)
        obj = await self.create(obj_in)
        
        # 关联角色
        if obj_in.role_ids:
            await RelationQuery.replace_user_roles(obj.id, obj_in.role_ids)
        
        return obj
    
    def _extract_relation_fields(self, obj_in: UserUpdate) -> Dict[str, Any]:
        """提取关联字段"""
        relation_fields = {}
        if hasattr(obj_in, "role_ids") and obj_in.role_ids is not None:
            relation_fields["role_ids"] = obj_in.role_ids
        return relation_fields
    
    async def _update_relations(self, obj: User, relation_fields: Dict[str, Any]) -> None:
        """更新关联关系"""
        if "role_ids" in relation_fields:
            await RelationQuery.replace_user_roles(obj.id, relation_fields["role_ids"])

user_controller = UserController()
```

#### 数据库查询性能规范

> **⚠️ 重要约束**: 数据库查询必须避免在 for 循环内进行单条查询或更新。
> 应当先组装数据，然后进行批量查询或批量更新。

```python
# ❌ 错误：在循环内逐个查询（N+1 问题）
user_list = []
for user_id in user_ids:
    user = await User.get(id=user_id)  # 每次循环都查询数据库
    user_list.append(user)

# ❌ 错误：在循环内逐个更新
for user_id in user_ids:
    user = await User.get(id=user_id)
    user.is_active = True
    await user.save()  # 每次循环都更新数据库

# ✅ 正确：先组装数据，然后批量查询
user_list = await User.filter(id__in=user_ids).all()  # 一次查询

# ✅ 正确：批量更新
await User.filter(id__in=user_ids).update(is_active=True)  # 一次更新

# ✅ 正确：批量创建
users_to_create = [User(name=f"user_{i}") for i in range(100)]
await User.bulk_create(users_to_create)

# ✅ 正确：复杂场景 - 先查询组装，再批量操作
async def process_users(user_ids: List[int]):
    # 1. 批量查询所有用户
    users = await User.filter(id__in=user_ids).all()
    
    # 2. 在内存中处理数据
    to_update = []
    for user in users:
        if user.status == "pending":
            user.status = "active"
            to_update.append(user)
    
    # 3. 批量更新（如果 ORM 支持）
    if to_update:
        await User.bulk_update(to_update, fields=["status"])
```

### 2.5 API 路由约束

#### 路由定义规范

```python
# api/v1/users/users.py
from fastapi import APIRouter, Query, Header

router = APIRouter()

@router.get("/list", summary="查看用户列表")
async def list_user(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    username: str = Query("", description="用户名称"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    
    # 构建查询条件
    q = Q()
    if username:
        q &= Q(username__contains=username)
    
    # 多租户筛选
    if not is_superuser(current_user):
        tenant_user_ids = await RelationQuery.get_user_ids_by_tenant_id(
            current_user.current_tenant_id
        )
        q &= Q(id__in=tenant_user_ids)
    
    total, user_objs = await user_controller.list(
        page=page, 
        page_size=page_size, 
        search=q
    )
    
    data = [await obj.to_dict(exclude_fields=["password"]) for obj in user_objs]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)
```

### 2.6 响应格式约束

#### 统一响应模型

```python
# schemas/base.py
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class Success(BaseModel, Generic[T]):
    code: int = 200
    msg: str = "success"
    data: T

class SuccessExtra(BaseModel, Generic[T]):
    code: int = 200
    msg: str = "success"
    data: List[T]
    total: int
    page: int
    page_size: int

class Fail(BaseModel):
    code: int
    msg: str
    error: Optional[dict] = None
```

### 2.7 关联查询约束

#### 必须使用 RelationQuery

```python
# ✅ 正确：所有关联查询通过 RelationQuery
from app.core.relation import RelationQuery

# 获取用户角色
role_ids = await RelationQuery.get_role_ids_by_user_id(user_id)

# 更新用户角色
await RelationQuery.replace_user_roles(user_id, role_ids)

# 批量获取
user_role_map = await RelationQuery.batch_get_role_ids_by_user_ids(user_ids)

# ❌ 错误：禁止直接查询关联表
roles = await UserRole.filter(user_id=user_id)  # 不允许
```

### 2.8 认证与权限约束

#### 认证依赖

```python
from app.core.dependency import AuthControl, PermissionControl

# ✅ 正确：使用依赖注入
@router.get("/list", summary="查看列表")
async def list_data(
    current_user: User = Depends(AuthControl.is_authed),
):
    pass

# 或
@router.get("/list", summary="查看列表")
async def list_data(
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
```

#### 权限检查

```python
# ✅ 正确：显式检查权限
from app.core.dependency import PermissionControl

@router.post("/create", summary="创建")
async def create_data(
    data: CreateSchema,
    current_user: User = Depends(PermissionControl.has_permission),
):
    pass

# 或手动检查超级管理员
def is_superuser(user: User) -> bool:
    return user.is_superuser
```

### 2.9 多租户约束

#### 数据隔离规范

```python
# ✅ 正确：非超级管理员必须筛选当前租户
async def list_user(
    current_user: User = Depends(AuthControl.is_authed),
):
    q = Q()
    
    # 多租户筛选
    if not is_superuser(current_user):
        if current_user.current_tenant_id:
            tenant_user_ids = await RelationQuery.get_user_ids_by_tenant_id(
                current_user.current_tenant_id
            )
            q &= Q(id__in=tenant_user_ids)
    
    total, users = await user_controller.list(page=1, page_size=10, search=q)
    return SuccessExtra(data=users, total=total, page=1, page_size=10)
```

#### 租户ID获取规范

> **⚠️ 重要约束**: 接口中租户ID的获取必须区分超管和普通用户。
> - 超管账号：从请求参数获取 `data.tenant_id`
> - 普通账号：从JWT获取 `current_user.current_tenant_id`

```python
# ✅ 正确：租户ID获取逻辑
@router.post("/update_tenant_roles", summary="更新用户在指定租户下的角色")
async def update_user_tenant_roles(
    data: UserUpdateTenantRoles,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 确定要操作的租户ID
    if is_superuser(current_user):
        # 超管使用传参的tenant_id
        if not data.tenant_id:
            return Fail(code=400, msg="请指定租户ID")
        target_tenant_id = data.tenant_id
    else:
        # 普通账号使用JWT中的current_tenant_id
        target_tenant_id = current_user.current_tenant_id
        if not target_tenant_id:
            return Fail(code=400, msg="您当前未选择租户")

    # 权限检查：普通用户检查是否有权限操作该租户
    if not is_superuser(current_user):
        user_tenant_ids = await RelationQuery.get_tenant_ids_by_user_id(current_user.id)
        if target_tenant_id not in user_tenant_ids:
            return Fail(code=403, msg="您没有该租户的权限")
    
    # 业务逻辑...
```

#### 查询范围约束

> **⚠️ 重要约束**: 查询必须限制范围，禁止无过滤条件的全表查询。
> 特别是 `get_by_tenant` 等方法，必须确保传入的 tenant_id 是有效的。

```python
# ❌ 错误：查询范围过大，未限制用户权限
async def get_roles(tenant_id: int):
    # 普通用户可能传入其他租户的ID
    return await role_controller.get_by_tenant(tenant_id)

# ✅ 正确：验证用户权限后再查询
async def get_roles(tenant_id: int, current_user: User):
    # 普通用户只能查询自己所属的租户
    if not is_superuser(current_user):
        user_tenant_ids = await RelationQuery.get_tenant_ids_by_user_id(current_user.id)
        if tenant_id not in user_tenant_ids:
            return Fail(code=403, msg="您没有该租户的权限")
    
    return await role_controller.get_by_tenant(tenant_id)
```

---

## 3. API 认证与多租户约束

### 3.1 认证方式规范

#### 双认证体系

```
┌─────────────────────────────────────────────────────────────┐
│                    认证体系架构                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────┐        │
│  │   管理后台接口       │    │   公开/第三方接口    │        │
│  │   (Internal APIs)   │    │   (Public APIs)     │        │
│  │                     │    │                     │        │
│  │  • 用户管理          │    │  • Dify 调用        │        │
│  │  • 角色权限          │    │  • 外部系统对接     │        │
│  │  • 菜单配置          │    │  • 开放 API         │        │
│  │  • 系统设置          │    │                     │        │
│  └──────────┬──────────┘    └──────────┬──────────┘        │
│             │                          │                   │
│             ▼                          ▼                   │
│  ┌─────────────────────┐    ┌─────────────────────┐        │
│  │   JWT 认证          │    │   API Key 认证      │        │
│  │   AuthControl       │    │   APIKeyAuth        │        │
│  │                     │    │                     │        │
│  │  Header: token      │    │  Header:            │        │
│  │  解析用户身份        │    │  Authorization:     │        │
│  │  获取当前租户        │    │  Bearer {api_key}   │        │
│  └─────────────────────┘    └─────────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 管理后台接口 - JWT 认证

> **⚠️ 强制约束**: 所有管理后台接口必须使用 JWT 认证 (`AuthControl.is_authed`)

```python
# ✅ 正确：管理后台接口使用 JWT 认证
from app.core.dependency import AuthControl, DependAuth

@router.get("/list", summary="查看列表")
async def list_data(
    page: int = Query(1),
    current_user: User = Depends(AuthControl.is_authed),  # JWT 认证
):
    # current_user 包含用户信息、current_tenant_id
    pass

# 或使用简写
@router.post("/create", summary="创建")
async def create_data(
    data: DataCreate,
    current_user: User = DependAuth,  # 简写形式
):
    pass
```

#### 公开/第三方接口 - API Key 认证

> **⚠️ 强制约束**: 所有对外接口必须使用 API Key 认证 (`APIKeyAuth.authenticate`)

```python
# ✅ 正确：公开接口使用 API Key 认证
from app.core.autofill_auth import APIKeyAuth

@autofill_public_router.get("/template/list", summary="查询模板列表")
async def list_templates(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate),  # API Key 认证
):
    """
    对外接口使用 API Key 认证
    auth_info 包含: {
        "tenant_id": int,
        "app_name": str,
        "domain": str,
        "dify_url": str,
        "dify_api_key": str
    }
    """
    tenant_id = auth_info["tenant_id"]  # 从认证信息获取租户
    # 业务逻辑...
```

#### 认证方式选择决策树

```
接口类型判断
    │
    ├─ 管理后台使用？ ──Yes──► JWT 认证 (AuthControl.is_authed)
    │   • 用户管理
    │   • 角色权限
    │   • 系统配置
    │
    └─ 第三方/Dify调用？ ──Yes──► API Key 认证 (APIKeyAuth.authenticate)
        • 模板查询
        • 数据填报
        • 外部系统对接
```

### 3.2 多租户数据隔离规范

#### 数据隔离原则

> **⚠️ 强制约束**: 所有 CURD 操作必须考虑 `tenant_id`，实现多租户数据隔离。

```
┌─────────────────────────────────────────────────────────────┐
│                    多租户数据隔离模型                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  超级管理员 (is_superuser=True)                              │
│  ├── 可见所有租户数据                                        │
│  ├── 前端展示租户筛选框                                      │
│  └── 可通过 tenant_id 参数筛选特定租户                       │
│                                                             │
│  普通用户 (is_superuser=False)                               │
│  ├── 仅可见当前租户数据                                      │
│  ├── 前端不展示租户筛选框                                    │
│  └── 后端自动从 JWT 解析 current_tenant_id 进行限制          │
│                                                             │
│  公开接口 (API Key 认证)                                     │
│  └── 自动从 auth_info 获取 tenant_id 进行限制                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 后端多租户实现规范

```python
# ✅ 正确：标准多租户查询实现
def is_superuser(user: User) -> bool:
    """检查是否为超级管理员"""
    return user.is_superuser

@router.get("/list", summary="查看列表")
async def list_data(
    page: int = Query(1),
    page_size: int = Query(10),
    tenant_id: int = Query(None, description="租户ID（仅超管可见）"),  # 仅超管可用
    token: str = Header(...),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    
    # 多租户筛选逻辑
    if tenant_id is not None and is_superuser(current_user):
        # 超管可按租户筛选
        q &= Q(tenant_id=tenant_id)
    elif not is_superuser(current_user):
        # 普通用户只能查看当前租户
        if current_user.current_tenant_id:
            q &= Q(tenant_id=current_user.current_tenant_id)
        else:
            q &= Q(tenant_id=None)  # 或报错：用户未绑定租户
    
    total, items = await controller.list(page=page, page_size=page_size, search=q)
    return SuccessExtra(data=items, total=total, page=page, page_size=page_size)
```

#### 前端多租户展示规范

```vue
<template>
  <div class="data-page">
    <CrudTable ...>
      <!-- 筛选条件 -->
      <template #filter-items>
        <!-- ✅ 正确：仅超管显示租户筛选 -->
        <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8">
          <a-form-item label="租户">
            <a-select 
              v-model:value="queryParams.tenant_id" 
              placeholder="请选择租户"
              :options="tenantOptions"
              @change="handleSearch"
            />
          </a-form-item>
        </a-col>
      </template>
    </CrudTable>
  </div>
</template>

<script setup>
import { useUserStore } from '@/store'

const userStore = useUserStore()

// 查询参数
const queryParams = reactive({
  keyword: '',
  tenant_id: undefined,  // 超管可传，普通用户后端会忽略
})
</script>
```

#### 公开接口多租户处理

```python
# ✅ 正确：公开接口从 auth_info 获取 tenant_id
@autofill_public_router.get("/data/list", summary="查询数据")
async def list_public_data(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate),
):
    """
    公开接口自动从 API Key 获取租户信息
    无需前端传递 tenant_id
    """
    tenant_id = auth_info["tenant_id"]  # 自动获取
    
    q = Q(tenant_id=tenant_id)  # 自动限制
    # 业务逻辑...
```

#### 创建/更新时的租户处理

```python
# ✅ 正确：创建时自动设置租户
@router.post("/create", summary="创建")
async def create_data(
    data: DataCreate,
    current_user: User = DependAuth,
):
    # 超管可以指定租户
    if is_superuser(current_user):
        if data.tenant_id is None:
            data.tenant_id = current_user.current_tenant_id
    else:
        # 普通用户强制使用当前租户
        data.tenant_id = current_user.current_tenant_id
    
    obj = await controller.create(data)
    return Success(data=await obj.to_dict())
```

#### 多租户检查清单

**后端检查项：**
- [ ] 所有列表查询是否包含 tenant_id 筛选
- [ ] 超管是否可以通过参数筛选任意租户
- [ ] 普通用户是否只能访问 current_tenant_id 的数据
- [ ] 创建/更新时是否自动设置正确的 tenant_id
- [ ] 公开接口是否从 auth_info 获取 tenant_id
- [ ] 关联查询是否限制在相同租户内

**前端检查项：**
- [ ] 租户筛选框是否仅在 `userStore.isSuperUser` 时显示
- [ ] 普通用户是否无法看到其他租户的数据
- [ ] 创建表单中租户选择是否仅超管可见

---

## 4. 数据库约束

### 4.1 命名规范

| 对象 | 规范 | 示例 |
|------|------|------|
| 表名 | 单数小写 | user, role, menu |
| 字段 | 小写下划线 | user_name, created_at |
| 索引 | idx_表名_字段 | idx_user_username |
| 关联表 | 表1_表2 | user_role, role_menu |

> **⚠️ 禁止**: 禁止使用数据库外键约束（Foreign Key），通过应用层维护关联关系。

### 4.2 字段规范

```python
# ✅ 正确：所有字段必须有描述和索引（需要时）
class User(BaseModel):
    username = fields.CharField(
        max_length=20, 
        unique=True, 
        description="用户名称", 
        index=True
    )
    is_active = fields.BooleanField(
        default=True, 
        description="是否激活", 
        index=True
    )
    created_at = fields.DatetimeField(
        auto_now_add=True, 
        description="创建时间"
    )
```

### 4.3 字段默认值规范

> **⚠️ 重要约束**: 尽量少使用 `null=True`，字段应设置合理的默认值。

```python
# ❌ 错误：使用 null=True
name = fields.CharField(max_length=100, null=True, description="名称")
status = fields.IntField(null=True, description="状态")

# ✅ 正确：使用默认值
name = fields.CharField(max_length=100, default="", description="名称")
status = fields.IntField(default=0, description="状态")
is_active = fields.BooleanField(default=True, description="是否激活")
count = fields.IntField(default=0, description="计数")
```

**允许使用 null=True 的场景：**
- 可选的时间字段（如 deleted_at 软删除时间）
- 真正可选且需要区分"未设置"和"空值"的字段
- 关联字段在关联对象被删除时需要置空的情况

### 4.3.1 可空字段设计规范

> **⚠️ 设计原则**: 以下场景允许使用 `null=True` 设计：

**1. 可选时间字段**

时间类字段在业务上表示"未发生"或"未设置"时，可以设计为 NULL：

```python
# ✅ 正确：可选时间字段定义
class User(BaseModel, TimestampMixin):
    """用户模型"""
    username = fields.CharField(max_length=20, description="用户名")
    
    # 软删除时间 - NULL 表示未删除
    deleted_at = fields.DatetimeField(null=True, default=None, description="删除时间")
    
    # 最后登录时间 - NULL 表示从未登录
    last_login_at = fields.DatetimeField(null=True, default=None, description="最后登录时间")
    
    # 激活时间 - NULL 表示未激活
    activated_at = fields.DatetimeField(null=True, default=None, description="激活时间")
    
    class Meta:
        table = "user"
```

**2. 大文本字段（TEXT/LONGTEXT）**

TEXT 类字段默认可以设置为 NULL，因为：
- 空字符串和 NULL 在业务语义上可能有区别
- 大文本字段存储空字符串也会占用存储空间
- 某些场景下 NULL 表示"未填写"，空字符串表示"已填写但内容为空"

```python
# ✅ 正确：TEXT 字段可空设计
class Article(BaseModel, TimestampMixin):
    """文章模型"""
    title = fields.CharField(max_length=200, default="", description="标题")
    
    # 正文内容 - 可以为 NULL 表示草稿/未填写
    content = fields.TextField(null=True, default=None, description="正文内容")
    
    # 摘要 - 可以为 NULL 表示未生成摘要
    summary = fields.TextField(null=True, default=None, description="摘要")
    
    class Meta:
        table = "article"
```

**3. 软删除规范**

```python
# ✅ 正确：软删除字段定义
class User(BaseModel, TimestampMixin):
    """用户模型"""
    username = fields.CharField(max_length=20, description="用户名")
    is_deleted = fields.BooleanField(default=False, description="是否删除标记", index=True)
    deleted_at = fields.DatetimeField(null=True, default=None, description="删除时间")
    
    class Meta:
        table = "user"

# ✅ 正确：查询时过滤已删除记录
async def list_active_users():
    return await User.filter(is_deleted=False).all()

# ✅ 正确：软删除操作
async def soft_delete_user(user_id: int):
    await User.filter(id=user_id).update(
        is_deleted=True,
        deleted_at=datetime.now()
    )

# ✅ 正确：恢复软删除
async def restore_user(user_id: int):
    await User.filter(id=user_id).update(
        is_deleted=False,
        deleted_at=None
    )
```

**默认值规范：**
| 字段类型 | 默认值 | 是否可空 | 说明 |
|----------|--------|----------|------|
| 字符串（VARCHAR/CHAR） | `""` | 否 | 空字符串 |
| 整数 | `0` | 否 | 零值 |
| 布尔（是否类） | `0/1` | **否** | TINYINT(1)，0=False, 1=True |
| JSON | `[]` 或 `{}` | 否 | 空数组或空对象 |
| 日期时间（创建/更新） | `auto_now_add/auto_now` | 否 | 自动时间戳 |
| 日期时间（可选业务时间） | `None` | **是** | 删除时间、最后登录时间等 |
| 大文本（TEXT/LONGTEXT） | `None` | **是** | 内容字段、描述字段等 |

**布尔类型规范：**
```python
# ✅ 正确：布尔字段使用 TINYINT(1) NOT NULL
class User(BaseModel, TimestampMixin):
    """用户模型"""
    username = fields.CharField(max_length=20, description="用户名")
    
    # 是否启用 - 默认启用（1）
    is_active = fields.BooleanField(default=True, description="是否启用")
    
    # 是否超级用户 - 默认否（0）
    is_superuser = fields.BooleanField(default=False, description="是否超级用户")
    
    # 是否删除 - 默认否（0）
    is_deleted = fields.BooleanField(default=False, description="是否删除")
    
    class Meta:
        table = "user"

# ❌ 错误：布尔字段不要设置为可空
is_active = fields.BooleanField(null=True, description="是否启用")  # 不要这样设计
```

### 4.4 关联表规范

```python
# ✅ 正确：关联表定义（无外键约束）
class UserRole(BaseModel, TimestampMixin):
    """用户-角色关联表"""
    user_id = fields.IntField(description="用户ID", index=True)
    role_id = fields.IntField(description="角色ID", index=True)
    
    class Meta:
        table = "user_role"
        unique_together = ("user_id", "role_id")  # 联合唯一
```

### 4.5 禁止外键约束

> **⚠️ 强制约束**: 禁止使用数据库外键约束（Foreign Key），所有关联关系通过应用层维护。

**原因：**
1. **性能**: 外键约束会增加写操作的开销
2. **灵活性**: 应用层可以更灵活地控制关联关系
3. **分布式**: 便于后续数据库分片/分布式架构
4. **维护性**: 避免级联删除/更新带来的意外数据丢失

```python
# ❌ 错误：使用外键约束
class Order(BaseModel):
    user = fields.ForeignKeyField("models.User", related_name="orders")

# ✅ 正确：使用普通字段存储关联ID
class Order(BaseModel):
    user_id = fields.IntField(description="用户ID", index=True)
```

---

## 5. API 设计约束

### 5.1 RESTful 规范

| 操作 | HTTP 方法 | URL 格式 | 示例 |
|------|-----------|----------|------|
| 列表查询 | GET | /{resource}/list | GET /user/list |
| 详情查询 | GET | /{resource}/get | GET /user/get?id=1 |
| 创建 | POST | /{resource}/create | POST /user/create |
| 更新 | POST | /{resource}/update | POST /user/update |
| 删除 | DELETE | /{resource}/delete | DELETE /user/delete?id=1 |

### 5.2 参数规范

```python
# ✅ 正确：查询参数使用 Query
@router.get("/list")
async def list_data(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    keyword: str = Query("", description="关键词"),
):
    pass

# ✅ 正确：请求体使用 Body（Pydantic 模型）
@router.post("/create")
async def create_data(data: UserCreate):
    pass

# ✅ 正确：Token 使用 Header
token: str = Header(..., description="token验证")
```

### 5.3 响应规范

```python
# ✅ 正确：列表响应
return SuccessExtra(
    data=data,
    total=total,
    page=page,
    page_size=page_size
)

# ✅ 正确：单条数据响应
return Success(data=user_dict)

# ✅ 正确：操作成功响应
return Success(msg="删除成功")
```

---

## 6. 前端组件开发约束

### 6.1 Vue Transition 约束

> **⚠️ 重要约束**: Vue 的 `<Transition>` 组件要求子组件只能有一个根元素。
> 如果组件有多个根元素，会触发警告：`Component inside <Transition> renders non-element root node that cannot be animated.`

```vue
<!-- ❌ 错误：多个根元素 -->
<template>
  <CrudTable>...</CrudTable>
  <a-drawer>...</a-drawer>
  <a-modal>...</a-modal>
</template>

<!-- ✅ 正确：单一根元素包裹 -->
<template>
  <div class="role-page">
    <CrudTable>...</CrudTable>
    <a-drawer>...</a-drawer>
    <a-modal>...</a-modal>
  </div>
</template>
```

### 6.2 通用 CrudTable 组件规范

> **⚠️ 重要约束**: 所有表格页面必须使用 `CrudTable` 通用组件，禁止重复编写表格、筛选、分页、弹窗等代码。

#### 使用 CrudTable 组件

```vue
<template>
  <div class="role-page">
    <CrudTable
      ref="crudTableRef"
      :columns="columns"
      :data-source="tableData"
      :loading="loading"
      :pagination="pagination"
      :filter-model="queryParams"
      :filter-item-count="filterItemCount"
      show-modal
      :modal-title="modalTitle"
      :modal-loading="modalLoading"
      :modal-form="modalForm"
      :modal-rules="modalRules"
      @search="handleSearch"
      @reset="handleReset"
      @table-change="handleTableChange"
      @modal-ok="handleSave"
    >
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6">
          <a-form-item label="角色名">
            <a-input v-model:value="queryParams.role_name" placeholder="请输入角色名" allow-clear />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-button v-permission="'post/api/v1/role/create'" type="primary" @click="handleAdd">
          <PlusOutlined /> 新建角色
        </a-button>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <a-tag color="blue">{{ record.name }}</a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除吗？" @confirm="handleDelete(record)">
              <a-button type="link" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form, action }">
        <a-form-item label="角色名" name="name">
          <a-input v-model:value="form.name" placeholder="请输入角色名称" />
        </a-form-item>
      </template>
    </CrudTable>

    <!-- 其他弹窗/Drawer（如设置权限等） -->
    <a-drawer v-model:open="drawerVisible" title="设置权限">...</a-drawer>
  </div>
</template>

<script setup lang="ts">
import CrudTable from '@/components/CrudTable/index.vue'

const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 表格列定义
const columns = computed(() => [
  { title: '角色名', dataIndex: 'name', key: 'name', width: 150 },
  { title: '操作', key: 'action', width: 200, fixed: 'right' as const },
])

// 筛选条件数量（用于布局计算）
const filterItemCount = computed(() => 1)

// 打开新增弹窗
function handleAdd() {
  modalTitle.value = '新增角色'
  crudTableRef.value?.openAddModal()
}

// 打开编辑弹窗
function handleEdit(record: any) {
  modalTitle.value = '编辑角色'
  crudTableRef.value?.openEditModal(record)
}
</script>
```

#### CrudTable Props

| 属性 | 类型 | 说明 |
|------|------|------|
| columns | ColumnType[] | 表格列配置 |
| dataSource | any[] | 数据源 |
| loading | boolean | 加载状态 |
| pagination | PaginationConfig | 分页配置 |
| filterModel | Record<string, any> | 筛选表单模型 |
| filterItemCount | number | 筛选条件数量（用于布局） |
| showModal | boolean | 是否显示内置弹窗 |
| modalTitle | string | 弹窗标题 |
| modalLoading | boolean | 弹窗确认按钮加载状态 |
| modalForm | Record<string, any> | 弹窗表单模型 |
| modalRules | Record<string, any> | 表单验证规则 |

#### CrudTable Slots

| 插槽名 | 说明 |
|--------|------|
| filter-items | 自定义筛选条件 |
| actions | 自定义操作按钮 |
| bodyCell | 自定义单元格渲染 |
| modal-form | 自定义弹窗表单内容 |

#### CrudTable 方法（通过 ref 调用）

```typescript
// 打开新增弹窗
crudTableRef.value?.openAddModal()

// 打开编辑弹窗（自动填充表单数据）
crudTableRef.value?.openEditModal(record)

// 关闭弹窗
crudTableRef.value?.closeModal()

// 重置弹窗表单
crudTableRef.value?.resetModalForm()
```

#### 禁止事项

```vue
<!-- ❌ 错误：重复编写表格代码 -->
<template>
  <div>
    <a-card>
      <!-- 筛选表单 -->
      <a-form>...</a-form>
      <!-- 表格 -->
      <a-table>...</a-table>
    </a-card>
    <!-- 弹窗 -->
    <a-modal>...</a-modal>
  </div>
</template>

<!-- ✅ 正确：使用 CrudTable 组件 -->
<template>
  <div>
    <CrudTable>...</CrudTable>
  </div>
</template>
```

### 6.3 表格列定义规范

```typescript
// ✅ 正确：列定义使用 computed
const columns = computed(() => [
  {
    title: '名称',
    dataIndex: 'name',
    key: 'name',
    width: 120,
    ellipsis: true,
  },
  {
    title: '状态',
    dataIndex: 'is_active',
    key: 'is_active',
    width: 100,
  },
  {
    title: '创建时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 180,
  },
  {
    title: '操作',
    key: 'action',
    fixed: 'right',
    width: 200,
  },
])
```

### 6.4 表单验证规范

```typescript
// ✅ 正确：表单验证规则
const modalRules = {
  name: [
    { required: true, message: '请输入名称', trigger: 'blur' },
    { min: 2, max: 20, message: '长度在 2-20 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  role_ids: [
    { type: 'array', required: true, message: '请选择角色', trigger: 'change' },
  ],
}
```

---

## 7. 文件上传约束

### 7.1 前端上传

```typescript
// ✅ 正确：使用 FormData
async function handleUpload(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  
  const res = await request.post('/upload/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  
  return res.data.url
}
```

### 7.2 后端接收

```python
# ✅ 正确：使用 UploadFile
from fastapi import UploadFile, File

@router.post("/avatar", summary="上传头像")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(AuthControl.is_authed),
):
    # 验证文件类型
    allowed_extensions = settings.ALLOWED_EXTENSIONS
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        return Fail(code=400, msg="不支持的文件类型")
    
    # 验证文件大小
    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE * 1024 * 1024:
        return Fail(code=400, msg="文件大小超过限制")
    
    # 保存文件
    # ...
```

---

## 8. 错误处理约束

### 8.1 前端错误处理

```typescript
// ✅ 正确：统一错误处理在 request.ts
// 组件中只需要处理业务逻辑
async function handleSave() {
  modalLoading.value = true
  try {
    const apiCall = modalAction.value === 'add' 
      ? api.createData 
      : api.updateData
    await apiCall(modalForm)
    
    window.$message?.success(modalAction.value === 'add' ? '创建成功' : '更新成功')
    modalVisible.value = false
    fetchData()
  } finally {
    modalLoading.value = false
  }
}
```

### 8.2 后端错误处理

```python
# ✅ 正确：使用自定义异常
from app.core.exceptions import HTTPException

# 业务异常
raise HTTPException(status_code=400, detail="用户已存在")

# 权限异常
raise HTTPException(status_code=403, detail="没有权限")

# 未找到
raise HTTPException(status_code=404, detail="用户不存在")
```

---

## 9. 日志约束

### 9.1 后端日志

```python
from app.log import logger

# ✅ 正确：使用结构化日志
logger.info(f"用户登录成功: {user.username}")
logger.error(f"操作失败: {str(error)}")

# ✅ 正确：审计日志自动记录（通过中间件）
# HttpAuditLogMiddleware 会自动记录所有请求
```

---

## 10. 配置约束

### 10.1 环境配置

```python
# settings/config.py
class Settings(BaseSettings):
    # 数据库配置
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root123456"
    MYSQL_DATABASE: str = "autofill"

    # JWT 配置
    SECRET_KEY: str = "..."
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # 上传配置
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 5  # MB
```

### 10.2 前端配置

```typescript
// .env
VITE_BASE_API = '/api'

// vite.config.ts
server: {
  port: 3200,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:9999',
      changeOrigin: true,
    },
  },
}
```

---

## 11. 代码生成约束

### 11.1 生成新模块步骤

#### 后端

```
1. 创建模型 (models/admin.py)
2. 创建 Schema (schemas/{name}.py)
3. 创建控制器 (controllers/{name}.py) - 继承 CRUDBase
4. 创建 API (api/v1/{name}/{name}.py)
5. 注册路由 (api/v1/__init__.py)
6. 创建数据库迁移 (aerich migrate)
```

#### 前端

```
1. 创建视图 (views/{module}/{page}/index.vue)
2. 添加 API (api/index.ts)
3. 后端菜单管理中添加菜单
4. 角色管理中分配权限
```

### 11.2 必须遵守的导入路径

```typescript
// ✅ 正确：使用路径别名
import { useUserStore } from '@/store'
import api from '@/api'
import { formatDateTime } from '@/utils'

// ❌ 错误：相对路径过深
import { useUserStore } from '../../../store'
```

```python
# ✅ 正确：使用绝对导入
from app.models.admin import User
from app.core.crud import CRUDBase
from app.schemas.users import UserCreate

# ❌ 错误：相对导入
from ..models import User
```

---

## 13. 禁止事项清单

### 13.1 前端禁止

- ❌ 禁止使用 Options API
- ❌ 禁止使用 `any` 类型（除非必要）
- ❌ 禁止直接修改 Pinia State（必须通过 action）
- ❌ 禁止在模板中写复杂表达式
- ❌ 禁止使用未注册的组件
- ❌ 禁止直接操作 DOM（使用 Vue 的 ref）
- ❌ 禁止在组件中直接调用 axios（使用封装的 request）
- ❌ 禁止组件模板有多个根元素（必须使用单一根元素包裹）
- ❌ 禁止表格页面重复编写表格/筛选/分页/弹窗代码（必须使用 CrudTable 组件）

### 13.2 后端禁止

- ❌ 禁止不使用类型注解
- ❌ 禁止直接查询关联表（必须使用 RelationQuery）
- ❌ 禁止在控制器中写 SQL
- ❌ 禁止明文存储密码
- ❌ 禁止返回敏感字段（如 password）
- ❌ 禁止非超级管理员跨租户查询数据
- ❌ 禁止在循环中查询数据库（使用批量查询）
- ❌ 禁止查询范围过大的全表扫描（如 `Model.all()` 未加过滤条件）

---

## 14. 代码复用架构指导

### 14.1 前端组件复用架构

#### 组件分层模型

```
┌─────────────────────────────────────────────────────────────┐
│                      页面层 (Pages)                          │
│  views/system/role/index.vue                                │
│  views/system/user/index.vue                                │
│  - 使用 CrudTable 组件                                      │
│  - 定义业务特定的 columns、筛选条件、表单                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   业务组件层 (Business)                      │
│  components/CrudTable/index.vue                             │
│  - 通用 CRUD 表格组件                                       │
│  - 封装筛选、表格、分页、弹窗                               │
│  - 提供 slots 自定义扩展点                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   基础组件层 (Base)                          │
│  Ant Design Vue (a-table, a-modal, a-form...)               │
│  - 第三方 UI 组件库                                         │
│  - 不直接修改，通过封装使用                                 │
└─────────────────────────────────────────────────────────────┘
```

#### 页面开发规范

> **⚠️ 强制约束**: 所有表格页面必须使用 `CrudTable` 组件，禁止复制粘贴重复代码。

> **特殊页面说明**：
> - **带侧边栏的页面**（如用户管理）：将 CrudTable 作为右侧主内容区组件，左侧部门树保持独立
> - **树形表格页面**（如菜单）：CrudTable 支持树形展示，使用 `:pagination="false"` 禁用分页

#### 页面模板标准结构

```vue
<template>
  <div class="{module}-page">
    <!-- 1. 使用 CrudTable 组件 -->
    <CrudTable
      ref="crudTableRef"
      :columns="columns"
      :data-source="tableData"
      :loading="loading"
      :pagination="pagination"
      :filter-model="queryParams"
      :filter-item-count="filterItemCount"
      show-modal
      :modal-title="modalTitle"
      :modal-loading="modalLoading"
      :modal-form="modalForm"
      :modal-rules="modalRules"
      @search="handleSearch"
      @reset="handleReset"
      @table-change="handleTableChange"
      @modal-ok="handleSave"
    >
      <!-- 2. 自定义筛选条件 -->
      <template #filter-items>
        <!-- 筛选项 -->
      </template>

      <!-- 3. 自定义操作按钮 -->
      <template #actions>
        <!-- 按钮 -->
      </template>

      <!-- 4. 自定义表格列 -->
      <template #bodyCell="{ column, record }">
        <!-- 列渲染 -->
      </template>

      <!-- 5. 自定义弹窗表单 -->
      <template #modal-form="{ form, action }">
        <!-- 表单字段 -->
      </template>
    </CrudTable>

    <!-- 6. 其他业务弹窗/Drawer -->
    <a-drawer v-model:open="drawerVisible">...</a-drawer>
    <a-modal v-model:open="otherModalVisible">...</a-modal>
  </div>
</template>

<script setup lang="ts">
// 1. 导入顺序：Vue/Pinia -> 第三方 -> 本地
import { ref, computed, reactive, onMounted } from 'vue'
import { useUserStore } from '@/store'
import CrudTable from '@/components/CrudTable/index.vue'
import api from '@/api'
import { formatDateTime } from '@/utils'

// 2. 定义选项
defineOptions({ name: '页面名称' })

// 3. Store 注入
const userStore = useUserStore()

// 4. CrudTable ref
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 5. 查询参数
const queryParams = reactive({
  keyword: '',
  // ...
})

// 6. 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({ current: 1, pageSize: 10, total: 0 })

// 7. 弹窗数据
const modalTitle = ref('')
const modalLoading = ref(false)
const modalForm = reactive({ name: '' })
const modalRules = { name: [{ required: true, message: '请输入名称' }] }

// 8. 计算属性
// 注意：columns 不需要显式声明类型，CrudTable 组件已自动处理类型推断
// 如需使用 fixed: 'right' 等属性，直接写即可，组件内部会自动转换
const columns = computed(() => [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '操作', key: 'action', fixed: 'right' },
])

const filterItemCount = computed(() => 1)

// 9. 方法
async function loadData() {
  loading.value = true
  try {
    const res: any = await api.getList({
      page: pagination.current,
      page_size: pagination.pageSize,
      ...queryParams,
    })
    tableData.value = res.data
    pagination.total = res.total
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.current = 1
  loadData()
}

function handleReset() {
  Object.assign(queryParams, { keyword: '' })
  handleSearch()
}

function handleTableChange(p: any) {
  pagination.current = p.current
  pagination.pageSize = p.pageSize
  loadData()
}

function handleAdd() {
  modalTitle.value = '新增'
  Object.assign(modalForm, { name: '' })
  crudTableRef.value?.openAddModal()
}

function handleEdit(record: any) {
  modalTitle.value = '编辑'
  crudTableRef.value?.openEditModal(record)
}

async function handleSave(form: Record<string, any>, action: 'add' | 'edit') {
  modalLoading.value = true
  try {
    const apiFn = action === 'add' ? api.create : api.update
    await apiFn(form)
    window.$message?.success(action === 'add' ? '创建成功' : '更新成功')
    crudTableRef.value?.closeModal()
    loadData()
  } finally {
    modalLoading.value = false
  }
}

// 10. 生命周期
onMounted(loadData)
</script>
```

### 12.2 后端代码复用架构

#### 控制器分层模型

```
┌─────────────────────────────────────────────────────────────┐
│                    API 层 (Routers)                          │
│  api/v1/users/users.py                                      │
│  api/v1/roles/roles.py                                      │
│  - 参数校验                                                 │
│  - 权限检查                                                 │
│  - 调用控制器/Service                                       │
│  - 返回统一响应格式                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 控制器层 (Controllers)                       │
│  controllers/user.py                                        │
│  controllers/role.py                                        │
│  - 继承 CRUDBase                                            │
│  - 简单业务逻辑封装                                         │
│  - 关联关系处理                                             │
│  - 复用基类 CRUD 方法                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Service 层 (Services)                      │
│  services/ai_fill_service.py                                │
│  services/file_service.py                                   │
│  - 复杂业务逻辑封装                                         │
│  - 跨控制器复用的业务逻辑                                   │
│  - 外部服务调用（AI、文件存储等）                           │
│  - 事务管理                                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   基础层 (Core)                              │
│  core/crud.py - CRUDBase 基类                               │
│  core/relation.py - RelationQuery 关联查询                  │
│  - 通用 CRUD 操作封装                                       │
│  - 关联查询封装                                             │
│  - 所有控制器复用                                           │
└─────────────────────────────────────────────────────────────┘
```

#### Service 层使用规范

> **💡 提示**: Service 层用于封装较复杂的业务逻辑，以下情况应考虑使用 Service：

1. **复杂业务逻辑**: 涉及多个步骤、多个模型操作的复杂业务流程
2. **跨控制器复用**: 多个控制器需要使用的相同业务逻辑
3. **外部服务调用**: 调用第三方 API、AI 服务、文件存储等
4. **事务管理**: 需要保证原子性的多表操作

```python
# ✅ 正确：Service 层封装复杂业务
# services/ai_fill_service.py
from app.services.ai_fill_service import get_ai_fill_service

@router.post("/fill", summary="AI填单")
async def ai_fill(
    request: FillRequest,
    current_user: User = DependAuth,
):
    # 复杂业务逻辑交给 Service
    service = get_ai_fill_service()
    result = await service.process_fill(
        template_id=request.template_id,
        content=request.content,
        tenant_id=current_user.current_tenant_id
    )
    return Success(data=result)

# ✅ 正确：简单 CRUD 直接使用控制器
@router.get("/list", summary="查看列表")
async def list_data(
    page: int = Query(1),
    current_user: User = DependAuth,
):
    # 简单查询直接使用控制器
    q = Q(tenant_id=current_user.current_tenant_id)
    total, items = await controller.list(page=page, search=q)
    return SuccessExtra(data=items, total=total, page=page)
```

**Service 层设计原则：**
- Service 应该是无状态的，不保存请求相关的状态
- Service 方法应该明确输入输出，便于单元测试
- 复杂的业务校验应该在 Service 中完成
- **⚠️ 禁止**: Service 层禁止依赖 Controller 层，Service 应直接操作 Model

#### Service 层架构约束

> **⚠️ 重要约束**: 严格遵循分层架构，禁止循环依赖

**依赖方向（必须遵守）:**
```
API 层 (Routers) → Controller 层 → Service 层 → Model 层
```

**禁止反向依赖:**
```python
# ❌ 禁止: Service 层导入 Controller
# services/some_service.py
from app.controllers.llm_config import llm_config_controller  # 禁止！
from app.controllers.autofill import fill_data_controller     # 禁止！

# ✅ 正确: Service 层直接操作 Model
# services/some_service.py
from app.models.llm_config import LLMConfig
from app.services.llm.llm_config_utils import get_default_llm_config  # 使用 Service 层工具

async def get_config():
    # 直接查询 Model，不通过 Controller
    return await LLMConfig.filter(is_default=True).first()
```

**公共工具函数位置:**
```python
# ✅ 正确: 公共 LLM 配置获取函数放在 Service 层
# app/services/llm/llm_config_utils.py
async def get_default_llm_config(tenant_id: int = 0, app_name: str = None) -> Optional[LLMConfig]:
    """获取默认 LLM 配置 - 供所有 Service 使用"""
    ...

# 其他 Service 导入使用
# app/services/agent/core/param_extractor.py
from app.services.llm.llm_config_utils import get_default_llm_config
```

#### 控制器开发规范

```python
# ✅ 正确：继承 CRUDBase，复用通用方法
from app.core.crud import CRUDBase
from app.models.admin import User
from app.schemas.users import UserCreate, UserUpdate

class UserController(CRUDBase[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(model=User)
    
    # 扩展基类方法
    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.model.filter(email=email).first()
    
    # 重写创建方法（需要处理关联关系时）
    async def create_user(self, obj_in: UserCreate) -> User:
        # 1. 调用基类创建
        obj = await self.create(obj_in)
        
        # 2. 处理关联关系
        if obj_in.role_ids:
            await RelationQuery.replace_user_roles(obj.id, obj_in.role_ids)
        
        return obj

# 单例模式
user_controller = UserController()
```

#### 关联查询规范

```python
# ✅ 正确：所有关联操作通过 RelationQuery
from app.core.relation import RelationQuery

# 获取用户的角色ID列表
role_ids = await RelationQuery.get_role_ids_by_user_id(user_id)

# 批量获取多个用户的角色
user_role_map = await RelationQuery.batch_get_role_ids_by_user_ids(user_ids)

# 更新用户角色（自动处理关联表）
await RelationQuery.replace_user_roles(user_id, role_ids)

# 批量添加关联
await RelationQuery.batch_add_user_roles([(user_id, role_id) for role_id in role_ids])

# ❌ 禁止：直接操作关联表
from app.models.admin import UserRole
await UserRole.filter(user_id=user_id).delete()  # 禁止！
await UserRole.create(user_id=user_id, role_id=role_id)  # 禁止！
```

#### Schema 复用规范

```python
# ✅ 正确：使用继承复用 Schema
from pydantic import BaseModel
from typing import Optional, List

class UserBase(BaseModel):
    """用户基础字段"""
    username: str
    email: str
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    """创建用户"""
    password: str
    role_ids: Optional[List[int]] = []

class UserUpdate(UserBase):
    """更新用户"""
    id: int
    role_ids: Optional[List[int]] = []

class UserOut(UserBase):
    """用户输出"""
    id: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
```

### 14.3 API 设计复用模式

#### 标准 CRUD API 模板

```python
# api/v1/{module}/{module}.py
from fastapi import APIRouter, Query, Depends

router = APIRouter()

@router.get("/list", summary="查看列表")
async def list_{module}(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    keyword: str = Query("", description="关键词"),
    current_user: User = Depends(AuthControl.is_authed),
):
    # 1. 构建查询条件
    q = Q()
    if keyword:
        q &= Q(name__contains=keyword)
    
    # 2. 多租户筛选（非超管）
    if not is_superuser(current_user):
        # 根据业务添加租户筛选
        pass
    
    # 3. 调用控制器
    total, items = await {module}_controller.list(
        page=page, 
        page_size=page_size, 
        search=q
    )
    
    # 4. 序列化
    data = [await item.to_dict() for item in items]
    
    # 5. 返回统一格式
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)

@router.post("/create", summary="创建")
async def create_{module}(
    data: {Module}Create,
    current_user: User = Depends(PermissionControl.has_permission),
):
    obj = await {module}_controller.create(data)
    return Success(data=await obj.to_dict())

@router.post("/update", summary="更新")
async def update_{module}(
    data: {Module}Update,
    current_user: User = Depends(PermissionControl.has_permission),
):
    obj = await {module}_controller.update(data.id, data)
    return Success(data=await obj.to_dict())

@router.delete("/delete", summary="删除")
async def delete_{module}(
    id: int = Query(..., description="ID"),
    current_user: User = Depends(PermissionControl.has_permission),
):
    await {module}_controller.remove(id)
    return Success(msg="删除成功")
```

### 14.4 代码复用检查清单

#### 前端检查项

- [ ] 表格页面是否使用 CrudTable 组件
- [ ] 是否通过 slots 自定义而非修改组件
- [ ] API 调用是否使用统一的 api/index.ts
- [ ] 工具函数是否从 @/utils 导入
- [ ] 类型定义是否复用已有接口

#### 后端检查项

- [ ] 控制器是否继承 CRUDBase
- [ ] 关联操作是否使用 RelationQuery
- [ ] Schema 是否使用继承复用基础字段
- [ ] API 是否遵循标准 CRUD 模式
- [ ] 权限检查是否使用装饰器/依赖

---

## 15. 检查清单

### 15.1 代码提交前检查

- [ ] 前端代码通过 TypeScript 编译
- [ ] 后端代码通过 ruff 检查
- [ ] 后端代码通过 black 格式化
- [ ] 所有 API 都有权限控制
- [ ] 敏感数据已排除（password 等）
- [ ] 多租户数据隔离正确
- [ ] 表单验证规则完整
- [ ] 错误处理完善
- [ ] 表格页面使用 CrudTable 组件（如适用）
- [ ] 控制器继承 CRUDBase（如适用）

---

## 16. 日志记录规范

### 16.1 日志框架使用规范

> **⚠️ 重要约束**: 项目使用 loguru 作为核心日志框架，通过自定义代理类兼容标准库 logging。

```python
# ✅ 正确：使用项目统一的日志模块
from app.log import getLogger

logger = getLogger(__name__)
logger.info("用户登录成功", user_id=user.id)
logger.error("数据库连接失败", error=str(e))

# ✅ 正确：使用 bind 添加上下文
logger.bind(request_id=request_id, user_id=user_id).info("处理请求")

# ❌ 错误：直接使用标准库 logging
import logging
logger = logging.getLogger(__name__)  # 不允许

# ❌ 错误：直接使用 loguru
from loguru import logger  # 不允许，使用项目封装的模块
```

### 16.2 日志级别使用规范

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| DEBUG | 开发调试信息，生产环境关闭 | `logger.debug(f"SQL: {sql}")` |
| INFO | 业务流程记录 | `logger.info("用户创建成功", user_id=123)` |
| WARNING | 非致命异常，可恢复错误 | `logger.warning("请求限流", client_ip=ip)` |
| ERROR | 业务错误，需要处理 | `logger.error("数据库查询失败", error=str(e))` |
| CRITICAL | 系统级错误，需要立即处理 | `logger.critical("服务启动失败")` |

### 16.3 日志内容规范

```python
# ✅ 正确：结构化日志，使用关键字参数
logger.info(
    "订单处理完成",
    order_id=order.id,
    user_id=order.user_id,
    amount=order.amount,
    duration_ms=processing_time
)

# ✅ 正确：异常日志包含完整上下文
try:
    result = await process_data()
except Exception as e:
    logger.error(
        "数据处理失败",
        error=str(e),
        error_type=type(e).__name__,
        data_id=data.id,
        retry_count=retry
    )

# ❌ 错误：使用字符串拼接
logger.info("用户" + user.name + "登录成功")  # 不允许

# ❌ 错误：敏感信息未脱敏
logger.info("用户登录", password=password)  # 不允许！
```

### 16.4 请求日志规范

> **⚠️ 重要约束**: 所有 HTTP 请求必须通过 `RequestLoggingMiddleware` 自动记录，禁止在业务代码中重复记录请求日志。

```python
# ✅ 正确：中间件自动记录，包含以下字段
{
    "timestamp": "2026-05-02T14:42:56.330878+08:00",
    "level": "INFO",
    "message": "POST /api/v1/base/access_token - 422",
    "method": "POST",
    "path": "/api/v1/base/access_token",
    "query": "",
    "status_code": 422,
    "duration_ms": 3.2,
    "client_ip": "127.0.0.1",
    "request_params": {"invalid": "data"},
    "request_id": "d5329543-0178-456e-b8f8-d62804fc9289"
}

# ❌ 错误：在业务代码中重复记录请求日志
@router.post("/login")
async def login(data: LoginData):
    logger.info(f"用户登录请求: {data.username}")  # 不需要，中间件已记录
    ...
```

### 16.5 异常日志规范

> **⚠️ 重要约束**: 所有异常必须通过全局异常处理器捕获并记录，禁止在业务代码中捕获异常后仅打印日志而不处理。

```python
# ✅ 正确：让异常冒泡到全局处理器
@router.post("/process")
async def process(data: ProcessData):
    # 不做 try-except，让异常被全局处理器捕获
    result = await service.process(data)
    return Success(data=result)

# ✅ 正确：需要特定处理时，重新抛出
@router.post("/transfer")
async def transfer(data: TransferData):
    try:
        await service.transfer(data)
    except InsufficientBalanceException:
        # 转换为业务异常，会被记录
        raise BusinessException(code=400, msg="余额不足")

# ❌ 错误：捕获异常仅打印日志
@router.post("/process")
async def process(data: ProcessData):
    try:
        result = await service.process(data)
    except Exception as e:
        logger.error(f"处理失败: {e}")  # 不允许！异常被吞掉了
        return Fail(msg="处理失败")  # 没有 request_id，没有调用栈
```

### 16.6 日志脱敏规范

```python
# ✅ 正确：敏感字段自动脱敏
SENSITIVE_FIELDS = {"password", "token", "secret", "api_key", "authorization"}

# 在日志中自动过滤
logger.bind(
    username=user.username,
    password="***",  # 脱敏显示
    token="***"      # 脱敏显示
).info("用户信息")

# ❌ 错误：明文记录敏感信息
logger.info("用户登录", password=raw_password, token=access_token)
```

---

## 17. 公开接口设计规范

### 17.1 目录结构规范

> **⚠️ 重要约束**: 所有通过 API Key 认证的公开接口必须放在 `app/api/public/` 目录下。

```
app/api/
├── __init__.py           # 路由聚合
├── v1/                   # JWT 认证接口（内部使用）
│   ├── base/
│   ├── user/
│   └── ...
└── public/               # API Key 认证接口（外部使用）
    ├── __init__.py       # 公开路由聚合
    ├── autofill.py       # 智能填单接口
    ├── llm_proxy.py      # LLM 代理接口
    └── query_agent.py    # QueryAgent 接口
```

### 17.2 路由注册规范

```python
# app/api/public/__init__.py
"""
公开 API 模块 (API Key 认证)

本目录下的接口都使用 API Key 进行认证，不依赖 JWT，
主要供 Dify、三方应用和外部系统调用。
"""

from fastapi import APIRouter

from .autofill import autofill_public_router
from .llm_proxy import llm_proxy_public_router
from .query_agent import query_agent_public_router

public_router = APIRouter()

# 注册公开接口（无需 prefix，在 app/api/__init__.py 统一设置）
public_router.include_router(autofill_public_router)
public_router.include_router(llm_proxy_public_router, prefix="/api")
public_router.include_router(query_agent_public_router, prefix="/api")

__all__ = ["public_router"]
```

### 17.3 接口定义规范

```python
# app/api/public/autofill.py
from fastapi import APIRouter, Depends, Header
from typing import Optional

from app.core.dependency import AuthControl
from app.schemas.base import Success, Fail

router = APIRouter()

# ✅ 正确：使用 API Key 认证
@router.post("/autofill/llm/fill", summary="智能填单")
async def autofill_llm(
    data: AutoFillRequest,
    app_key: str = Header(..., alias="X-App-Key", description="应用密钥"),
    current_app: App = Depends(AuthControl.is_app_authed),  # API Key 认证
):
    """
    智能填单公开接口
    
    使用 API Key 进行认证，无需 JWT Token
    """
    result = await autofill_service.fill(data)
    return Success(data=result)

# ✅ 正确：可选参数使用 Optional
@router.get("/autofill/result", summary="查询填单结果")
async def get_autofill_result(
    task_id: str,
    include_detail: Optional[bool] = False,  # 可选参数
    app_key: str = Header(..., alias="X-App-Key"),
    current_app: App = Depends(AuthControl.is_app_authed),
):
    result = await autofill_service.get_result(task_id, include_detail)
    return Success(data=result)
```

### 17.4 认证方式对比

| 特性 | JWT 认证 (v1) | API Key 认证 (public) |
|------|--------------|----------------------|
| 认证头 | `Authorization: Bearer {token}` | `X-App-Key: {app_key}` |
| 用户身份 | 具体用户 | 应用/系统 |
| 适用场景 | 内部用户操作 | 第三方系统调用 |
| 权限控制 | 基于用户角色 | 基于应用权限 |
| 租户隔离 | 支持多租户切换 | 固定应用所属租户 |

### 17.5 响应格式规范

> **⚠️ 重要约束**: 公开接口使用与内部接口相同的统一响应格式。

```python
# ✅ 正确：成功响应
{
    "code": 200,
    "msg": "success",
    "data": {
        "task_id": "task_123",
        "status": "completed",
        "result": {...}
    }
}

# ✅ 正确：错误响应（包含 request_id 用于追踪）
{
    "code": 400,
    "msg": "请求参数验证失败",
    "data": {
        "errors": [
            {"field": "body.field_group_id", "msg": "Field required", "type": "missing"}
        ]
    },
    "request_id": "d5329543-0178-456e-b8f8-d62804fc9289"
}

# ✅ 正确：服务器错误（生产环境隐藏详细错误）
{
    "code": 500,
    "msg": "服务器内部错误，请稍后重试",
    "request_id": "d5329543-0178-456e-b8f8-d62804fc9289"
}
```

### 17.6 接口文档规范

```python
@router.post(
    "/autofill/llm/fill",
    summary="智能填单",
    description="""
    智能填单公开接口，支持通过自然语言描述自动填写表单。
    
    ## 认证方式
    使用 `X-App-Key` 请求头进行认证，从应用管理页面获取。
    
    ## 使用示例
    ```python
    import requests
    
    response = requests.post(
        "https://api.example.com/api/autofill/llm/fill",
        headers={"X-App-Key": "your_app_key"},
        json={
            "field_group_id": 123,
            "input_data": {"query": "填写一个北京的用户"}
        }
    )
    ```
    """,
    response_model=Success[AutoFillResponse],
    responses={
        400: {"model": Fail, "description": "参数错误"},
        401: {"model": Fail, "description": "认证失败"},
        429: {"model": Fail, "description": "请求过于频繁"},
    }
)
async def autofill_llm(...):
    pass
```

### 17.7 速率限制规范

```python
# ✅ 正确：公开接口需要添加速率限制
from fastapi_limiter.depends import RateLimiter

@router.post(
    "/autofill/llm/fill",
    summary="智能填单",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))]  # 每分钟10次
)
async def autofill_llm(...):
    pass
```

---

## 18. 架构更新约束

### 18.1 约束文档维护规范

> **⚠️ 重要约束**: 当实现新的架构功能时，必须同步更新 `.trae/docs/tech-constraints.md` 文档。

#### 需要更新的场景

- [ ] 新增日志记录方式或规范
- [ ] 新增异常处理方式
- [ ] 新增接口类型或认证方式
- [ ] 新增代码组织方式（如新目录结构）
- [ ] 新增性能优化方案
- [ ] 新增安全规范

#### 更新流程

```
1. 实现新功能
   ↓
2. 验证功能正常工作
   ↓
3. 更新 tech-constraints.md 相应章节
   ↓
4. 确保示例代码与实际实现一致
   ↓
5. 提交代码时包含文档更新
```

#### 文档章节对应关系

| 功能模块 | 对应章节 |
|---------|---------|
| 日志记录 | 第 16 章 |
| 公开接口 | 第 17 章 |
| 异常处理 | 第 2.10 节 |
| 性能优化 | 第 2.4 节 |
| 安全规范 | 第 2.8、2.9 节 |
| 测试文件管理 | 第 19 章 |
| 架构设计 | [architecture.md](./architecture.md) |

### 18.2 Skill 动态更新要求

> **⚠️ 重要约束**: 创建新的架构实现后，必须检查并更新对应的 Skill 文档。

```bash
# Skill 目录结构
.trae/skills/
├── dev/                    # 开发规范 Skill
│   └── SKILL.md
├── logging/                # 日志规范 Skill（新增）
│   └── SKILL.md
├── api-design/             # 接口设计 Skill（新增）
│   └── SKILL.md
└── exception-handling/     # 异常处理 Skill（新增）
    └── SKILL.md
```

#### Skill 更新检查清单

- [ ] Skill 描述是否准确反映新功能
- [ ] Skill 使用示例是否与新实现一致
- [ ] Skill 触发条件是否覆盖新场景
- [ ] Skill 是否引用了最新的约束文档章节

---

## 19. 测试文件管理规范

### 19.1 测试目录结构

> **⚠️ 重要约束**: 所有测试文件必须放在 `tests/` 目录下，禁止在项目根目录创建测试文件。

```
tests/
├── __init__.py
├── unit/                    # 单元测试 - 测试单个函数/类
│   ├── __init__.py
│   └── test_*.py
├── integration/             # 集成测试 - 测试多个组件交互
│   ├── __init__.py
│   └── test_*.py
├── e2e/                     # 端到端测试 - 测试完整业务流程
│   ├── __init__.py
│   └── test_*.py
└── scripts/                 # 临时/调试脚本
    ├── __init__.py
    └── test_*.py
```

### 19.2 测试分类规范

#### 单元测试 (`tests/unit/`)

**适用场景：**
- 测试单个函数或类
- 测试工具函数、解析器
- 测试业务逻辑
- 测试模型验证

**特点：**
- 执行速度快 (< 100ms)
- 无外部依赖（使用 mock）
- 高代码覆盖率

```python
# ✅ 正确：单元测试示例
# tests/unit/test_curl_parser.py
class TestCurlParser:
    """Curl 解析器测试"""
    
    def test_parse_simple_get(self):
        """测试简单的 GET 请求"""
        curl = "curl https://api.example.com/users"
        result = CurlParser.parse(curl)
        
        assert result.url == "https://api.example.com/users"
        assert result.method == "GET"
```

#### 集成测试 (`tests/integration/`)

**适用场景：**
- 测试 API 端点
- 测试数据库操作
- 测试服务集成
- 测试认证授权

**特点：**
- 可能使用真实数据库
- 测试组件间交互
- 比单元测试慢

```python
# ✅ 正确：集成测试示例
# tests/integration/test_public_api.py
async def test_autofill_api():
    """测试智能填单 API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/public/autofill",
            json={"query": "测试数据"}
        )
        assert response.status_code == 200
```

#### 端到端测试 (`tests/e2e/`)

**适用场景：**
- 测试完整用户故事
- 测试多步骤工作流
- 测试业务场景

**特点：**
- 测试完整业务流程
- 涉及多个 API 调用
- 最慢但最全面

```python
# ✅ 正确：端到端测试示例
# tests/e2e/test_agent_workflow.py
async def test_complete_agent_workflow():
    """测试完整的 Agent 工作流程"""
    # 1. 创建会话
    session = await create_session()
    
    # 2. 发送消息
    response = await send_message(session, "查询上海门店")
    
    # 3. 验证结果
    assert "门店" in response
```

#### 测试脚本 (`tests/scripts/`)

**适用场景：**
- 临时调试脚本
- 一次性验证
- 开发阶段测试

**特点：**
- 不参与 CI/CD
- 可随时删除
- 建议添加时间戳

```python
# ✅ 正确：测试脚本示例
# tests/scripts/test_debug_api_20240115.py
#!/usr/bin/env python3
"""
调试脚本 - 测试特定 API 问题
创建时间: 2024-01-15
创建人: developer
目的: 调试接口响应格式问题
"""

import httpx

async def debug_api():
    # 临时调试代码
    pass

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_api())
```

### 19.3 命名规范

#### 测试文件命名

```
test_<module_name>.py          # 测试对应模块
test_<feature_name>.py         # 测试特定功能
test_<scenario_name>.py        # 测试特定场景
```

**示例：**
- `test_query_agent.py` - 测试 QueryAgent 模块
- `test_curl_parser.py` - 测试 Curl 解析功能
- `test_byd_dealer_search.py` - 测试比亚迪门店搜索场景

#### 测试类/方法命名

```python
# 测试类命名
class Test<ModuleName>:          # 如: TestQueryAgent
    
    # 测试方法命名
    def test_<function>_<scenario>(self):   # 如: test_parse_valid_curl
        pass
    
    def test_<function>_<edge_case>(self):  # 如: test_parse_invalid_curl
        pass
```

### 19.4 创建测试文件流程

#### 步骤 1：确定测试类型

```
测试单个函数？        → tests/unit/
测试 API 端点？       → tests/integration/
测试完整工作流？      → tests/e2e/
临时调试脚本？        → tests/scripts/
```

#### 步骤 2：创建文件

```bash
# 示例：创建单元测试
touch tests/unit/test_<module>.py

# 示例：创建集成测试
touch tests/integration/test_<api>_api.py
```

#### 步骤 3：添加文件头

```python
"""
<Module/Feature Name> 测试

测试范围:
- <测试点1>
- <测试点2>

作者: <name>
创建时间: <date>
"""
```

### 19.5 禁止事项

```python
# ❌ 错误：在项目根目录创建测试文件
# /autofill/test_something.py

# ❌ 错误：命名不清晰
# /autofill/tests/unit/test1.py
# /autofill/tests/unit/test_new.py

# ❌ 错误：混合测试类型
# 单元测试和集成测试写在同一个文件

# ✅ 正确：按规范放置测试文件
# /autofill/tests/unit/test_curl_parser.py
# /autofill/tests/integration/test_public_api.py
# /autofill/tests/e2e/test_agent_workflow.py
```

### 19.6 清理临时脚本

**定期清理 `tests/scripts/` 目录：**

```bash
# 查看脚本创建时间
ls -la tests/scripts/

# 删除超过 30 天的临时脚本
find tests/scripts/ -name "test_*.py" -mtime +30 -delete
```

**保留原则：**
- ✅ 保留：有明确文档说明的调试脚本
- ❌ 删除：无文档、无注释的临时脚本
- ❌ 删除：已解决问题的调试脚本

### 19.7 文档章节对应关系

| 测试类型 | 目录 | 用途 |
|---------|------|------|
| 单元测试 | `tests/unit/` | 测试单个函数/类 |
| 集成测试 | `tests/integration/` | 测试组件交互 |
| 端到端测试 | `tests/e2e/` | 测试完整业务流程 |
| 测试脚本 | `tests/scripts/` | 临时调试 |

### 19.8 Skill 关联

- **test-management**: 测试文件创建、移动、删除管理
- **architecture-update**: 架构变更时更新测试规范

---

## 20. 代码清理规范

### 20.1 核心原则

> **⚠️ 重要约束**: 重构或改造功能后，必须立即删除旧代码，禁止保留兼容性代码。

#### 为什么不要保留旧代码

```
❌ 错误观念："保留旧代码以防万一"
❌ 错误观念："保留兼容性让调用方平滑过渡"
❌ 错误观念："先留着，以后再说"

✅ 正确做法：改造完成 → 验证通过 → 立即删除旧代码
```

**保留旧代码的危害：**
- 代码库膨胀，维护成本增加
- 新开发者困惑（不知道用哪个版本）
- 隐藏 bug（旧代码可能仍有引用）
- 技术债务累积

### 20.2 重构后清理清单

#### 必须删除的内容

```markdown
## 重构后清理检查清单

### 文件清理
- [ ] 旧版服务实现文件
- [ ] 旧版 API 路由文件
- [ ] 旧版类型定义文件
- [ ] 旧版工具函数文件
- [ ] 旧版测试文件（已被新测试替代）

### 代码清理
- [ ] 移除旧版导入语句
- [ ] 移除旧版路由注册
- [ ] 移除旧版配置项
- [ ] 更新引用到新实现

### 文档清理
- [ ] 删除旧版文档
- [ ] 更新引用链接
- [ ] 添加变更说明
```

### 20.3 清理流程

```
1. 实现新功能
   ↓
2. 验证新功能可用（测试通过）
   ↓
3. 立即删除旧代码
   ↓
4. 验证项目仍能正常运行
   ↓
5. 提交代码（包含删除操作）
```

### 20.4 示例：Agent 重构清理

**重构前：**
```
app/services/
├── query_agent/              # 旧版实现
│   ├── __init__.py
│   ├── agent.py
│   ├── nodes.py
│   ├── parser.py
│   ├── types.py
│   ├── utils.py
│   └── prompts.py
└── agent/                    # 新版实现
    ├── __init__.py
    ├── base/
    ├── core/
    └── agents/

app/api/public/
├── query_agent.py            # 旧版 API
└── agents.py                 # 新版 API
```

**重构后（正确做法）：**
```
app/services/
└── agent/                    # 只保留新版
    ├── __init__.py
    ├── base/
    ├── core/
    └── agents/

app/api/public/
└── agents.py                 # 只保留新版
```

**清理操作：**
```bash
# 删除旧版服务
rm -rf app/services/query_agent/

# 删除旧版 API
rm app/api/public/query_agent.py

# 更新路由注册（移除旧版导入和注册）
# vim app/api/public/__init__.py
```

### 20.5 Git 提交规范

**删除代码的提交信息：**
```
chore: remove deprecated query_agent implementation

- Delete app/services/query_agent/ directory
- Delete app/api/public/query_agent.py
- Update public router to remove old imports

The new agent architecture in app/services/agent/
fully replaces the old implementation.
```

### 20.6 禁止事项

```python
# ❌ 错误：保留旧版导入
# app/api/public/__init__.py
from .query_agent import query_agent_public_router  # 旧版
from .agents import agents_router                    # 新版

public_router.include_router(query_agent_public_router)  # 不要保留
public_router.include_router(agents_router)              # 只保留新版

# ❌ 错误：条件编译/运行时切换
if USE_NEW_AGENT:
    from .agents import QueryAgent
else:
    from .query_agent import QueryAgent  # 不要保留

# ❌ 错误：注释掉旧代码而不是删除
# def old_function():  # 不要注释，直接删除
#     pass

# ✅ 正确：只保留新版
from .agents import agents_router
public_router.include_router(agents_router)
```

### 20.7 文档章节对应关系

| 场景 | 操作 |
|------|------|
| 重构服务 | 删除旧服务目录 |
| 重构 API | 删除旧路由文件 + 更新注册 |
| 重构工具函数 | 删除旧工具文件 |
| 重构类型定义 | 删除旧类型文件 |

### 20.8 Skill 关联

- **architecture-update**: 架构变更时执行清理
- **test-management**: 删除旧测试文件

---

## 21. 约束文档章节映射表（完整版）

| 功能模块 | 对应章节 | 说明 |
|---------|---------|------|
| 前端技术约束 | 第 1 章 | Vue/React 开发规范 |
| 后端技术约束 | 第 2 章 | FastAPI/Python 规范 |
| API 认证与多租户 | 第 3 章 | JWT/API Key 认证 |
| 数据库约束 | 第 4 章 | Tortoise ORM 规范 |
| API 设计约束 | 第 5 章 | RESTful API 设计 |
| 前端组件开发 | 第 6 章 | 组件化开发规范 |
| 文件上传 | 第 7 章 | 上传安全规范 |
| 错误处理 | 第 8 章 | 异常处理规范 |
| 日志约束 | 第 9 章 | 日志记录规范 |
| 配置约束 | 第 10 章 | 配置管理规范 |
| 代码生成 | 第 11 章 | 代码生成器规范 |
| 禁止事项清单 | 第 13 章 | 绝对不能做的事 |
| 代码复用架构 | 第 14 章 | 复用设计原则 |
| 检查清单 | 第 15 章 | 代码审查清单 |
| 日志记录规范 | 第 16 章 | 详细日志规范 |
| 公开接口设计 | 第 17 章 | API Key 接口规范 |
| 架构更新约束 | 第 18 章 | 文档更新要求 |
| 测试文件管理 | 第 19 章 | 测试组织规范 |
| 代码清理规范 | 第 20 章 | 重构后清理要求 |
| 脚本目录规范 | 第 21 章 | 脚本文件组织 |
| 架构设计 | [architecture.md](./architecture.md) | 整体架构文档 |

---

## 22. 脚本目录规范

### 22.1 目录结构

```
scripts/
├── db/                    # 数据库相关脚本
│   ├── fix_all_nulls.py      # 修复所有表 NULL 值
│   ├── fix_menu_nulls.py     # 修复菜单表 NULL 值
│   ├── fix_null_values.py    # 修复指定字段 NULL 值
│   └── update_llm_capabilities.py  # 更新 LLM 能力配置
├── init/                  # 数据初始化脚本
│   ├── init_llm_data.py      # 初始化 LLM 提供商和菜单
│   └── init_byd_dealers.py   # 初始化比亚迪门店数据
└── migrations/            # 数据库迁移脚本（Aerich）
```

### 22.2 脚本分类规则

| 类型 | 存放目录 | 说明 | 示例 |
|------|---------|------|------|
| 数据修复 | `scripts/db/` | 修复数据问题、更新字段值 | `fix_null_values.py` |
| 数据初始化 | `scripts/init/` | 初始化基础数据、配置数据 | `init_llm_data.py` |
| 数据迁移 | `scripts/migrations/` | 数据库结构变更（Aerich） | Aerich 自动生成 |
| 临时脚本 | `scripts/temp/` | 一次性临时脚本，用完即删 | 临时数据导出 |

### 22.3 脚本编写规范

```python
#!/usr/bin/env python3
"""
脚本功能说明
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from tortoise import Tortoise
from app.settings.config import settings


async def init_db():
    """初始化数据库连接"""
    db_url = f"mysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models']}
    )


async def main():
    """主函数"""
    await init_db()
    try:
        # 脚本逻辑
        pass
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
```

### 22.4 禁止事项

```python
# ❌ 错误：脚本放在项目根目录
# /autofill/fix_null_values.py

# ❌ 错误：脚本没有数据库连接关闭
async def main():
    await init_db()
    # 缺少 await Tortoise.close_connections()

# ❌ 错误：硬编码数据库连接
await Tortoise.init(
    db_url="mysql://root:123@localhost/db",  # 不要硬编码
)

# ✅ 正确：脚本放在 scripts/ 子目录
# /autofill/scripts/db/fix_null_values.py

# ✅ 正确：使用 settings 配置
db_url = f"mysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}..."

# ✅ 正确：确保关闭连接
try:
    await main()
finally:
    await Tortoise.close_connections()
```

---

*文档最后更新: 2026-05-02*
*版本: v2.1*
