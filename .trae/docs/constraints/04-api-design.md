# API 设计约束

> 本文档包含 RESTful API 设计、认证与多租户的所有约束规则。

---

## 1. RESTful 规范

### 1.1 URL 设计规范

| 操作 | HTTP 方法 | URL 格式 | 示例 |
|------|-----------|----------|------|
| 列表查询 | GET | /{resource}/list | GET /user/list |
| 详情查询 | GET | /{resource}/get | GET /user/get?id=1 |
| 创建 | POST | /{resource}/create | POST /user/create |
| 更新 | POST | /{resource}/update | POST /user/update |
| 删除 | DELETE | /{resource}/delete | DELETE /user/delete?id=1 |

### 1.2 参数规范

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

---

## 2. 响应格式约束

### 2.1 统一响应模型

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

### 2.2 响应规范

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
```

---

## 3. 认证体系

### 3.1 双认证体系架构

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

### 3.2 JWT 认证（内部接口）

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

### 3.3 权限检查

```python
# ✅ 正确：显式检查权限
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

## 4. 公开接口（API Key 认证）

### 4.1 目录结构

```
app/api/
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

### 4.2 路由注册

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

# 注册公开接口
public_router.include_router(autofill_public_router)
public_router.include_router(llm_proxy_public_router, prefix="/api")
public_router.include_router(query_agent_public_router, prefix="/api")

__all__ = ["public_router"]
```

### 4.3 接口定义

```python
from app.core.dependency import AuthControl

@router.post("/autofill/llm/fill", summary="智能填单")
async def autofill_llm(
    data: AutoFillRequest,
    app_key: str = Header(..., alias="X-App-Key", description="应用密钥"),
    current_app: App = Depends(AuthControl.is_app_authed),
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
    include_detail: Optional[bool] = False,
    app_key: str = Header(..., alias="X-App-Key"),
    current_app: App = Depends(AuthControl.is_app_authed),
):
    result = await autofill_service.get_result(task_id, include_detail)
    return Success(data=result)
```

### 4.4 认证方式对比

| 特性 | JWT 认证 (v1) | API Key 认证 (public) |
|------|--------------|----------------------|
| 认证头 | `Authorization: Bearer {token}` | `X-App-Key: {app_key}` |
| 用户身份 | 具体用户 | 应用/系统 |
| 适用场景 | 内部用户操作 | 第三方系统调用 |
| 权限控制 | 基于用户角色 | 基于应用权限 |
| 租户隔离 | 支持多租户切换 | 固定应用所属租户 |

### 4.5 接口文档规范

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

### 4.6 速率限制

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

## 5. 多租户约束

### 5.1 数据隔离规范

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

### 5.2 租户ID获取规范

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

### 5.3 查询范围约束

> **⚠️ 重要约束**: 查询必须限制范围，禁止无过滤条件的全表查询。

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

## 6. 文件上传约束

### 6.1 后端接收

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

## 7. 禁止事项清单

- ❌ 禁止不使用类型注解
- ❌ 禁止所有 API 没有权限控制
- ❌ 禁止返回敏感字段（如 password）
- ❌ 禁止非超级管理员跨租户查询数据
- ❌ 禁止无过滤条件的全表查询
- ❌ 禁止公开接口没有速率限制

---

*详细内容请查看 [tech-constraints-core.md](../tech-constraints-core.md)*
*最后更新: 2026-05-05*
