# Vue FastAPI Admin 核心约束文档

> 本文档包含最关键的约束规则，按领域拆分到 `constraints/` 目录。

---

## 0. 代码文件行数约束

> **⚠️ 重要约束**: 单个代码文件最大行数限制为 **600 行**。

### 0.1 为什么限制 600 行

- **可读性**: 超过 600 行的文件难以快速理解
- **维护性**: 小文件更容易定位和修复问题
- **AI 友好**: 便于 AI 助手完整加载和分析
- **测试性**: 小文件更容易编写单元测试

### 0.2 文件拆分策略

当文件接近 600 行时，按以下策略拆分：

```
# ❌ 错误：单个文件过大
views/user/index.vue (1200行)
services/agent/core.py (1500行)

# ✅ 正确：按职责拆分
views/user/
├── index.vue          # 主页面 (< 600行)
├── composables/
│   ├── useUserTable.ts    # 表格逻辑
│   ├── useUserForm.ts     # 表单逻辑
│   └── useUserPermission.ts # 权限逻辑

services/agent/core/
├── __init__.py
├── extractor.py       # 数据提取
├── validator.py       # 数据验证
├── transformer.py     # 数据转换
└── utils.py           # 工具函数
```

### 0.3 拆分原则

| 文件类型 | 拆分方式 | 示例 |
|---------|---------|------|
| Vue 组件 | 按功能拆分为 composables | `useTable.ts`, `useForm.ts` |
| Python Service | 按职责拆分为多个模块 | `extractor.py`, `validator.py` |
| API 路由 | 按资源拆分为多个文件 | `user.py`, `role.py` |
| 工具函数 | 按类别拆分为多个文件 | `date.ts`, `format.ts` |

### 0.4 检查清单

- [ ] 单个文件不超过 600 行
- [ ] 拆分后的文件职责单一
- [ ] 避免循环依赖
- [ ] 保持合理的目录深度（不超过 3 层）

---

## 1. 前端核心约束

### 1.1 Vue 3 组合式 API 规范

```typescript
// ✅ 正确：使用 <script setup> 语法
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

defineOptions({ name: '组件名称' })

const props = withDefaults(defineProps<{
  title: string
  visible?: boolean
}>(), {
  visible: false
})

const emit = defineEmits<{
  update: [value: string]
  submit: []
}>()

const loading = ref(false)
const displayTitle = computed(() => props.title || '默认标题')

onMounted(() => {
  initData()
})

async function initData() {
  // 实现
}
</script>
```

**禁止事项：**
- ❌ 禁止使用 Options API
- ❌ 禁止使用 `any` 类型（除非必要）
- ❌ 禁止组件模板有多个根元素
- ❌ 禁止直接修改 Pinia State

### 1.2 表格页面必须使用 CrudTable

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
      show-modal
      :modal-title="modalTitle"
      :modal-form="modalForm"
      @search="handleSearch"
      @modal-ok="handleSave"
    >
      <template #filter-items>
        <!-- 筛选条件 -->
      </template>
      <template #actions>
        <!-- 操作按钮 -->
      </template>
    </CrudTable>
  </div>
</template>
```

---

## 2. 后端核心约束

### 2.1 Python 类型注解强制

```python
# ✅ 正确：所有函数参数和返回值必须加类型注解
async def get_user_by_id(user_id: int) -> Optional[User]:
    return await User.filter(id=user_id).first()

async def list_users(page: int, page_size: int) -> Tuple[int, List[User]]:
    total = await User.all().count()
    users = await User.all().offset((page - 1) * page_size).limit(page_size)
    return total, users
```

### 2.2 禁止使用 Tortoise ORM 隐式关系

```python
# ❌ 禁止：隐式关系查询
user = await User.get(id=user_id)
roles = await user.roles  # 禁止！
for role in await user.roles.all():  # 禁止！
    pass

# ✅ 正确：使用 RelationQuery
from app.core.relation import RelationQuery

role_ids = await RelationQuery.get_role_ids_by_user_id(user_id)
await RelationQuery.replace_user_roles(user_id, role_ids)
```

### 2.3 禁止在循环中查询数据库

```python
# ❌ 错误：N+1 问题
for user_id in user_ids:
    user = await User.get(id=user_id)  # 每次循环都查询

# ✅ 正确：批量查询
user_list = await User.filter(id__in=user_ids).all()

# ✅ 正确：批量更新
await User.filter(id__in=user_ids).update(is_active=True)
```

### 2.4 禁止函数内 Import

```python
# ❌ 绝对禁止
async def refresh_api(self):
    from app import app  # 禁止！

def process_data(data):
    import json  # 禁止！

# ✅ 正确：所有 import 在文件顶部
import json
from app import app
```

---

## 3. 数据库核心约束

### 3.1 禁止外键约束

```python
# ❌ 错误：使用外键
class Order(BaseModel):
    user = fields.ForeignKeyField("models.User", related_name="orders")

# ✅ 正确：使用普通字段
class Order(BaseModel):
    user_id = fields.IntField(description="用户ID", index=True)
```

### 3.2 字段默认值规范

```python
# ❌ 错误：使用 null=True
name = fields.CharField(max_length=100, null=True, description="名称")

# ✅ 正确：使用默认值
name = fields.CharField(max_length=100, default="", description="名称")
status = fields.IntField(default=0, description="状态")
is_active = fields.BooleanField(default=True, description="是否激活")
```

**允许 null=True 的场景：**
- 可选时间字段（deleted_at, last_login_at）
- 大文本字段（TEXT/LONGTEXT）

---

## 4. API 设计核心约束

### 4.1 RESTful 规范

| 操作 | HTTP 方法 | URL 格式 |
|------|-----------|----------|
| 列表查询 | GET | /{resource}/list |
| 详情查询 | GET | /{resource}/get?id=1 |
| 创建 | POST | /{resource}/create |
| 更新 | POST | /{resource}/update |
| 删除 | DELETE | /{resource}/delete?id=1 |

### 4.2 统一响应格式

```python
# 成功响应
return Success(data=user_dict)
return SuccessExtra(data=data, total=total, page=page, page_size=page_size)

# 错误响应
return Fail(code=400, msg="用户已存在")
```

### 4.3 多租户数据隔离

```python
async def list_user(current_user: User = Depends(AuthControl.is_authed)):
    q = Q()
    
    # 非超级管理员必须筛选当前租户
    if not is_superuser(current_user):
        tenant_user_ids = await RelationQuery.get_user_ids_by_tenant_id(
            current_user.current_tenant_id
        )
        q &= Q(id__in=tenant_user_ids)
    
    total, users = await user_controller.list(page=1, page_size=10, search=q)
    return SuccessExtra(data=users, total=total, page=1, page_size=10)
```

**租户ID获取规范：**
- 超管：从请求参数获取 `data.tenant_id`
- 普通账号：从JWT获取 `current_user.current_tenant_id`

---

## 5. 架构分层约束

### 5.1 依赖方向（必须遵守）

```
API 层 (Routers) → Controller 层 → Service 层 → Model 层
```

**禁止反向依赖：**
```python
# ❌ 禁止：Service 层导入 Controller
from app.controllers.llm_config import llm_config_controller  # 禁止！

# ✅ 正确：Service 层直接操作 Model
from app.models.llm_config import LLMConfig
```

### 5.3 LLM 配置全局化约束

**核心原则：LLM 配置是全局资源，不涉及租户隔离**

```python
# ❌ 禁止：LLMConfig 包含租户相关字段
tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)

# ❌ 禁止：Service 层接收租户参数
async def get_default_config(tenant_id: int, app_name: str)  # 禁止！

# ✅ 正确：LLMConfig 纯全局配置
class LLMConfig(BaseModel):
    name = fields.CharField(max_length=128, description="配置名称")
    is_default = fields.BooleanField(default=False, description="是否为默认配置")
    # ... 其他配置字段

# ✅ 正确：Service 层无租户参数
async def get_default_config() -> Optional[LLMConfig]:
    return await LLMConfig.filter(is_default=True, is_active=True).first()
```

**调用规范：**
```python
# ✅ 正确：Handler 直接调用 Service
from app.services.llm.llm_config_service import llm_config_service

config = await llm_config_service.get_default_config()

# ✅ 正确：Controller 复用 Service 逻辑
async def get_default_config(self) -> Optional[LLMConfig]:
    return await llm_config_service.get_default_config()
```

### 5.2 控制器继承 CRUDBase

```python
from app.core.crud import CRUDBase

class UserController(CRUDBase[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(model=User)
    
    async def create_user(self, obj_in: UserCreate) -> User:
        obj_in.password = get_password_hash(password=obj_in.password)
        obj = await self.create(obj_in)
        
        if obj_in.role_ids:
            await RelationQuery.replace_user_roles(obj.id, obj_in.role_ids)
        
        return obj

user_controller = UserController()
```

---

## 6. 日志约束

### 6.1 使用项目统一日志模块

```python
# ✅ 正确
from app.log import getLogger
logger = getLogger(__name__)
logger.info("用户登录成功", user_id=user.id)

# ❌ 错误
import logging
from loguru import logger
```

### 6.2 结构化日志

```python
logger.info(
    "订单处理完成",
    order_id=order.id,
    user_id=order.user_id,
    duration_ms=processing_time
)
```

---

## 7. 公开接口（API Key 认证）

### 7.1 目录结构

```
app/api/
├── v1/                   # JWT 认证接口
└── public/               # API Key 认证接口
    ├── autofill.py
    ├── llm_proxy.py
    └── query_agent.py
```

### 7.2 接口定义

```python
from app.core.dependency import AuthControl

@router.post("/autofill/llm/fill", summary="智能填单")
async def autofill_llm(
    data: AutoFillRequest,
    app_key: str = Header(..., alias="X-App-Key", description="应用密钥"),
    current_app: App = Depends(AuthControl.is_app_authed),
):
    result = await autofill_service.fill(data)
    return Success(data=result)
```

---

## 8. 快速检查清单

### 代码提交前检查

- [ ] 前端代码通过 TypeScript 编译
- [ ] 后端代码通过 ruff 检查
- [ ] 后端代码通过 black 格式化
- [ ] 所有 API 都有权限控制
- [ ] 敏感数据已排除（password 等）
- [ ] 多租户数据隔离正确
- [ ] 表格页面使用 CrudTable 组件
- [ ] 控制器继承 CRUDBase
- [ ] 没有在函数内的 import
- [ ] 关联操作使用 RelationQuery

### 禁止事项清单

**前端：**
- ❌ 禁止使用 Options API
- ❌ 禁止使用 `any` 类型
- ❌ 禁止直接修改 Pinia State
- ❌ 禁止组件多个根元素
- ❌ 禁止重复编写表格代码（必须使用 CrudTable）

**后端：**
- ❌ 禁止不使用类型注解
- ❌ 禁止直接查询关联表（必须使用 RelationQuery）
- ❌ 禁止在循环中查询数据库
- ❌ 禁止函数内 import
- ❌ 禁止明文存储密码
- ❌ 禁止返回敏感字段
- ❌ 禁止非超级管理员跨租户查询
- ❌ 禁止外键约束
- ❌ 禁止无过滤的全表查询

---

## 9. 章节映射表

| 功能模块 | 完整文档章节 | 说明 |
|---------|-------------|------|
| 前端技术 | 第 1、6 章 | Vue/Pinia/组件规范 |
| 后端技术 | 第 2 章 | FastAPI/Python 规范 |
| 数据库 | 第 4 章 | Tortoise ORM 规范 |
| API 设计 | 第 5、17 章 | RESTful/API Key 规范 |
| 日志 | 第 16 章 | 日志记录规范 |
| 测试 | 第 19 章 | 测试文件管理 |
| Import 规范 | 第 23 章 | Python Import 约束 |

---

*本文档为精简版，详细内容请查看 [tech-constraints.md](./tech-constraints.md)*
*最后更新: 2026-05-05*
