# 后端技术约束

> 本文档包含 Python + FastAPI 后端开发的所有约束规则。

---

## 1. Python 代码规范

### 1.1 基础规范

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

### 1.2 类型注解强制使用

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

### 1.3 禁止函数内 Import

> **⚠️ 绝对禁止**: 严禁在函数、方法内部进行 `import` 操作。

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

## 2. 模型约束

### 2.1 Tortoise ORM 模型规范

> **⚠️ 重要约束**: 禁止使用 Tortoise ORM 的隐式关系查询。

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

### 2.2 关系查询规范

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

### 2.3 模型基类

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

---

## 3. Schema 约束

### 3.1 Pydantic Schema 规范

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

### 3.2 Schema 复用规范

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

---

## 4. 控制器约束

### 4.1 CRUD 控制器规范

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

### 4.2 数据库查询性能规范

> **⚠️ 重要约束**: 数据库查询必须避免在 for 循环内进行单条查询或更新。

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
```

---

## 5. API 路由约束

### 5.1 路由定义规范

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

### 5.2 标准 CRUD API 模板

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

---

## 6. 响应格式约束

### 6.1 统一响应模型

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

### 6.2 响应规范

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

## 7. 认证与权限约束

### 7.1 认证依赖

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

### 7.2 权限检查

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

---

## 8. 多租户约束

### 8.1 数据隔离规范

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

### 8.2 租户ID获取规范

> **⚠️ 重要约束**: 接口中租户ID的获取必须区分超管和普通用户。

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

---

## 9. 架构分层约束

### 9.1 依赖方向（必须遵守）

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

### 9.2 Service 层设计原则

- Service 应该是无状态的，不保存请求相关的状态
- Service 方法应该明确输入输出，便于单元测试
- 复杂的业务校验应该在 Service 中完成
- **⚠️ 禁止**: Service 层禁止依赖 Controller 层

---

## 10. 错误处理约束

### 10.1 后端错误处理

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

### 10.2 异常日志规范

> **⚠️ 重要约束**: 所有异常必须通过全局异常处理器捕获并记录。

```python
# ✅ 正确：让异常冒泡到全局处理器
@router.post("/process")
async def process(data: ProcessData):
    # 不做 try-except，让异常被全局处理器捕获
    result = await service.process(data)
    return Success(data=result)

# ❌ 错误：捕获异常仅打印日志
@router.post("/process")
async def process(data: ProcessData):
    try:
        result = await service.process(data)
    except Exception as e:
        logger.error(f"处理失败: {e}")  # 不允许！异常被吞掉了
        return Fail(msg="处理失败")
```

---

## 11. 文件行数约束

> **⚠️ 重要约束**: 单个代码文件最大行数限制为 **600 行**。

### 11.1 Python 模块拆分策略

```
# ❌ 错误：单个文件过大
services/agent/core.py (1500行)

# ✅ 正确：按职责拆分
services/agent/core/
├── __init__.py          # 导出公共接口
├── extractor.py         # 数据提取 (< 600行)
├── validator.py         # 数据验证 (< 600行)
├── transformer.py       # 数据转换 (< 600行)
├── processor.py         # 处理器 (< 600行)
└── utils.py             # 工具函数 (< 600行)
```

### 11.2 Service 层拆分示例

```python
# services/agent/core/extractor.py
from typing import Dict, Any
from app.log import logger

class DataExtractor:
    """数据提取器"""
    
    async def extract(self, source: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """从源提取数据"""
        logger.info("提取数据", source=source)
        # 实现...
        return {}


# services/agent/core/validator.py
from typing import Dict, Any

class DataValidator:
    """数据验证器"""
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """验证数据"""
        # 实现...
        return True
```

### 11.3 API 路由拆分

```python
# api/v1/user/__init__.py
from fastapi import APIRouter
from . import users, roles, permissions

router = APIRouter()
router.include_router(users.router, prefix="/users")
router.include_router(roles.router, prefix="/roles")
router.include_router(permissions.router, prefix="/permissions")

# api/v1/user/users.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/list")
async def list_users():
    pass

@router.post("/create")
async def create_user():
    pass
```

---

## 12. 禁止事项清单

- ❌ 禁止不使用类型注解
- ❌ 禁止直接查询关联表（必须使用 RelationQuery）
- ❌ 禁止在控制器中写 SQL
- ❌ 禁止明文存储密码
- ❌ 禁止返回敏感字段（如 password）
- ❌ 禁止非超级管理员跨租户查询数据
- ❌ 禁止在循环中查询数据库（使用批量查询）
- ❌ 禁止查询范围过大的全表扫描（如 `Model.all()` 未加过滤条件）
- ❌ 禁止函数内 import
- ❌ 禁止单个文件超过 600 行

---

*详细内容请查看 [tech-constraints-core.md](../tech-constraints-core.md)*
*最后更新: 2026-05-05*
