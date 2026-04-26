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

## 3. 数据库约束

### 3.1 命名规范

| 对象 | 规范 | 示例 |
|------|------|------|
| 表名 | 单数小写 | user, role, menu |
| 字段 | 小写下划线 | user_name, created_at |
| 索引 | idx_表名_字段 | idx_user_username |
| 外键 | fk_表名_关联表 | fk_user_role |
| 关联表 | 表1_表2 | user_role, role_menu |

### 3.2 字段规范

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

### 3.3 关联表规范

```python
# ✅ 正确：关联表定义
class UserRole(BaseModel, TimestampMixin):
    """用户-角色关联表"""
    user_id = fields.IntField(description="用户ID", index=True)
    role_id = fields.IntField(description="角色ID", index=True)
    
    class Meta:
        table = "user_role"
        unique_together = ("user_id", "role_id")  # 联合唯一
```

---

## 4. API 设计约束

### 4.1 RESTful 规范

| 操作 | HTTP 方法 | URL 格式 | 示例 |
|------|-----------|----------|------|
| 列表查询 | GET | /{resource}/list | GET /user/list |
| 详情查询 | GET | /{resource}/get | GET /user/get?id=1 |
| 创建 | POST | /{resource}/create | POST /user/create |
| 更新 | POST | /{resource}/update | POST /user/update |
| 删除 | DELETE | /{resource}/delete | DELETE /user/delete?id=1 |

### 4.2 参数规范

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

### 4.3 响应规范

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

## 5. 前端组件开发约束

### 5.1 CRUD 页面规范

```vue
<template>
  <div class="{module}-page crud-page">
    <a-card>
      <!-- 筛选表单 -->
      <a-form :model="queryParams" class="crud-filter-form smart-filter-form">
        <a-row :gutter="16" class="filter-row">
          <!-- 筛选项 -->
          <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6">
            <a-form-item label="名称" class="filter-item">
              <a-input v-model:value="queryParams.name" placeholder="请输入名称" allow-clear />
            </a-form-item>
          </a-col>
          
          <!-- 操作按钮 -->
          <a-col v-bind="getActionColProps" class="filter-actions-col">
            <a-form-item class="filter-actions">
              <a-space>
                <a-button type="primary" @click="handleSearch">
                  <SearchOutlined /> 查询
                </a-button>
                <a-button @click="handleReset">
                  <ReloadOutlined /> 重置
                </a-button>
              </a-space>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>

      <!-- 操作按钮区 -->
      <div class="table-actions">
        <a-button v-permission="'post/api/v1/{module}/create'" type="primary" @click="handleAdd">
          <PlusOutlined /> 新增
        </a-button>
      </div>

      <!-- 数据表格 -->
      <a-table
        class="crud-table"
        :columns="columns"
        :data-source="tableData"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
        :scroll="{ x: 'max-content' }"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button v-permission="'post/api/v1/{module}/update'" type="link" @click="handleEdit(record)">
                编辑
              </a-button>
              <a-popconfirm title="确定删除吗？" @confirm="handleDelete(record)">
                <a-button v-permission="'delete/api/v1/{module}/delete'" type="link" danger>
                  删除
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新增/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="modalTitle"
      :confirm-loading="modalLoading"
      @ok="handleSave"
      @cancel="modalVisible = false"
    >
      <a-form
        ref="modalFormRef"
        :model="modalForm"
        :rules="modalRules"
        :label-col="{ span: 6 }"
        :wrapper-col="{ span: 16 }"
      >
        <!-- 表单字段 -->
      </a-form>
    </a-modal>
  </div>
</template>
```

### 5.2 表格列定义规范

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

### 5.3 表单验证规范

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

## 6. 文件上传约束

### 6.1 前端上传

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

### 6.2 后端接收

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

## 7. 错误处理约束

### 7.1 前端错误处理

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

### 7.2 后端错误处理

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

## 8. 日志约束

### 8.1 后端日志

```python
from app.log import logger

# ✅ 正确：使用结构化日志
logger.info(f"用户登录成功: {user.username}")
logger.error(f"操作失败: {str(error)}")

# ✅ 正确：审计日志自动记录（通过中间件）
# HttpAuditLogMiddleware 会自动记录所有请求
```

---

## 9. 配置约束

### 9.1 环境配置

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

### 9.2 前端配置

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

## 10. 代码生成约束

### 10.1 生成新模块步骤

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

### 10.2 必须遵守的导入路径

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

## 11. 禁止事项清单

### 11.1 前端禁止

- ❌ 禁止使用 Options API
- ❌ 禁止使用 `any` 类型（除非必要）
- ❌ 禁止直接修改 Pinia State（必须通过 action）
- ❌ 禁止在模板中写复杂表达式
- ❌ 禁止使用未注册的组件
- ❌ 禁止直接操作 DOM（使用 Vue 的 ref）
- ❌ 禁止在组件中直接调用 axios（使用封装的 request）

### 11.2 后端禁止

- ❌ 禁止不使用类型注解
- ❌ 禁止直接查询关联表（必须使用 RelationQuery）
- ❌ 禁止在控制器中写 SQL
- ❌ 禁止明文存储密码
- ❌ 禁止返回敏感字段（如 password）
- ❌ 禁止非超级管理员跨租户查询数据
- ❌ 禁止在循环中查询数据库（使用批量查询）
- ❌ 禁止查询范围过大的全表扫描（如 `Model.all()` 未加过滤条件）

---

## 12. 检查清单

### 12.1 代码提交前检查

- [ ] 前端代码通过 TypeScript 编译
- [ ] 后端代码通过 ruff 检查
- [ ] 后端代码通过 black 格式化
- [ ] 所有 API 都有权限控制
- [ ] 敏感数据已排除（password 等）
- [ ] 多租户数据隔离正确
- [ ] 表单验证规则完整
- [ ] 错误处理完善
