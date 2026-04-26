# 智能填单系统（AutoFill）详细实现文档

## 一、项目现状分析

### 1.1 技术栈
- **后端**: Python 3.11 + FastAPI 0.111 + Tortoise ORM + MySQL 8.0
- **前端**: TypeScript + Axios + ant-design-vue
- **认证**: JWT Token (Header: `token`)
- **权限**: RBAC (用户-角色-菜单/API)
- **部署**: Docker + Docker Compose

### 1.2 现有目录结构
```
autofill/
├── app/                          # 后端主目录
│   ├── api/v1/                   # API路由 (users, roles, menus, tenants...)
│   ├── controllers/              # 控制器层 (CRUD封装)
│   ├── core/                     # 核心模块 (middlewares, crud, exceptions, dependency)
│   ├── models/                   # 数据模型 (Tortoise ORM)
│   ├── schemas/                  # Pydantic 校验模型
│   ├── services/                 # 业务服务层
│   ├── settings/                 # 配置管理
│   └── utils/                    # 工具函数
├── frontend/                     # 管理后台前端 (Vue3)
│   ├── src/api/index.ts          # API 统一封装
│   ├── src/components/CrudTable/ # 通用CRUD表格组件
│   ├── src/views/system/         # 系统管理页面
│   └── src/utils/request.ts      # Axios 请求拦截
├── doc/                          # 文档目录
├── config.toml                   # 配置文件
└── requirements.txt              # Python依赖
```

### 1.3 现有核心组件
- **BaseModel**: 基础模型 (id: BigInt, created_at, updated_at)
- **CRUDBase**: 通用CRUD控制器 (list/create/update/remove)
- **AuthControl**: JWT认证依赖注入
- **PermissionControl**: 接口权限校验
- **CrudTable**: 前端通用表格组件 (过滤/分页/操作)

---

## 二、新增模块设计

### 2.1 数据模型设计 (Tortoise ORM)

#### 2.1.1 应用管理表 (AppManagement)
```python
class AppManagement(BaseModel, TimestampMixin):
    app_name = fields.CharField(max_length=128, default="", description="应用名称(英文)", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    api_key = fields.CharField(max_length=256, default="", description="API密钥", unique=True, index=True)
    dify_url = fields.CharField(max_length=512, default="", description="Dify服务地址")
    dify_api_key = fields.CharField(max_length=256, default="", description="Dify API密钥")
    description = fields.CharField(max_length=500, null=True, description="应用描述")
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)

    class Meta:
        table = "app_management"
        unique_together = ("tenant_id", "app_name")
```

**设计说明**:
- `api_key` 采用 `af_{32位随机字符串}` 格式
- 增加 `dify_url` 和 `dify_api_key` 字段，用于存储该应用对应的Dify配置
- `is_active` 控制应用是否可用

#### 2.1.2 总结类填单模板表 (SummaryTemplate)
```python
class SummaryTemplate(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=256, default="", description="模板名称", index=True)
    app_name = fields.CharField(max_length=128, default="", description="应用名称", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    class_name = fields.CharField(max_length=128, default="", description="模板分类", index=True)
    summary = fields.CharField(max_length=2000, default="", description="模板摘要")
    template_content = fields.TextField(null=True, description="模板内容")

    class Meta:
        table = "summary_template"
        unique_together = ("tenant_id", "app_name", "class_name", "name")
```

**设计说明**:
- `summary` 使用 2000 长度，适应中文大段描述
- `template_content` 使用 TextField，存储大段模板内容

#### 2.1.3 下拉选项类填单模板表 (DropdownOption)
```python
class DropdownOption(BaseModel, TimestampMixin):
    domain = fields.CharField(max_length=512, default="", description="应用域名", index=True)
    summary = fields.CharField(max_length=2000, default="", description="字段摘要")
    description = fields.TextField(null=True, description="详细说明")
    class_name = fields.CharField(max_length=128, default="", description="模板分类", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    app_name = fields.CharField(max_length=128, default="", description="应用名称", index=True)
    parent_id = fields.BigIntField(default=0, description="父选项ID，0表示顶级选项", index=True)
    option_value = fields.CharField(max_length=512, default="", description="选项值", index=True)
    class Meta:
        table = "dropdown_option"
        unique_together = ("tenant_id", "app_name", "class_name", "parent_id", "option_value")
```

**设计说明**:
- `option_value` 同时作为字段标识和选项值，简化模型设计
- `parent_id` 关联本表ID，0表示顶级选项，支持多级级联
- 单条记录存储单个选项值，便于级联查询和独立维护

#### 2.1.4 填单数据记录表 (FillDataRecord)
```python
class FillDataRecord(BaseModel, TimestampMixin):
    session_id = fields.CharField(max_length=256, default="", description="会话ID", index=True)
    phone = fields.CharField(max_length=32, default="", description="手机号", index=True)
    user_unique_id = fields.CharField(max_length=256, default="", description="用户唯一标识", index=True)
    user_name = fields.CharField(max_length=256, default="", description="用户名称", index=True)
    app_name = fields.CharField(max_length=128, default="", description="应用名称", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    data = fields.JSONField(null=True, description="填单数据")

    class Meta:
        table = "fill_data_record"
        unique_together = ("session_id", "tenant_id", "app_name")
```

### 2.2 数据库索引设计

```sql
-- 应用管理表索引
CREATE UNIQUE INDEX uk_app_management_api_key ON app_management(api_key);
CREATE UNIQUE INDEX uk_app_management_tenant_app ON app_management(tenant_id, app_name);
CREATE INDEX idx_app_management_tenant ON app_management(tenant_id);

-- 总结模板表索引
CREATE UNIQUE INDEX uk_summary_template ON summary_template(tenant_id, app_name, class_name, name);
CREATE INDEX idx_summary_template_tenant_app ON summary_template(tenant_id, app_name);
CREATE INDEX idx_summary_template_class ON summary_template(class_name);

-- 下拉选项表索引
CREATE UNIQUE INDEX uk_dropdown_option ON dropdown_option(tenant_id, app_name, class_name, parent_id, option_value);
CREATE INDEX idx_dropdown_option_tenant_app ON dropdown_option(tenant_id, app_name);
CREATE INDEX idx_dropdown_option_class ON dropdown_option(class_name);
CREATE INDEX idx_dropdown_option_parent ON dropdown_option(parent_id);
CREATE INDEX idx_dropdown_option_value ON dropdown_option(option_value);

-- 填单记录表索引
CREATE UNIQUE INDEX uk_fill_data_record ON fill_data_record(session_id, tenant_id, app_name);
CREATE INDEX idx_fill_data_record_phone ON fill_data_record(phone);
CREATE INDEX idx_fill_data_record_user ON fill_data_record(user_unique_id);
CREATE INDEX idx_fill_data_record_time ON fill_data_record(created_at);
```

---

## 三、API 接口详细设计

### 3.1 接口路由规划

```
/api/v1/autofill/app          # 应用管理 (需权限)
/api/v1/autofill/template     # 总结模板管理 (需权限)
/api/v1/autofill/dropdown     # 下拉选项管理 (需权限)
/api/v1/autofill/record       # 填单记录管理 (需权限)

/autofill/summary_template/list     # Dify调用 (Bearer认证)
/autofill/summary_template          # Dify调用 (Bearer认证)
/autofill/dropdown_options/list     # Dify调用 (Bearer认证)
/autofill/dropdown_options          # Dify调用 (Bearer认证)
/autofill/record_fill_data          # Dify调用 (Bearer认证)
/autofill/get_ai_fill_data          # 三方应用调用 (Bearer认证)
```

### 3.2 管理后台接口 (需 JWT + 权限)

#### 3.2.1 应用管理接口
```python
# 创建应用
POST /api/v1/autofill/app/create
Body: {
    "app_name": "insurance_claim",
    "tenant_id": 1,
    "description": "保险理赔应用",
    "dify_url": "https://dify.example.com/v1",
    "dify_api_key": "app-xxxxxxxx"
}
Response: { "code": 200, "data": { "id": 1, "app_name": "...", "api_key": "af_1_abc123..." } }

# 列表查询
GET /api/v1/autofill/app/list?page=1&page_size=10&app_name=&tenant_id=
Response: { "code": 200, "data": { "total": 10, "items": [...] } }

# 更新应用
POST /api/v1/autofill/app/update
Body: { "id": 1, "app_name": "...", "description": "..." }

# 删除应用
DELETE /api/v1/autofill/app/delete?id=1
```

#### 3.2.2 总结模板管理接口
```python
# 创建模板
POST /api/v1/autofill/template/create
Body: {
    "name": "车险理赔模板",
    "app_name": "insurance_claim",
    "tenant_id": 1,
    "class_name": "vehicle",
    "summary": "用于车险理赔场景的填单模板",
    "template_content": "..."
}

# 列表查询
GET /api/v1/autofill/template/list?page=1&page_size=10&app_name=&class_name=&name=

# 更新模板
POST /api/v1/autofill/template/update
Body: { "id": 1, "name": "...", "template_content": "..." }

# 删除模板
DELETE /api/v1/autofill/template/delete?id=1
```

#### 3.2.3 下拉选项管理接口
```python
# 创建选项
POST /api/v1/autofill/dropdown/create
Body: {
    "domain": "claim.example.com",
    "summary": "车辆类型",
    "description": "...",
    "class_name": "vehicle",
    "tenant_id": 1,
    "app_name": "insurance_claim",
    "parent_id": 0,
    "option_value": "vehicle_type"
}

# 列表查询 (支持树形结构)
GET /api/v1/autofill/dropdown/list?page=1&page_size=10&app_name=&parent_id=

# 查询树形结构 (用于级联选择器)
GET /api/v1/autofill/dropdown/tree?app_name=&parent_id=

# 更新选项
POST /api/v1/autofill/dropdown/update

# 删除选项
DELETE /api/v1/autofill/dropdown/delete?id=1
```

#### 3.2.4 填单记录管理接口
```python
# 列表查询
GET /api/v1/autofill/record/list?page=1&page_size=10&app_name=&phone=&user_unique_id=&session_id=
Response: {
    "code": 200,
    "data": {
        "total": 100,
        "items": [
            {
                "id": 1,
                "session_id": "sess_abc123",
                "phone": "13800138000",
                "user_name": "张三",
                "app_name": "insurance_claim",
                "data": { "vehicle_type": "轿车", "damage_desc": "..." },
                "created_at": "2024-01-01 10:00:00"
            }
        ]
    }
}

# 查看详情
GET /api/v1/autofill/record/get?id=1

# 更新数据 (JSON编辑器)
POST /api/v1/autofill/record/update
Body: { "id": 1, "data": { "key": "value" } }

# 删除记录
DELETE /api/v1/autofill/record/delete?id=1
```

### 3.3 Dify/三方调用接口 (Bearer认证)

#### 3.3.1 API Key 认证中间件
```python
class APIKeyAuth:
    @classmethod
    async def authenticate(cls, authorization: str = Header(...)) -> dict:
        """
        解析 Authorization: Bearer {api_key}
        返回: {"tenant_id": int, "app_name": str, "domain": str, "dify_url": str, "dify_api_key": str}
        """
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        api_key = authorization.replace("Bearer ", "").strip()
        
        # Redis 缓存查询
        cache_key = f"api_key:{api_key}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # 数据库查询
        app = await AppManagement.filter(api_key=api_key, is_active=True).first()
        if not app:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # 查询租户域名
        tenant = await Tenant.filter(id=app.tenant_id).first()
        domain = tenant.domain if tenant else ""
        
        result = {
            "tenant_id": app.tenant_id,
            "app_name": app.app_name,
            "domain": domain,
            "dify_url": app.dify_url,
            "dify_api_key": app.dify_api_key,
        }
        
        # 写入缓存 (1小时)
        await redis.setex(cache_key, 3600, json.dumps(result))
        return result
```

#### 3.3.2 查询模板列表
```python
@router.post("/autofill/summary_template/list")
async def list_summary_templates(
    body: SummaryTemplateListRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据 tenant_id + app_name + class_name 查询模板列表
    """
    q = Q(tenant_id=auth_info["tenant_id"], app_name=auth_info["app_name"])
    if body.class_name:
        q &= Q(class_name=body.class_name)
    
    templates = await SummaryTemplate.filter(q).all()
    return {
        "code": 200,
        "data": [
            {"id": t.id, "name": t.name, "summary": t.summary}
            for t in templates
        ]
    }
```

#### 3.3.3 查询模板详情
```python
@router.post("/autofill/summary_template")
async def get_summary_template(
    body: SummaryTemplateDetailRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据ID查询模板详情
    """
    template = await SummaryTemplate.filter(
        id=body.id,
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"]
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "code": 200,
        "data": {
            "id": template.id,
            "name": template.name,
            "summary": template.summary,
            "template_content": template.template_content
        }
    }
```

#### 3.3.4 查询下拉选项列表
```python
@router.post("/autofill/dropdown_options/list")
async def list_dropdown_options(
    body: DropdownOptionListRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据 app_name/domain + class_name + parent_id 查询下拉选项列表
    """
    q = Q(tenant_id=auth_info["tenant_id"], app_name=auth_info["app_name"])
    if body.class_name:
        q &= Q(class_name=body.class_name)
    
    # parent_id 默认为0，表示查询顶级选项
    parent_id = body.parent_id or 0
    q &= Q(parent_id=parent_id)
    
    options = await DropdownOption.filter(q).all()
    return {
        "code": 200,
        "data": [
            {
                "id": o.id,
                "option_value": o.option_value,
                "summary": o.summary,
                "has_children": await DropdownOption.filter(parent_id=o.id).exists()
            }
            for o in options
        ]
    }
```

#### 3.3.5 查询下拉选项详情
```python
@router.post("/autofill/dropdown_options")
async def get_dropdown_option(
    body: DropdownOptionDetailRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据ID查询选项详情及其子选项
    """
    # 根据ID查询选项
    option = await DropdownOption.filter(
        id=body.id,
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"]
    ).first()
    
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    
    # 查询子选项
    children = await DropdownOption.filter(
        tenant_id=auth_info["tenant_id"],
        app_name=auth_info["app_name"],
        parent_id=option.id
    ).all()
    
    return {
        "code": 200,
        "data": {
            "id": option.id,
            "option_value": option.option_value,
            "summary": option.summary,
            "description": option.description,
            "children": [
                {"id": c.id, "option_value": c.option_value, "summary": c.summary}
                for c in children
            ]
        }
    }
```

#### 3.3.6 记录填单数据 (核心合并逻辑)
```python
@router.post("/autofill/record_fill_data")
async def record_fill_data(
    body: RecordFillDataRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 记录填单数据，支持数据合并
    """
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    
    # 查询现有记录
    record = await FillDataRecord.filter(
        session_id=body.session_id,
        tenant_id=tenant_id,
        app_name=app_name
    ).first()
    
    if record:
        # 合并数据: 传入数据覆盖旧数据
        existing_data = record.data or {}
        new_data = body.data or {}
        merged_data = {**existing_data, **new_data}
        
        record.data = merged_data
        if body.phone:
            record.phone = body.phone
        if body.user_unique_id:
            record.user_unique_id = body.user_unique_id
        if body.user_name:
            record.user_name = body.user_name
        await record.save()
    else:
        # 创建新记录
        record = await FillDataRecord.create(
            session_id=body.session_id,
            phone=body.phone or "",
            user_unique_id=body.user_unique_id or "",
            user_name=body.user_name or "",
            app_name=app_name,
            tenant_id=tenant_id,
            data=body.data or {}
        )
    
    return { "code": 200, "message": "success" }
```

#### 3.3.7 获取AI填单数据 (核心转发逻辑)
```python
@router.post("/autofill/get_ai_fill_data")
async def get_ai_fill_data(
    request: Request,
    body: AIFillDataRequest,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    三方应用调用: 接收请求 -> 存储数据 -> 转发Dify -> 返回响应
    """
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]
    
    # 1. 存储原始数据到数据库
    await _save_original_data(
        session_id=body.session_id,
        tenant_id=tenant_id,
        app_name=app_name,
        data=body.data
    )
    
    # 2. 转发请求到 Dify
    dify_url = auth_info["dify_url"]
    dify_api_key = auth_info["dify_api_key"]
    
    if not dify_url or not dify_api_key:
        raise HTTPException(status_code=500, detail="Dify configuration not found")
    
    # 构建转发请求
    headers = {
        "Authorization": f"Bearer {dify_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "session_id": body.session_id,
        "data": body.data
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{dify_url}/chat-messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Dify service timeout")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Dify service error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


async def _save_original_data(session_id: str, tenant_id: int, app_name: str, data: dict):
    """存储原始数据，包装为 {original_data: {...}}"""
    record = await FillDataRecord.filter(
        session_id=session_id,
        tenant_id=tenant_id,
        app_name=app_name
    ).first()
    
    wrapped_data = {"original_data": data}
    
    if record:
        existing = record.data or {}
        existing["original_data"] = data
        record.data = existing
        await record.save()
    else:
        await FillDataRecord.create(
            session_id=session_id,
            app_name=app_name,
            tenant_id=tenant_id,
            data=wrapped_data
        )
```

---

## 四、Schema 设计 (Pydantic)

```python
# 应用管理
class AppCreate(BaseModel):
    app_name: str = Field(..., max_length=128, pattern=r"^[a-zA-Z0-9_]+$")
    tenant_id: int
    description: Optional[str] = None
    dify_url: Optional[str] = None
    dify_api_key: Optional[str] = None

class AppUpdate(BaseModel):
    id: int
    app_name: Optional[str] = None
    description: Optional[str] = None
    dify_url: Optional[str] = None
    dify_api_key: Optional[str] = None
    is_active: Optional[bool] = None

# 总结模板
class SummaryTemplateCreate(BaseModel):
    name: str = Field(..., max_length=256)
    app_name: str = Field(..., max_length=128)
    tenant_id: int
    class_name: str = Field(..., max_length=128)
    summary: str = Field(default="", max_length=2000)
    template_content: Optional[str] = None

class SummaryTemplateListRequest(BaseModel):
    class_name: Optional[str] = None

class SummaryTemplateDetailRequest(BaseModel):
    id: int

# 下拉选项
class DropdownOptionCreate(BaseModel):
    domain: str = Field(default="", max_length=512)
    summary: str = Field(default="", max_length=2000)
    description: Optional[str] = None
    class_name: str = Field(..., max_length=128)
    tenant_id: int
    app_name: str = Field(..., max_length=128)
    parent_id: int = Field(default=0, description="父选项ID，0表示顶级选项")
    option_value: str = Field(..., max_length=512, description="选项值")

class DropdownOptionUpdate(BaseModel):
    id: int
    domain: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    class_name: Optional[str] = None
    parent_id: Optional[int] = None
    option_value: Optional[str] = None

class DropdownOptionListRequest(BaseModel):
    class_name: Optional[str] = None
    parent_id: Optional[int] = 0

class DropdownOptionDetailRequest(BaseModel):
    id: int

# 填单记录
class RecordFillDataRequest(BaseModel):
    session_id: str = Field(..., max_length=256)
    data: dict = Field(default_factory=dict)
    phone: Optional[str] = None
    user_unique_id: Optional[str] = None
    user_name: Optional[str] = None

class AIFillDataRequest(BaseModel):
    session_id: str = Field(..., max_length=256)
    data: dict = Field(default_factory=dict)
```

---

## 五、控制器层设计

```python
# app/controllers/app_management.py
from app.core.crud import CRUDBase
from app.models.autofill import AppManagement
from app.schemas.autofill import AppCreate, AppUpdate

class AppManagementController(CRUDBase[AppManagement, AppCreate, AppUpdate]):
    def __init__(self):
        super().__init__(model=AppManagement)
    
    async def create_with_key(self, obj_in: AppCreate) -> AppManagement:
        """创建应用并自动生成API Key"""
        import secrets
        api_key = f"af_{obj_in.tenant_id}_{secrets.token_urlsafe(32)}"
        
        obj_dict = obj_in.model_dump()
        obj_dict["api_key"] = api_key
        
        obj = self.model(**obj_dict)
        await obj.save()
        return obj

app_management_controller = AppManagementController()

# app/controllers/summary_template.py
class SummaryTemplateController(CRUDBase[SummaryTemplate, SummaryTemplateCreate, SummaryTemplateUpdate]):
    def __init__(self):
        super().__init__(model=SummaryTemplate)

summary_template_controller = SummaryTemplateController()

# app/controllers/dropdown_option.py
class DropdownOptionController(CRUDBase[DropdownOption, DropdownOptionCreate, DropdownOptionUpdate]):
    def __init__(self):
        super().__init__(model=DropdownOption)

dropdown_option_controller = DropdownOptionController()

# app/controllers/fill_data_record.py
class FillDataRecordController(CRUDBase[FillDataRecord, RecordFillDataCreate, RecordFillDataUpdate]):
    def __init__(self):
        super().__init__(model=FillDataRecord)
    
    async def get_by_session(self, session_id: str, tenant_id: int, app_name: str) -> Optional[FillDataRecord]:
        return await self.model.filter(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name
        ).first()

fill_data_record_controller = FillDataRecordController()
```

---

## 六、前端页面设计

### 6.1 路由配置
```typescript
// frontend/src/router/routes.ts 新增
{
    path: '/autofill',
    name: '智能填单',
    component: Layout,
    children: [
        {
            path: 'app',
            name: '应用管理',
            component: () => import('@/views/autofill/app/index.vue')
        },
        {
            path: 'template',
            name: '总结模板',
            component: () => import('@/views/autofill/template/index.vue')
        },
        {
            path: 'dropdown',
            name: '下拉选项',
            component: () => import('@/views/autofill/dropdown/index.vue')
        },
        {
            path: 'record',
            name: '填单记录',
            component: () => import('@/views/autofill/record/index.vue')
        }
    ]
}
```

### 6.2 API 封装
```typescript
// frontend/src/api/autofill.ts
import request from '@/utils/request'

export default {
    // 应用管理
    getAppList: (params: any = {}) => request.get('/autofill/app/list', { params }),
    createApp: (data: any = {}) => request.post('/autofill/app/create', data),
    updateApp: (data: any = {}) => request.post('/autofill/app/update', data),
    deleteApp: (params: any = {}) => request.delete('/autofill/app/delete', { params }),
    
    // 总结模板
    getTemplateList: (params: any = {}) => request.get('/autofill/template/list', { params }),
    createTemplate: (data: any = {}) => request.post('/autofill/template/create', data),
    updateTemplate: (data: any = {}) => request.post('/autofill/template/update', data),
    deleteTemplate: (params: any = {}) => request.delete('/autofill/template/delete', { params }),
    
    // 下拉选项
    getDropdownList: (params: any = {}) => request.get('/autofill/dropdown/list', { params }),
    createDropdown: (data: any = {}) => request.post('/autofill/dropdown/create', data),
    updateDropdown: (data: any = {}) => request.post('/autofill/dropdown/update', data),
    deleteDropdown: (params: any = {}) => request.delete('/autofill/dropdown/delete', { params }),
    
    // 填单记录
    getRecordList: (params: any = {}) => request.get('/autofill/record/list', { params }),
    getRecordById: (params: any = {}) => request.get('/autofill/record/get', { params }),
    updateRecord: (data: any = {}) => request.post('/autofill/record/update', data),
    deleteRecord: (params: any = {}) => request.delete('/autofill/record/delete', { params }),
}
```

### 6.3 页面设计 (CrudTable 组件)

#### 应用管理页面
```vue
<template>
    <CrudTable
        :api="api"
        :columns="columns"
        :filter-items="filterItems"
        :form-items="formItems"
    />
</template>

<script setup>
const columns = [
    { title: 'ID', dataIndex: 'id', width: 80 },
    { title: '应用名称', dataIndex: 'app_name' },
    { title: 'API Key', dataIndex: 'api_key', ellipsis: true },
    { title: '租户ID', dataIndex: 'tenant_id' },
    { title: 'Dify地址', dataIndex: 'dify_url', ellipsis: true },
    { title: '状态', dataIndex: 'is_active', slotName: 'status' },
    { title: '创建时间', dataIndex: 'created_at' },
]

const filterItems = [
    { field: 'app_name', label: '应用名称', type: 'input' },
    { field: 'tenant_id', label: '租户ID', type: 'number' },
]

const formItems = [
    { field: 'app_name', label: '应用名称', type: 'input', required: true },
    { field: 'tenant_id', label: '租户ID', type: 'number', required: true },
    { field: 'description', label: '描述', type: 'textarea' },
    { field: 'dify_url', label: 'Dify地址', type: 'input' },
    { field: 'dify_api_key', label: 'Dify密钥', type: 'input' },
]
</script>
```

#### 填单记录页面 (JSON编辑器)
```vue
<template>
    <CrudTable
        :api="api"
        :columns="columns"
        :filter-items="filterItems"
    >
        <template #data="{ record }">
            <a-button type="link" @click="showJsonEditor(record)">
                查看/编辑数据
            </a-button>
        </template>
    </CrudTable>
    
    <!-- JSON编辑器弹窗 -->
    <a-modal v-model:visible="editorVisible" title="编辑填单数据" width="800px">
        <JsonEditor v-model="currentData" />
        <template #footer>
            <a-button @click="editorVisible = false">取消</a-button>
            <a-button type="primary" @click="saveData">保存</a-button>
        </template>
    </a-modal>
</template>
```

---

## 七、中间件与认证流程

### 7.1 请求链路

```
三方应用/Dify请求
    │
    ▼
Nginx (SSL/限流)
    │
    ▼
FastAPI Middleware
    ├── CORS Middleware
    ├── RequestId Middleware
    ├── RequestLogging Middleware
    └── HttpAuditLog Middleware (排除 /autofill/*)
    │
    ▼
路由分发
    ├── /api/v1/* → JWT认证 + 权限校验
    │   └── AuthControl.is_authed(token)
    │   └── PermissionControl.has_permission()
    │
    └── /autofill/* → Bearer认证
        └── APIKeyAuth.authenticate(Authorization)
            ├── 解析 Bearer api_key
            ├── Redis查询缓存
            ├── DB查询 AppManagement
            └── 注入 tenant_id/app_name/domain
```

### 7.2 API Key 缓存策略
```python
# 缓存结构
redis_key = f"api_key:{api_key}"
redis_value = {
    "tenant_id": 1,
    "app_name": "insurance_claim",
    "domain": "claim.example.com",
    "dify_url": "https://dify.example.com/v1",
    "dify_api_key": "app-xxxx"
}
expire = 3600  # 1小时

# 缓存失效场景
# 1. 应用信息更新时主动删除缓存
# 2. 缓存过期自动失效
# 3. 应用禁用(is_active=False)时删除缓存
```

---

## 八、异常处理设计

### 8.1 异常码定义

| 状态码 | 场景 | 处理 |
|--------|------|------|
| 200 | 成功 | 正常返回 |
| 400 | 参数校验失败 | 返回详细错误信息 |
| 401 | API Key无效/过期 | 返回认证失败 |
| 403 | 无权限 | 返回权限不足 |
| 404 | 资源不存在 | 返回未找到 |
| 429 | 请求过于频繁 | 返回限流提示 |
| 500 | 内部错误 | 记录日志，返回服务异常 |
| 502 | Dify服务错误 | 返回上游服务异常 |
| 504 | Dify超时 | 返回服务超时 |

### 8.2 异常处理器
```python
# 新增异常处理
async def APIKeyAuthHandle(_: Request, exc: APIKeyAuthError) -> JSONResponse:
    return JSONResponse(
        content={"code": 401, "msg": f"API Key认证失败: {exc.message}"},
        status_code=401
    )

async def DifyServiceHandle(_: Request, exc: DifyServiceError) -> JSONResponse:
    return JSONResponse(
        content={"code": 502, "msg": f"Dify服务异常: {exc.message}"},
        status_code=502
    )
```

---

## 九、日志设计

### 9.1 日志格式
```json
{
    "timestamp": "2024-01-01T10:00:00+08:00",
    "level": "INFO",
    "request_id": "uuid-xxx",
    "module": "autofill",
    "path": "/autofill/get_ai_fill_data",
    "method": "POST",
    "api_key": "af_1_xxx",
    "tenant_id": 1,
    "app_name": "insurance_claim",
    "session_id": "sess_xxx",
    "duration_ms": 1500,
    "status_code": 200,
    "message": "AI填单请求处理完成"
}
```

### 9.2 关键日志点
- API Key 认证成功/失败
- Dify 请求转发 (请求体、响应状态、耗时)
- 数据合并操作 (旧数据、新数据、合并结果)
- 数据库操作异常

---

## 十、Redis 全局组件设计

### 10.1 配置说明

在 `config.toml` 中配置 Redis：

```toml
[redis]
# Redis配置 - 全局缓存组件
host = "127.0.0.1"
port = 6379
password = "redis123456"
db = 3
key_prefix = "auto_fill"
```

### 10.2 全局 Redis 客户端

使用 `redis-py` 组件：

```python
# app/core/redis.py
import redis.asyncio as redis
from app.core.config import settings

class RedisClient:
    """全局Redis客户端 - 单例模式 (redis-py组件)"""
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def init(self):
        """初始化Redis连接"""
        if self._client is None:
            self._client = redis.Redis(
                host=settings.redis.host,
                port=settings.redis.port,
                password=settings.redis.password if settings.redis.password else None,
                db=settings.redis.db,
                encoding="utf-8",
                decode_responses=True
            )
        return self._client
    
    @property
    def client(self):
        """获取Redis客户端实例"""
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call init() first.")
        return self._client
    
    def key(self, name: str) -> str:
        """生成带前缀的key"""
        return f"{settings.redis.key_prefix}:{name}"
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._client = None

# 全局实例
redis_client = RedisClient()

# 便捷函数
async def get_redis():
    """获取Redis客户端 (用于依赖注入)"""
    return redis_client.client
```

### 10.3 使用示例

```python
# 在应用启动时初始化
@app.on_event("startup")
async def startup_event():
    await redis_client.init()

# 在应用关闭时释放
@app.on_event("shutdown")
async def shutdown_event():
    await redis_client.close()

# 在API中使用
from app.core.redis import redis_client, get_redis
import redis.asyncio as redis

@router.post("/autofill/get_ai_fill_data")
async def get_ai_fill_data(
    body: AIFillDataRequest,
    redis: redis.Redis = Depends(get_redis)
):
    # 使用依赖注入获取redis
    cache_key = redis_client.key(f"api_key:{api_key}")
    cached = await redis.get(cache_key)
    
# 或者直接使用全局实例
async def some_function():
    await redis_client.client.set(
        redis_client.key("mykey"), 
        "value",
        ex=3600
    )
```

### 10.4 应用场景

| 场景 | Key 设计 | TTL |
|------|----------|-----|
| API Key 认证缓存 | `auto_fill:api_key:{hashed_key}` | 3600s |
| 会话数据缓存 | `auto_fill:session:{session_id}` | 86400s |
| 限流计数 | `auto_fill:rate_limit:{ip}` | 60s |
| 模板缓存 | `auto_fill:template:{tenant_id}:{app_name}:{id}` | 1800s |
| 下拉选项缓存 | `auto_fill:dropdown:{tenant_id}:{app_name}:{class_name}` | 1800s |

---

## 十一、文件新增清单

### 后端文件
```
app/models/autofill.py              # 新增4个数据模型
app/schemas/autofill.py             # 新增Pydantic模型
app/controllers/app_management.py   # 应用管理控制器
app/controllers/summary_template.py # 模板控制器
app/controllers/dropdown_option.py  # 下拉选项控制器
app/controllers/fill_data_record.py # 填单记录控制器
app/api/v1/autofill/              # 管理后台API路由
    ├── __init__.py
    ├── app.py
    ├── template.py
    ├── dropdown.py
    └── record.py
app/api/autofill.py               # Dify/三方调用路由 (独立router)
app/core/api_key_auth.py          # API Key认证模块
app/services/dify_proxy.py        # Dify代理转发服务
```

### 前端文件
```
frontend/src/api/autofill.ts      # API封装
frontend/src/views/autofill/      # 页面目录
    ├── app/
    │   └── index.vue
    ├── template/
    │   └── index.vue
    ├── dropdown/
    │   └── index.vue
    └── record/
        └── index.vue
frontend/src/components/JsonEditor/  # JSON编辑器组件
    └── index.vue
```

---

## 十二、数据流时序图

### 12.1 三方应用调用AI填单
```
三方应用          AutoFill                数据库              Redis              Dify
   │                │                       │                   │                │
   │─1.请求───────>│                       │                   │                │
   │  /get_ai_fill_data                   │                   │                │
   │  Bearer api_key                      │                   │                │
   │                │                       │                   │                │
   │                │─2.认证───────────────>│                   │                │
   │                │  查询api_key映射      │                   │                │
   │                │<─3.返回tenant信息────│                   │                │
   │                │                       │                   │                │
   │                │─4.存储数据───────────>│                   │                │
   │                │  original_data包装    │                   │                │
   │                │<─5.确认──────────────│                   │                │
   │                │                       │                   │                │
   │                │─6.转发请求─────────────────────────────────────────────────>│
   │                │  原请求体+Dify Key    │                   │                │
   │                │                       │                   │                │
   │                │<─7.返回AI结果────────────────────────────────────────────────│
   │                │                       │                   │                │
   │<─8.返回────────│                       │                   │                │
   │                │                       │                   │                │
```

### 12.2 Dify查询模板列表
```
Dify              AutoFill                数据库
 │                  │                       │
 │─1.请求─────────>│                       │
 │  /summary_template/list                 │
 │  Bearer api_key  │                       │
 │                  │                       │
 │                  │─2.认证────────────────>│
 │                  │  Redis/DB查询api_key   │
 │                  │<─3.返回映射信息────────│
 │                  │                       │
 │                  │─4.查询模板────────────>│
 │                  │  tenant_id+app_name    │
 │                  │<─5.返回模板列表────────│
 │                  │                       │
 │<─6.返回列表──────│                       │
 │                  │                       │
```

