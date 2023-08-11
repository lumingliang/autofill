# 数据库约束

> 本文档包含 Tortoise ORM 数据库设计的所有约束规则。

---

## 1. 数据库设计约束

### 1.1 禁止外键约束

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

## 2. 模型规范

### 2.1 Tortoise ORM 模型规范

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

### 2.2 模型基类

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

## 3. 字段规范

### 3.1 字段定义规范

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

### 3.2 字段默认值规范

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

### 3.3 可空字段设计规范

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

TEXT 类字段默认可以设置为 NULL：

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

### 3.4 默认值规范表

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

---

## 4. 关联表规范

### 4.1 关联表定义

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

### 4.2 关系查询规范

> **⚠️ 重要约束**: 所有关联操作必须通过 RelationQuery。

```python
# ✅ 正确：使用 RelationQuery 进行显式关联查询
from app.core.relation import RelationQuery

# 获取用户的角色ID列表
role_ids = await RelationQuery.get_role_ids_by_user_id(user_id)

# 获取角色的用户ID列表
user_ids = await RelationQuery.get_user_ids_by_role_id(role_id)

# 更新关联关系
await RelationQuery.replace_user_roles(user_id, role_ids)

# 批量获取
user_role_map = await RelationQuery.batch_get_role_ids_by_user_ids(user_ids)

# ❌ 错误：禁止直接查询关联表
from app.models.admin import UserRole
await UserRole.filter(user_id=user_id).delete()  # 禁止！
await UserRole.create(user_id=user_id, role_id=role_id)  # 禁止！
```

---

## 5. 软删除规范

### 5.1 软删除字段定义

```python
# ✅ 正确：软删除字段定义
class User(BaseModel, TimestampMixin):
    """用户模型"""
    username = fields.CharField(max_length=20, description="用户名")
    is_deleted = fields.BooleanField(default=False, description="是否删除标记", index=True)
    deleted_at = fields.DatetimeField(null=True, default=None, description="删除时间")
    
    class Meta:
        table = "user"
```

### 5.2 软删除操作

```python
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

---

## 6. 数据库查询性能规范

### 6.1 避免 N+1 问题

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

### 6.2 复杂场景批量操作

```python
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

---

## 7. 禁止事项清单

- ❌ 禁止使用数据库外键约束（Foreign Key）
- ❌ 禁止使用 Tortoise ORM 的隐式关系查询
- ❌ 禁止直接查询关联表（必须使用 RelationQuery）
- ❌ 禁止在循环中查询数据库（使用批量查询）
- ❌ 禁止查询范围过大的全表扫描（如 `Model.all()` 未加过滤条件）
- ❌ 禁止布尔字段设置为可空
- ❌ 禁止字符串/整数字段无意义地使用 null=True

---

*详细内容请查看 [tech-constraints-core.md](../tech-constraints-core.md)*
*最后更新: 2026-05-05*
