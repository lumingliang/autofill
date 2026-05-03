# 智能填单系统 - 实施文档

## 1. 项目概述

本文档详细描述了智能填单系统的实施步骤，包括数据库迁移、后端开发、前端开发和测试部署。

---

## 2. 实施计划

### 2.1 任务分解

| 阶段 | 任务 | 预计工时 | 依赖 |
|------|------|----------|------|
| 阶段1 | 数据库模型设计与迁移 | 4h | - |
| 阶段2 | 后端API开发 | 16h | 阶段1 |
| 阶段3 | 前端页面开发 | 16h | 阶段2 |
| 阶段4 | 接口联调与测试 | 8h | 阶段3 |
| 阶段5 | 文档编写与部署 | 4h | 阶段4 |

### 2.2 实施顺序

```
数据库模型 → 后端API → 前端页面 → 接口联调 → 测试 → 部署
    │            │          │          │         │       │
    ▼            ▼          ▼          ▼         ▼       ▼
 FillPage   页面管理    页面管理      端到端    单元测试  生产环境
 FieldGroup 字段组管理  字段组管理     测试      集成测试
 FieldSpec  字段管理    字段管理
```

---

## 3. 数据库实施

### 3.1 创建迁移文件

```bash
# 进入项目目录
cd /Users/lu/code/code/py/autofill

# 使用aerich创建迁移
aerich migrate --name add_fill_page_and_field_models
```

### 3.2 模型代码实现

#### 3.2.1 修改 `app/models/autofill.py`

> **关联关系设计规范**：本项目所有模型关联关系均通过 `BigIntField` 存储关联ID实现，**禁止使用数据库外键约束**。原因如下：
> 1. **性能考虑**：外键约束会增加数据库写入时的检查开销，影响高并发场景性能
> 2. **灵活性**：无外键约束便于数据迁移和分库分表
> 3. **软删除支持**：应用层控制关联关系，更容易实现软删除逻辑
> 4. **租户隔离**：通过应用层查询条件（`tenant_id`）实现数据隔离

```python
import secrets
import string
from enum import Enum

from tortoise import fields

from .base import BaseModel, TimestampMixin


# ✅ 已实现: app/models/autofill.py
def generate_api_key():
    """生成 API Key: af_{32位随机字符串}"""
    random_str = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    return f"af_{random_str}"


def generate_field_group_code():
    """生成字段组唯一标识: fg_{16位随机字符串}"""
    random_str = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(16))
    return f"fg_{random_str}"


# ==================== 现有模型（保持不变）====================
# ✅ 以下模型已实现: app/models/autofill.py

class AppManagement(BaseModel, TimestampMixin):
    """应用管理表 ✅ 已实现"""
    app_name = fields.CharField(max_length=64, default="", description="应用名称(英文)", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    api_key = fields.CharField(max_length=64, default=generate_api_key, description="API密钥", unique=True)
    dify_url = fields.CharField(max_length=255, default="", description="Dify服务地址")
    dify_api_key = fields.CharField(max_length=128, default="", description="Dify API密钥")
    description = fields.CharField(max_length=255, null=True, description="应用描述")
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)

    class Meta:
        table = "app_management"


class SummaryTemplate(BaseModel, TimestampMixin):
    """总结类填单模板表 ✅ 已实现"""
    name = fields.CharField(max_length=128, default="", description="模板名称", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    class_name = fields.CharField(max_length=64, default="", description="模板分类", index=True)
    summary = fields.CharField(max_length=500, default="", description="模板摘要")
    template_content = fields.TextField(null=True, description="模板内容")

    class Meta:
        table = "summary_template"


class DropdownOption(BaseModel, TimestampMixin):
    """下拉选项类填单模板表 ✅ 已实现"""
    summary = fields.CharField(max_length=500, default="", description="字段摘要")
    description = fields.TextField(null=True, description="详细说明")
    class_name = fields.CharField(max_length=64, default="", description="模板分类", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    parent_id = fields.BigIntField(default=0, description="父选项ID，0表示顶级选项", index=True)
    option_value = fields.CharField(max_length=128, default="", description="选项值", index=True)

    class Meta:
        table = "dropdown_option"


class FillDataRecord(BaseModel, TimestampMixin):
    """填单数据记录表 ✅ 已实现"""
    session_id = fields.CharField(max_length=64, default="", description="会话ID", index=True)
    phone = fields.CharField(max_length=32, default="", description="手机号", index=True)
    user_unique_id = fields.CharField(max_length=64, default="", description="用户唯一标识", index=True)
    user_name = fields.CharField(max_length=64, default="", description="用户名称", index=True)
    app_name = fields.CharField(max_length=64, default="", description="应用名称", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    data = fields.JSONField(null=True, description="填单数据")
    status = fields.CharField(max_length=32, default="pending", description="处理状态", index=True)
    result = fields.JSONField(null=True, description="AI填单结果数据")
    error_msg = fields.TextField(null=True, description="错误信息")
    processed_at = fields.DatetimeField(null=True, description="处理完成时间")

    class Meta:
        table = "fill_data_record"


# ==================== 新增模型 ====================

class FieldType(str, Enum):
    """字段类型枚举 - 仅支持select和text两种类型"""
    SELECT = "select"
    TEXT = "text"


class FillPage(BaseModel, TimestampMixin):
    """填单页面管理表"""
    page_name = fields.CharField(max_length=64, description="页面名称", index=True)
    page_code = fields.CharField(max_length=64, description="页面编码", index=True)
    app_id = fields.BigIntField(description="关联应用ID", index=True)
    app_name = fields.CharField(max_length=64, description="应用名称", index=True)
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    description = fields.TextField(null=True, description="页面描述")
    is_active = fields.BooleanField(default=True, description="是否启用")

    class Meta:
        table = "fill_page"


class FieldGroupConfig(BaseModel, TimestampMixin):
    """字段组配置表"""
    code = fields.CharField(max_length=64, description="全局唯一标识", unique=True, index=True, default=generate_field_group_code)
    app_name = fields.CharField(max_length=64, description="应用名称", index=True)
    page_id = fields.BigIntField(description="关联页面ID", index=True)
    page_name = fields.CharField(max_length=64, description="页面名称")
    field_group_name = fields.CharField(max_length=64, description="字段组名称")
    prompt_template_base = fields.TextField(description="Prompt基础模板，包含{{fields_instructions}}和{{query}}占位符")
    output_templates = fields.JSONField(default=dict, description="多输出模板配置，如{key: {template, description}}")
    description = fields.TextField(null=True, description="字段组描述")
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    is_active = fields.BooleanField(default=True, description="是否启用")
    version = fields.IntField(default=1, description="版本号，用于缓存控制")

    class Meta:
        table = "field_group_config"


class FieldSpec(BaseModel, TimestampMixin):
    """字段明细表 - 核心表"""
    field_group_id = fields.BigIntField(description="关联字段组ID", index=True)
    field_name = fields.CharField(max_length=64, description="字段英文名（用于JSON输出）")
    field_label = fields.CharField(max_length=128, description="字段显示名称")
    field_type = fields.CharEnumField(FieldType, default=FieldType.TEXT, description="字段类型")
    tenant_id = fields.BigIntField(default=0, description="租户ID", index=True)
    fill_instruction = fields.TextField(null=True, description="字段填写指引（用于生成LLM描述）")
    options = fields.JSONField(null=True, description="select类型选项配置，含source/api_identifier/items/last_sync_at")
    corrections = fields.JSONField(default=list, description="text类型全局批注列表[{id, text, created_by, created_at}]")
    is_active = fields.BooleanField(default=True, description="是否启用")

    class Meta:
        table = "field_spec"
```

### 3.3 执行迁移

```bash
# 执行迁移
aerich upgrade

# 验证迁移结果
# 检查数据库表是否创建成功
```

---

## 4. 后端实施

### 4.1 Schema定义

#### 4.1.1 创建 `app/schemas/fill_page.py`

```python
from typing import Optional

from pydantic import BaseModel, Field


# ==================== 填单页面 Schemas ====================

class FillPageCreate(BaseModel):
    page_name: str = Field(..., max_length=64)
    page_code: str = Field(..., max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    app_id: int
    app_name: str = Field(..., max_length=64)
    tenant_id: int
    description: Optional[str] = None
    is_active: Optional[bool] = True


class FillPageUpdate(BaseModel):
    id: int
    page_name: Optional[str] = Field(None, max_length=64)
    page_code: Optional[str] = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    app_id: Optional[int] = None
    app_name: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FillPageOut(BaseModel):
    id: int
    page_name: str
    page_code: str
    app_id: int
    app_name: str
    tenant_id: int
    description: Optional[str]
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ==================== 字段组配置 Schemas ====================

class OutputTemplateItem(BaseModel):
    """输出模板项"""
    template: str
    description: str


class FieldGroupConfigCreate(BaseModel):
    app_name: str = Field(..., max_length=64)
    page_id: int
    page_name: str = Field(..., max_length=64)
    field_group_name: str = Field(..., max_length=64)
    prompt_template_base: Optional[str] = None
    output_templates: Optional[dict[str, OutputTemplateItem]] = None
    description: Optional[str] = None
    tenant_id: int
    is_active: Optional[bool] = True


class FieldGroupConfigUpdate(BaseModel):
    id: int
    app_name: Optional[str] = Field(None, max_length=64)
    page_id: Optional[int] = None
    page_name: Optional[str] = Field(None, max_length=64)
    field_group_name: Optional[str] = Field(None, max_length=64)
    prompt_template_base: Optional[str] = None
    output_templates: Optional[dict[str, OutputTemplateItem]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FieldGroupConfigOut(BaseModel):
    id: int
    code: str
    app_name: str
    page_id: int
    page_name: str
    field_group_name: str
    prompt_template_base: str
    output_templates: dict
    description: Optional[str]
    tenant_id: int
    is_active: bool
    version: int
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ==================== 字段明细 Schemas ====================

class OptionItem(BaseModel):
    """选项项"""
    value: str
    label: str
    base_annotation: Optional[str] = ""
    corrections: Optional[list[dict]] = []
    is_deleted: Optional[bool] = False


class FieldOptions(BaseModel):
    """字段选项配置（select类型）"""
    source: str = Field(default="static", description="选项来源：static/api")
    api_identifier: Optional[str] = None
    last_sync_at: Optional[str] = None
    items: list[OptionItem] = []


class FieldSpecCreate(BaseModel):
    field_group_id: int
    field_name: str = Field(..., max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    field_label: str = Field(..., max_length=128)
    field_type: str = Field(default="text")
    fill_instruction: Optional[str] = None
    options: Optional[FieldOptions] = None
    corrections: Optional[list[dict]] = None
    is_active: Optional[bool] = True


class FieldSpecUpdate(BaseModel):
    id: int
    field_group_id: Optional[int] = None
    field_name: Optional[str] = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    field_label: Optional[str] = Field(None, max_length=128)
    field_type: Optional[str] = None
    fill_instruction: Optional[str] = None
    options: Optional[FieldOptions] = None
    corrections: Optional[list[dict]] = None
    is_active: Optional[bool] = None


class FieldSpecOut(BaseModel):
    id: int
    field_group_id: int
    field_name: str
    field_label: str
    field_type: str
    fill_instruction: Optional[str]
    options: Optional[FieldOptions]
    corrections: Optional[list[dict]]
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ==================== 公开接口请求 Schemas ====================

class FieldGroupQueryRequest(BaseModel):
    app_name: Optional[str] = None
    page_name: Optional[str] = None
    field_group_name: Optional[str] = None
    code: Optional[str] = None


class FieldSpecListRequest(BaseModel):
    field_group_id: int
```

### 4.2 控制器实现

#### 4.2.1 修改 `app/controllers/autofill.py`

```python
from app.core.crud import CRUDBase
from app.models.autofill import (
    AppManagement,
    DropdownOption,
    FieldGroupConfig,
    FieldSpec,
    FillDataRecord,
    FillPage,
    SummaryTemplate,
)
from app.schemas.autofill import *
from app.schemas.fill_page import *


# ✅ 以下控制器已实现: app/controllers/autofill.py

class AppManagementController(CRUDBase[AppManagement, AppCreate, AppUpdate]):
    """应用管理控制器 ✅ 已实现"""
    def __init__(self):
        super().__init__(model=AppManagement)

    async def create_app(self, obj_in: AppCreate) -> AppManagement:
        """创建应用，自动生成API Key"""
        return await self.create(obj_in=obj_in)

    async def update_app(self, id: int, obj_in: AppUpdate) -> AppManagement:
        """更新应用"""
        return await self.update(id=id, obj_in=obj_in)


class SummaryTemplateController(CRUDBase[SummaryTemplate, SummaryTemplateCreate, SummaryTemplateUpdate]):
    """总结模板控制器 ✅ 已实现"""
    def __init__(self):
        super().__init__(model=SummaryTemplate)


class DropdownOptionController(CRUDBase[DropdownOption, DropdownOptionCreate, DropdownOptionUpdate]):
    """下拉选项控制器 ✅ 已实现"""
    def __init__(self):
        super().__init__(model=DropdownOption)


class FillDataRecordController(CRUDBase[FillDataRecord, FillDataRecordCreate, FillDataRecordUpdate]):
    """填单记录控制器 ✅ 已实现"""
    def __init__(self):
        super().__init__(model=FillDataRecord)


# ==================== 新增控制器 ====================

class FillPageController(CRUDBase[FillPage, FillPageCreate, FillPageUpdate]):
    """填单页面控制器"""
    def __init__(self):
        super().__init__(model=FillPage)


class FieldGroupConfigController(CRUDBase[FieldGroupConfig, FieldGroupConfigCreate, FieldGroupConfigUpdate]):
    """字段组配置控制器"""
    def __init__(self):
        super().__init__(model=FieldGroupConfig)


class FieldSpecController(CRUDBase[FieldSpec, FieldSpecCreate, FieldSpecUpdate]):
    """字段明细控制器"""
    def __init__(self):
        super().__init__(model=FieldSpec)


# 实例化控制器
app_management_controller = AppManagementController()
summary_template_controller = SummaryTemplateController()
dropdown_option_controller = DropdownOptionController()
fill_data_record_controller = FillDataRecordController()
fill_page_controller = FillPageController()
field_group_config_controller = FieldGroupConfigController()
field_spec_controller = FieldSpecController()
```

### 4.3 Prompt组装服务

#### 4.3.1 创建 `app/services/prompt_service.py`

```python
"""
Prompt模板组装服务 - 支持Function Calling和纯文本双模式
"""
from typing import List, Dict, Any, Optional, Tuple
from string import Template

from app.models.autofill import FieldGroupConfig, FieldSpec


def build_fields_instructions(fields: List[FieldSpec]) -> str:
    """
    组装字段指令（用于纯文本Prompt和Function Calling描述）
    
    Args:
        fields: 字段明细列表
        
    Returns:
        组装后的字段指令字符串
    """
    lines = []
    for field in fields:
        if field.field_type == 'text':
            desc = field.fill_instruction or "根据对话内容提取"
            if field.corrections:
                corrections_text = "；".join([c['text'] for c in field.corrections])
                desc += f"。人工补充规则：{corrections_text}"
            lines.append(f"- {field.field_label}（字段名：`{field.field_name}`）：{desc}")
        
        elif field.field_type == 'select':
            items = [opt for opt in field.options.get('items', []) if not opt.get('is_deleted', False)]
            option_strs = []
            for opt in items:
                label = opt['label']
                base = opt.get('base_annotation', '')
                corrections_list = opt.get('corrections', [])
                corrections_text = "；".join([c['text'] for c in corrections_list])
                full_desc = f"{label}：{base}"
                if corrections_text:
                    full_desc += f"；人工补充：{corrections_text}"
                option_strs.append(f"  - {full_desc}")
            
            options_block = "可选值：\n" + "\n".join(option_strs)
            global_inst = field.fill_instruction or "根据用户意图选择"
            lines.append(f"- {field.field_label}（字段名：`{field.field_name}`）：{global_inst}\n{options_block}\n  只能从上述选项中选择一个值。")
        
    return "\n".join(lines)


def build_function_schema(field_group: FieldGroupConfig, fields: List[FieldSpec]) -> Dict[str, Any]:
    """
    动态生成 Function Calling Schema
    
    Args:
        field_group: 字段组配置
        fields: 字段明细列表
        
    Returns:
        OpenAI Function Calling Schema
    """
    properties = {}
    
    for field in fields:
        if field.field_type == 'text':
            desc = field.fill_instruction or ""
            if field.corrections:
                corrections_text = "；".join([c['text'] for c in field.corrections])
                desc += f"；人工补充规则：{corrections_text}"
            properties[field.field_name] = {
                "type": "string",
                "description": desc
            }
        
        elif field.field_type == 'select':
            items = [opt for opt in field.options.get('items', []) if not opt.get('is_deleted', False)]
            enum_values = [opt['label'] for opt in items]
            option_descs = []
            for opt in items:
                label = opt['label']
                base = opt.get('base_annotation', '')
                corrections_list = opt.get('corrections', [])
                corrections_text = "；".join([c['text'] for c in corrections_list])
                full = f"{label}：{base}"
                if corrections_text:
                    full += f"；人工补充：{corrections_text}"
                option_descs.append(full)
            
            description = f"可选值：{'；'.join(option_descs)}"
            if field.fill_instruction:
                description = field.fill_instruction + " " + description
            
            properties[field.field_name] = {
                "type": "string",
                "description": description,
                "enum": enum_values
            }
        
    return {
        "name": f"fill_{field_group.code}",
        "description": f"填写 {field_group.field_group_name}",
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": list(properties.keys())
        }
    }


def build_text_prompt(field_group: FieldGroupConfig, fields: List[FieldSpec], query: str) -> str:
    """
    构建纯文本Prompt（Function Calling降级方案）

    Args:
        field_group: 字段组配置
        fields: 字段明细列表
        query: 对话内容

    Returns:
        完整的Prompt文本
    """
    fields_instructions = build_fields_instructions(fields)

    # 使用字段组的prompt_template_base作为基础模板
    template_str = field_group.prompt_template_base or """你是一个智能填单助手。请根据以下对话内容，填写表单中的各个字段。

## 字段填写说明
{{fields_instructions}}

## 对话内容
{{query}}

## 输出要求
- 你必须输出一个**合法的 JSON 对象**，不要包含任何其他解释或前缀。
- JSON 对象的 key 必须与上述字段名称完全一致。
- 对于「选择」类型的字段，必须从给出的选项中选择一个值。
- 如果某个字段无法从对话中确定，请填写空字符串（""）。

请直接输出 JSON："""

    template = Template(template_str)
    return template.safe_substitute(
        fields_instructions=fields_instructions,
        query=query
    )


def render_output_templates(field_group: FieldGroupConfig, field_values: Dict[str, Any], 
                            template_keys: Optional[List[str]] = None) -> Dict[str, str]:
    """
    渲染输出模板
    
    Args:
        field_group: 字段组配置
        field_values: LLM返回的字段值
        template_keys: 指定要渲染的模板key列表，None则渲染所有
        
    Returns:
        {template_key: rendered_text}
    """
    output_templates = field_group.output_templates or {}
    result = {}
    
    keys_to_render = template_keys if template_keys else output_templates.keys()
    
    for key in keys_to_render:
        if key in output_templates:
            template_str = output_templates[key].get('template', '')
            try:
                rendered = Template(template_str).safe_substitute(**field_values)
                result[key] = rendered
            except Exception as e:
                result[key] = f"[渲染错误: {str(e)}]"
    
    return result


def validate_and_fix_output(result: Dict[str, Any], fields: List[FieldSpec]) -> Dict[str, Any]:
    """
    验证并修正LLM输出
    
    Args:
        result: LLM返回的字段值
        fields: 字段明细列表
        
    Returns:
        修正后的字段值
    """
    for field in fields:
        value = result.get(field.field_name)
        
        if value is None:
            result[field.field_name] = ""
            continue
        
        if field.field_type == 'select':
            allowed_labels = [opt['label'] for opt in field.options.get('items', []) 
                            if not opt.get('is_deleted', False)]
            if value not in allowed_labels:
                # 尝试模糊匹配
                matched = next((label for label in allowed_labels 
                              if value in label or label in value), None)
                result[field.field_name] = matched if matched else ""
        
        elif field.field_type in ['text', 'textarea']:
            result[field.field_name] = str(value).strip()
        
        elif field.field_type == 'number':
            try:
                result[field.field_name] = float(value) if value else 0
            except (ValueError, TypeError):
                result[field.field_name] = 0
    
    return result


async def update_field_group_prompt(field_group_id: int) -> None:
    """
    更新字段组的版本号（触发缓存失效）
    
    当字段明细发生变更时，自动触发更新
    
    Args:
        field_group_id: 字段组ID
    """
    field_group = await FieldGroupConfig.get(id=field_group_id)
    # 版本号+1，使缓存失效
    field_group.version = field_group.version + 1
    await field_group.save()
```

### 4.4 API路由实现

#### 4.4.1 创建 `app/api/v1/autofill/page.py`

```python
"""
填单页面管理接口
"""
from typing import List

from fastapi import APIRouter, Header, Query
from tortoise.expressions import Q

from app.controllers.autofill import (
    app_management_controller,
    field_group_config_controller,
    fill_page_controller,
)
from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.fill_page import *
from app.services.autofill.prompt_service import update_field_group_prompt

page_router = APIRouter()


def is_superuser(user: User) -> bool:
    """检查是否为超级管理员"""
    return user.is_superuser


# ==================== 填单页面管理接口 ====================

@page_router.get("/page/list", summary="页面列表")
async def list_page(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    page_name: str = Query("", description="页面名称"),
    app_name: str = Query("", description="应用名称"),
    tenant_id: int = Query(None, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if page_name:
        q &= Q(page_name__contains=page_name)
    if app_name:
        q &= Q(app_name__contains=app_name)

    # 多租户筛选
    if tenant_id is not None and is_superuser(current_user):
        q &= Q(tenant_id=tenant_id)
    elif not is_superuser(current_user):
        if current_user.current_tenant_id:
            q &= Q(tenant_id=current_user.current_tenant_id)

    total, pages = await fill_page_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in pages]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@page_router.get("/page/get", summary="页面详情")
async def get_page(
    id: int = Query(..., description="页面ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    page = await fill_page_controller.get(id=id)
    return Success(data=await page.to_dict())


@page_router.post("/page/create", summary="创建页面")
async def create_page(
    page_in: FillPageCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 确定租户ID
    target_tenant_id = None
    if is_superuser(current_user):
        target_tenant_id = page_in.tenant_id
    else:
        target_tenant_id = current_user.current_tenant_id
        if not target_tenant_id:
            return Fail(code=400, msg="您当前未选择租户，无法创建页面")

    page_in.tenant_id = target_tenant_id
    page = await fill_page_controller.create(obj_in=page_in)
    return Success(data=await page.to_dict())


@page_router.post("/page/update", summary="更新页面")
async def update_page(
    page_in: FillPageUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    page = await fill_page_controller.get(id=page_in.id)

    # 权限检查
    if not is_superuser(current_user):
        if page.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的页面")

    updated = await fill_page_controller.update(id=page_in.id, obj_in=page_in)
    return Success(data=await updated.to_dict())


@page_router.delete("/page/delete", summary="删除页面")
async def delete_page(
    id: int = Query(..., description="页面ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    page = await fill_page_controller.get(id=id)

    # 权限检查
    if not is_superuser(current_user):
        if page.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的页面")

    await fill_page_controller.remove(id=id)
    return Success(msg="删除成功")


@page_router.get("/page/select", summary="页面下拉列表")
async def get_page_select(
    app_name: str = Query(None, description="应用名称"),
    tenant_id: int = Query(None, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """获取页面下拉列表，供其他模块使用"""
    current_user = await AuthControl.is_authed(token)

    q = Q(is_active=True)

    # 多租户筛选
    if tenant_id is not None and is_superuser(current_user):
        q &= Q(tenant_id=tenant_id)
    elif not is_superuser(current_user):
        if current_user.current_tenant_id:
            q &= Q(tenant_id=current_user.current_tenant_id)

    if app_name:
        q &= Q(app_name=app_name)

    pages = await fill_page_controller.model.filter(q).all()
    data = [{"label": f"{p.page_name} ({p.page_code})", "value": p.id, "app_name": p.app_name} for p in pages]
    return Success(data=data)


@page_router.get("/page/manual", summary="生成说明书")
async def generate_manual(
    page_id: int = Query(..., description="页面ID"),
    token: str = Header(..., description="token验证"),
):
    """
    生成Markdown格式的填单说明书
    
    查询当前页面下的所有字段组及其字段明细，生成说明书
    """
    await AuthControl.is_authed(token)
    
    # 获取页面信息
    page = await fill_page_controller.get(id=page_id)
    
    # 获取页面下的所有字段组
    field_groups = await field_group_config_controller.model.filter(
        page_id=page_id,
        is_active=True
    ).all()
    
    # 生成说明书内容
    manual_lines = [f"# {page.page_name}填单说明书\n"]
    
    for idx, group in enumerate(field_groups, 1):
        manual_lines.append(f"\n## {idx}、{group.field_group_name}\n")
        if group.description:
            manual_lines.append(f"> 组描述：{group.description}\n")
        
        # 获取字段组下的所有字段
        fields = await field_spec_controller.model.filter(
            field_group_id=group.id,
            is_active=True
        ).all()

        for f_idx, field in enumerate(fields, 1):
            manual_lines.append(f"\n### {f_idx}. {field.field_label} ({field.field_name})\n")
            manual_lines.append(f"- 类型：{field.field_type}\n")
            manual_lines.append(f"- 填写指引：{field.fill_instruction or '无'}\n")
            
            # select类型显示选项信息
            if field.field_type == 'select' and field.options:
                items = field.options.get('items', [])
                if items:
                    manual_lines.append(f"- 选项：\n")
                    for opt in items:
                        if not opt.get('is_deleted', False):
                            label = opt.get('label', '')
                            base = opt.get('base_annotation', '')
                            manual_lines.append(f"  - {label}：{base}\n")
            
            # 显示全局批注
            if field.corrections:
                manual_lines.append(f"- 📌 人工批注：\n")
                for corr in field.corrections:
                    manual_lines.append(f"  - {corr.get('text', '')}\n")
    
    manual_content = "".join(manual_lines)
    return Success(data=manual_content)
```

#### 4.4.2 创建 `app/api/v1/autofill/field_group.py`

```python
"""
字段组配置管理接口
"""
from fastapi import APIRouter, Header, Query
from tortoise.expressions import Q

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
    fill_page_controller,
)
from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.fill_page import *
from app.services.autofill.prompt_service import update_field_group_prompt

field_group_router = APIRouter()


def is_superuser(user: User) -> bool:
    """检查是否为超级管理员"""
    return user.is_superuser


# ==================== 字段组配置管理接口 ====================

@field_group_router.get("/field_group/list", summary="字段组列表")
async def list_field_group(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    field_group_name: str = Query("", description="字段组名称"),
    app_name: str = Query("", description="应用名称"),
    page_name: str = Query("", description="页面名称"),
    tenant_id: int = Query(None, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if field_group_name:
        q &= Q(field_group_name__contains=field_group_name)
    if app_name:
        q &= Q(app_name__contains=app_name)
    if page_name:
        q &= Q(page_name__contains=page_name)

    # 多租户筛选
    if tenant_id is not None and is_superuser(current_user):
        q &= Q(tenant_id=tenant_id)
    elif not is_superuser(current_user):
        if current_user.current_tenant_id:
            q &= Q(tenant_id=current_user.current_tenant_id)

    total, groups = await field_group_config_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in groups]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@field_group_router.get("/field_group/get", summary="字段组详情")
async def get_field_group(
    id: int = Query(..., description="字段组ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    group = await field_group_config_controller.get(id=id)
    return Success(data=await group.to_dict())


@field_group_router.post("/field_group/create", summary="创建字段组")
async def create_field_group(
    group_in: FieldGroupConfigCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 确定租户ID
    target_tenant_id = None
    if is_superuser(current_user):
        target_tenant_id = group_in.tenant_id
    else:
        target_tenant_id = current_user.current_tenant_id
        if not target_tenant_id:
            return Fail(code=400, msg="您当前未选择租户，无法创建字段组")

    group_in.tenant_id = target_tenant_id
    
    # 如果未提供Prompt基础模板，使用默认模板
    if not group_in.prompt_template_base:
        group_in.prompt_template_base = """你是一个智能填单助手。请根据以下对话内容，填写表单中的各个字段。

## 字段填写说明
{{fields_instructions}}

## 对话内容
{{query}}

## 输出要求
- 你必须输出一个**合法的 JSON 对象**，不要包含任何其他解释或前缀。
- JSON 对象的 key 必须与上述字段名称完全一致。
- 对于「选择」类型的字段，必须从给出的选项中选择一个值。
- 如果某个字段无法从对话中确定，请填写空字符串（""）。

请直接输出 JSON："""
    
    # 初始化output_templates为空字典
    if group_in.output_templates is None:
        group_in.output_templates = {}
    
    group = await field_group_config_controller.create(obj_in=group_in)
    return Success(data=await group.to_dict())


@field_group_router.post("/field_group/update", summary="更新字段组")
async def update_field_group(
    group_in: FieldGroupConfigUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    group = await field_group_config_controller.get(id=group_in.id)

    # 权限检查
    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的字段组")

    updated = await field_group_config_controller.update(id=group_in.id, obj_in=group_in)
    return Success(data=await updated.to_dict())


@field_group_router.delete("/field_group/delete", summary="删除字段组")
async def delete_field_group(
    id: int = Query(..., description="字段组ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    group = await field_group_config_controller.get(id=id)

    # 权限检查
    if not is_superuser(current_user):
        if group.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的字段组")

    await field_group_config_controller.remove(id=id)
    return Success(msg="删除成功")


@field_group_router.get("/field_group/select", summary="字段组下拉列表")
async def get_field_group_select(
    app_name: str = Query(None, description="应用名称"),
    page_id: int = Query(None, description="页面ID"),
    tenant_id: int = Query(None, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """获取字段组下拉列表，供其他模块使用"""
    current_user = await AuthControl.is_authed(token)

    q = Q(is_active=True)

    # 多租户筛选
    if tenant_id is not None and is_superuser(current_user):
        q &= Q(tenant_id=tenant_id)
    elif not is_superuser(current_user):
        if current_user.current_tenant_id:
            q &= Q(tenant_id=current_user.current_tenant_id)

    if app_name:
        q &= Q(app_name=app_name)
    if page_id:
        q &= Q(page_id=page_id)

    groups = await field_group_config_controller.model.filter(q).all()
    data = [{"label": group.field_group_name, "value": group.id, "code": group.code} for group in groups]
    return Success(data=data)
```

#### 4.4.3 创建 `app/api/v1/autofill/field_spec.py`

```python
"""
字段明细管理接口
"""
from fastapi import APIRouter, Header, Query
from tortoise.expressions import Q

from app.controllers.autofill import field_group_config_controller, field_spec_controller
from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.fill_page import *
from app.services.autofill.prompt_service import update_field_group_prompt

field_spec_router = APIRouter()


def is_superuser(user: User) -> bool:
    """检查是否为超级管理员"""
    return user.is_superuser


# ==================== 字段明细管理接口 ====================

@field_spec_router.get("/field_spec/list", summary="字段列表")
async def list_field_spec(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    field_name: str = Query("", description="字段名称"),
    field_group_id: int = Query(None, description="字段组ID"),
    field_type: str = Query(None, description="字段类型"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    q = Q()
    if field_name:
        q &= Q(field_name__contains=field_name) | Q(field_label__contains=field_name)
    if field_group_id:
        q &= Q(field_group_id=field_group_id)
    if field_type:
        q &= Q(field_type=field_type)

    total, fields = await field_spec_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in fields]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@field_spec_router.get("/field_spec/get", summary="字段详情")
async def get_field_spec(
    id: int = Query(..., description="字段ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    field = await field_spec_controller.get(id=id)
    return Success(data=await field.to_dict())


@field_spec_router.post("/field_spec/create", summary="创建字段")
async def create_field_spec(
    field_in: FieldSpecCreate,
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    
    # 检查字段组是否存在
    try:
        field_group = await field_group_config_controller.get(id=field_in.field_group_id)
    except Exception:
        return Fail(code=404, msg="字段组不存在")
    
    field = await field_spec_controller.create(obj_in=field_in)
    
    # 自动更新字段组的Prompt模板
    await update_field_group_prompt(field_in.field_group_id)
    
    return Success(data=await field.to_dict())


@field_spec_router.post("/field_spec/update", summary="更新字段")
async def update_field_spec(
    field_in: FieldSpecUpdate,
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    
    field = await field_spec_controller.get(id=field_in.id)
    field_group_id = field.field_group_id
    
    updated = await field_spec_controller.update(id=field_in.id, obj_in=field_in)
    
    # 如果修改了字段组，需要更新新旧字段组的Prompt模板
    if field_in.field_group_id and field_in.field_group_id != field_group_id:
        await update_field_group_prompt(field_group_id)
        await update_field_group_prompt(field_in.field_group_id)
    else:
        await update_field_group_prompt(field_group_id)
    
    return Success(data=await updated.to_dict())


@field_spec_router.delete("/field_spec/delete", summary="删除字段")
async def delete_field_spec(
    id: int = Query(..., description="字段ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    
    field = await field_spec_controller.get(id=id)
    field_group_id = field.field_group_id
    
    await field_spec_controller.remove(id=id)
    
    # 自动更新字段组的Prompt模板
    await update_field_group_prompt(field_group_id)
    
    return Success(msg="删除成功")
```

#### 4.4.4 公开接口 `app/api/autofill_field_public.py`

```python
"""
字段组配置公开接口 (Dify/三方应用调用)
使用 API Key 认证，不依赖 JWT
"""
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.controllers.autofill import (
    field_group_config_controller,
    field_spec_controller,
)
from app.core.autofill_auth import APIKeyAuth
from app.core.request_parser import parse_request_params
from app.schemas.base import Success
from app.schemas.fill_page import FieldGroupQueryRequest, FieldSpecListRequest

autofill_field_public_router = APIRouter()


# ==================== 字段组配置查询接口 ====================

async def get_field_group_handler(
    request: Request,
    auth_info: dict
):
    """
    查询字段组配置处理逻辑
    """
    params = await parse_request_params(request, FieldGroupQueryRequest)
    
    q = Q(tenant_id=auth_info["tenant_id"], is_active=True)
    
    # 支持多种查询方式
    if params.get("code"):
        q &= Q(code=params["code"])
    else:
        if params.get("app_name"):
            q &= Q(app_name=params["app_name"])
        if params.get("page_name"):
            q &= Q(page_name=params["page_name"])
        if params.get("field_group_name"):
            q &= Q(field_group_name=params["field_group_name"])
    
    field_group = await field_group_config_controller.model.filter(q).first()
    
    if not field_group:
        raise HTTPException(status_code=404, detail="Field group not found")
    
    # 查询关联的字段明细
    fields = await field_spec_controller.model.filter(
        field_group_id=field_group.id,
        is_active=True
    ).all()

    return Success(data={
        "id": field_group.id,
        "code": field_group.code,
        "app_name": field_group.app_name,
        "page_name": field_group.page_name,
        "field_group_name": field_group.field_group_name,
        "prompt_template_base": field_group.prompt_template_base,
        "output_templates": field_group.output_templates,
        "description": field_group.description,
        "fields": [
            {
                "field_name": f.field_name,
                "field_label": f.field_label,
                "field_type": f.field_type,
                "fill_instruction": f.fill_instruction,
                "options": f.options,
                "corrections": f.corrections
            }
            for f in fields
        ]
    })


@autofill_field_public_router.get("/autofill/field_group", summary="查询字段组配置")
@autofill_field_public_router.post("/autofill/field_group", summary="查询字段组配置")
async def get_field_group(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 根据app_name/page_name/字段组名或code查询字段组配置
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    """
    return await get_field_group_handler(request, auth_info)


async def list_field_specs_handler(
    request: Request,
    auth_info: dict
):
    """
    查询字段明细列表处理逻辑
    """
    params = await parse_request_params(request, FieldSpecListRequest)
    
    field_group_id = params.get("field_group_id")
    if not field_group_id:
        raise HTTPException(status_code=400, detail="field_group_id is required")
    
    # 验证字段组是否属于当前租户
    field_group = await field_group_config_controller.model.filter(
        id=field_group_id,
        tenant_id=auth_info["tenant_id"]
    ).first()
    
    if not field_group:
        raise HTTPException(status_code=404, detail="Field group not found")
    
    fields = await field_spec_controller.model.filter(
        field_group_id=field_group_id,
        is_active=True
    ).all()

    return Success(data=[
        {
            "id": f.id,
            "field_name": f.field_name,
            "field_label": f.field_label,
            "field_type": f.field_type,
            "fill_instruction": f.fill_instruction,
            "options": f.options,
            "corrections": f.corrections
        }
        for f in fields
    ])


@autofill_field_public_router.get("/autofill/field_spec/list", summary="查询字段明细列表")
@autofill_field_public_router.post("/autofill/field_spec/list", summary="查询字段明细列表")
async def list_field_specs(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    Dify调用: 查询字段组下的所有字段明细
    支持 GET 和 POST 方法
    支持参数传递方式: Query / Form-Data / JSON Body
    """
    return await list_field_specs_handler(request, auth_info)


# ==================== 新增：直接LLM填单接口 ====================

async def llm_fill_handler(
    request: Request,
    auth_info: dict
):
    """
    直接调用LLM进行填单处理
    支持 Function Calling 和 Prompt 两种模式
    """
    from app.services.autofill.prompt_service import (
        build_function_schema,
        build_fields_instructions,
        render_output_templates
    )
    from app.services.llm_proxy import LLMProxyService
    import time
    
    params = await parse_request_params(request)
    
    # 查询字段组配置
    q = Q(tenant_id=auth_info["tenant_id"], is_active=True)
    if params.get("code"):
        q &= Q(code=params["code"])
    else:
        if params.get("app_name"):
            q &= Q(app_name=params["app_name"])
        if params.get("page_name"):
            q &= Q(page_name=params["page_name"])
        if params.get("field_group_name"):
            q &= Q(field_group_name=params["field_group_name"])
    
    field_group = await field_group_config_controller.model.filter(q).first()
    if not field_group:
        raise HTTPException(status_code=404, detail="Field group not found")
    
    # 查询字段明细
    fields = await field_spec_controller.model.filter(
        field_group_id=field_group.id,
        is_active=True
    ).all()
    
    if not fields:
        raise HTTPException(status_code=404, detail="No active fields found")
    
    query = params.get("query", "")
    system_prompt = params.get("system_prompt")
    output_template_keys = params.get("output_template_keys", [])

    start_time = time.time()
    llm_service = LLMProxyService()

    result = {
        "field_values": {},
        "output_templates": {},
        "function_calling_schema": None,
        "prompt_used": None,
        "llm_response": None,
        "processing_time_ms": 0
    }

    try:
        # 优先尝试 Function Calling 模式
        function_schema = build_function_schema(field_group, fields)
        result["function_calling_schema"] = function_schema

        # 调用LLM Proxy的function_call方法
        llm_response = await llm_service.chat_with_function_calling(
            messages=[
                {"role": "system", "content": system_prompt or field_group.prompt_template_base or "你是一个智能填单助手"},
                {"role": "user", "content": query}
            ],
            functions=[function_schema],
            function_call={"name": function_schema["name"]}
        )

        result["llm_response"] = llm_response

        # 解析function calling结果
        if llm_response.get("function_call"):
            import json
            arguments = llm_response["function_call"].get("arguments", "{}")
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            result["field_values"] = arguments
        else:
            # 降级到 Prompt 模式
            fields_instructions = build_fields_instructions(fields)

            # 构建最终prompt
            prompt_template = system_prompt or field_group.prompt_template_base
            if not prompt_template:
                prompt_template = """你是一个智能填单助手。请根据以下对话内容，填写表单中的各个字段。

## 字段填写说明
{{fields_instructions}}

## 对话内容
{{query}}

请直接输出 JSON 格式的字段值："""

            final_prompt = prompt_template.replace("{{fields_instructions}}", fields_instructions)
            final_prompt = final_prompt.replace("{{query}}", query)

            result["prompt_used"] = final_prompt

            # 调用LLM Proxy
            llm_response = await llm_service.chat(
                messages=[
                    {"role": "user", "content": final_prompt}
                ]
            )

            result["llm_response"] = llm_response

            # 解析JSON响应
            import json
            import re
            content = llm_response.get("content", "{}")
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    result["field_values"] = json.loads(json_match.group())
                except json.JSONDecodeError:
                    result["field_values"] = {"_raw_response": content}
            else:
                result["field_values"] = {"_raw_response": content}
        
        # 渲染输出模板
        if field_group.output_templates and result["field_values"]:
            result["output_templates"] = render_output_templates(
                field_group,
                result["field_values"],
                output_template_keys if output_template_keys else None
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(e)}")
    
    result["processing_time_ms"] = int((time.time() - start_time) * 1000)
    
    return Success(data=result)


@autofill_field_public_router.post("/autofill/llm/fill", summary="直接LLM填单")
async def llm_fill(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    直接调用LLM进行填单，返回JSON字段值
    支持 Function Calling 和 Prompt 两种模式
    支持通过 code 或 app_name/page_name/field_group_name 查询字段组
    """
    return await llm_fill_handler(request, auth_info)


# ==================== 新增：更新字段配置接口 ====================

async def update_field_spec_public_handler(
    request: Request,
    auth_info: dict
):
    """
    更新指定字段组的字段配置
    支持更新 fill_instruction、options、corrections
    """
    params = await parse_request_params(request)
    
    # 查询字段组配置
    q = Q(tenant_id=auth_info["tenant_id"], is_active=True)
    if params.get("code"):
        q &= Q(code=params["code"])
    else:
        if params.get("app_name"):
            q &= Q(app_name=params["app_name"])
        if params.get("page_name"):
            q &= Q(page_name=params["page_name"])
        if params.get("field_group_name"):
            q &= Q(field_group_name=params["field_group_name"])
    
    field_group = await field_group_config_controller.model.filter(q).first()
    if not field_group:
        raise HTTPException(status_code=404, detail="Field group not found")
    
    field_name = params.get("field_name")
    if not field_name:
        raise HTTPException(status_code=400, detail="field_name is required")
    
    # 查询字段
    field = await field_spec_controller.model.filter(
        field_group_id=field_group.id,
        field_name=field_name
    ).first()
    
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    updates = params.get("updates", {})
    updated_fields = []
    
    # 更新 fill_instruction
    if "fill_instruction" in updates:
        field.fill_instruction = updates["fill_instruction"]
        updated_fields.append("fill_instruction")
    
    # 更新 options (select类型)
    if "options" in updates:
        field.options = updates["options"]
        updated_fields.append("options")
    
async def update_field_spec_public_handler(
    request: Request,
    auth_info: dict
):
    """
    更新指定字段组的字段配置 - 支持细粒度更新操作
    
    update_type 支持:
    - full: 完整替换字段数据
    - field_property: 更新字段级属性
    - upsert_option: 添加或更新选项
    - update_option_corrections: 替换选项批注
    - append_option_correction: 追加选项批注
    - update_corrections: 替换字段全局批注
    - append_correction: 追加字段全局批注
    - delete_option: 软删除选项
    - update_option_property: 更新选项属性
    """
    import uuid
    from datetime import datetime
    
    params = await parse_request_params(request)
    
    # 查询字段组配置
    q = Q(tenant_id=auth_info["tenant_id"], is_active=True)
    if params.get("code"):
        q &= Q(code=params["code"])
    else:
        if params.get("app_name"):
            q &= Q(app_name=params["app_name"])
        if params.get("page_name"):
            q &= Q(page_name=params["page_name"])
        if params.get("field_group_name"):
            q &= Q(field_group_name=params["field_group_name"])
    
    field_group = await field_group_config_controller.model.filter(q).first()
    if not field_group:
        raise HTTPException(status_code=404, detail="Field group not found")
    
    field_name = params.get("field_name")
    if not field_name:
        raise HTTPException(status_code=400, detail="field_name is required")
    
    # 查询字段
    field = await field_spec_controller.model.filter(
        field_group_id=field_group.id,
        field_name=field_name
    ).first()
    
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    update_type = params.get("update_type")
    data = params.get("data", {})
    
    if not update_type:
        raise HTTPException(status_code=400, detail="update_type is required")
    
    result = {
        "field_spec_id": field.id,
        "field_group_code": field_group.code,
        "field_name": field.field_name,
        "update_type": update_type,
        "affected": {},
        "updated_at": None
    }
    
    # 获取当前时间
    now = datetime.utcnow().isoformat()
    current_user = auth_info.get("username", "api_user")
    
    if update_type == "full":
        # 完整替换字段数据
        if "fill_instruction" in data:
            field.fill_instruction = data["fill_instruction"]
        if "options" in data:
            field.options = data["options"]
        if "corrections" in data:
            field.corrections = data["corrections"]
        await field.save()
        result["affected"] = {"replaced_fields": list(data.keys())}
    
    elif update_type == "field_property":
        # 更新字段级属性
        if "fill_instruction" in data:
            field.fill_instruction = data["fill_instruction"]
            await field.save()
            result["affected"] = {"updated_property": "fill_instruction"}
    
    elif update_type == "upsert_option":
        # 添加或更新选项（select类型）
        if field.field_type != "select":
            raise HTTPException(status_code=400, detail="Field is not select type")
        
        option = data.get("option", {})
        if not option or "id" not in option:
            raise HTTPException(status_code=400, detail="option with id is required")
        
        # 初始化options结构
        if not field.options:
            field.options = {"source": "static", "items": []}
        if "items" not in field.options:
            field.options["items"] = []
        
        option_id = option["id"]
        items = field.options["items"]
        
        # 查找是否已存在
        existing_idx = None
        for idx, item in enumerate(items):
            if item.get("id") == option_id:
                existing_idx = idx
                break
        
        # 准备选项数据
        option_data = {
            "id": option_id,
            "value": option.get("value", ""),
            "label": option.get("label", ""),
            "base_annotation": option.get("base_annotation", ""),
            "corrections": option.get("corrections", []),
            "is_deleted": option.get("is_deleted", False)
        }
        
        if existing_idx is not None:
            # 更新现有选项
            items[existing_idx] = option_data
            result["affected"] = {"option_id": option_id, "action": "updated"}
        else:
            # 添加新选项
            items.append(option_data)
            result["affected"] = {"option_id": option_id, "action": "created"}
        
        await field.save()
    
    elif update_type == "update_option_corrections":
        # 替换选项批注（通过option_id）
        if field.field_type != "select":
            raise HTTPException(status_code=400, detail="Field is not select type")
        
        option_id = data.get("option_id")
        corrections = data.get("corrections", [])
        
        if not option_id:
            raise HTTPException(status_code=400, detail="option_id is required")
        
        if not field.options or "items" not in field.options:
            raise HTTPException(status_code=404, detail="Options not found")
        
        # 查找选项
        option_found = False
        for item in field.options["items"]:
            if item.get("id") == option_id:
                item["corrections"] = corrections
                option_found = True
                break
        
        if not option_found:
            raise HTTPException(status_code=404, detail=f"Option {option_id} not found")
        
        await field.save()
        result["affected"] = {
            "option_id": option_id,
            "total_corrections": len(corrections)
        }
    
    elif update_type == "append_option_correction":
        # 追加选项批注
        if field.field_type != "select":
            raise HTTPException(status_code=400, detail="Field is not select type")
        
        option_id = data.get("option_id")
        correction = data.get("correction", {})
        
        if not option_id or not correction.get("text"):
            raise HTTPException(status_code=400, detail="option_id and correction.text are required")
        
        if not field.options or "items" not in field.options:
            raise HTTPException(status_code=404, detail="Options not found")
        
        # 查找选项
        option_found = False
        for item in field.options["items"]:
            if item.get("id") == option_id:
                if "corrections" not in item:
                    item["corrections"] = []
                
                new_correction = {
                    "id": correction.get("id") or str(uuid.uuid4())[:8],
                    "text": correction["text"],
                    "created_by": correction.get("created_by") or current_user,
                    "created_at": correction.get("created_at") or now
                }
                item["corrections"].append(new_correction)
                option_found = True
                result["affected"] = {
                    "option_id": option_id,
                    "correction_id": new_correction["id"],
                    "total_corrections": len(item["corrections"])
                }
                break
        
        if not option_found:
            raise HTTPException(status_code=404, detail=f"Option {option_id} not found")
        
        await field.save()
    
    elif update_type == "update_corrections":
        # 替换字段全局批注（text类型）
        corrections = data.get("corrections", [])
        field.corrections = corrections
        await field.save()
        result["affected"] = {"total_corrections": len(corrections)}
    
    elif update_type == "append_correction":
        # 追加字段全局批注
        correction = data.get("correction", {})
        if not correction.get("text"):
            raise HTTPException(status_code=400, detail="correction.text is required")
        
        if not field.corrections:
            field.corrections = []
        
        new_correction = {
            "id": correction.get("id") or str(uuid.uuid4())[:8],
            "text": correction["text"],
            "created_by": correction.get("created_by") or current_user,
            "created_at": correction.get("created_at") or now
        }
        field.corrections.append(new_correction)
        await field.save()
        result["affected"] = {
            "correction_id": new_correction["id"],
            "total_corrections": len(field.corrections)
        }
    
    elif update_type == "delete_option":
        # 软删除选项
        if field.field_type != "select":
            raise HTTPException(status_code=400, detail="Field is not select type")
        
        option_id = data.get("option_id")
        if not option_id:
            raise HTTPException(status_code=400, detail="option_id is required")
        
        if not field.options or "items" not in field.options:
            raise HTTPException(status_code=404, detail="Options not found")
        
        option_found = False
        for item in field.options["items"]:
            if item.get("id") == option_id:
                item["is_deleted"] = True
                option_found = True
                break
        
        if not option_found:
            raise HTTPException(status_code=404, detail=f"Option {option_id} not found")
        
        await field.save()
        result["affected"] = {"option_id": option_id, "action": "soft_deleted"}
    
    elif update_type == "update_option_property":
        # 更新选项属性
        if field.field_type != "select":
            raise HTTPException(status_code=400, detail="Field is not select type")
        
        option_id = data.get("option_id")
        property_updates = data.get("property", {})
        
        if not option_id:
            raise HTTPException(status_code=400, detail="option_id is required")
        
        if not field.options or "items" not in field.options:
            raise HTTPException(status_code=404, detail="Options not found")
        
        option_found = False
        for item in field.options["items"]:
            if item.get("id") == option_id:
                for key, value in property_updates.items():
                    if key in ["value", "label", "base_annotation"]:
                        item[key] = value
                option_found = True
                break
        
        if not option_found:
            raise HTTPException(status_code=404, detail=f"Option {option_id} not found")
        
        await field.save()
        result["affected"] = {"option_id": option_id, "updated_properties": list(property_updates.keys())}
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported update_type: {update_type}")
    
    result["updated_at"] = field.updated_at.isoformat() if field.updated_at else now
    
    return Success(data=result)


@autofill_field_public_router.post("/autofill/field_spec/update", summary="更新字段配置")
async def update_field_spec_public(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    """
    更新指定字段组的字段配置
    支持通过 code 或 app_name/page_name/field_group_name 查询字段组
    支持细粒度更新操作（update_type控制）
    """
    return await update_field_spec_public_handler(request, auth_info)
```

### 4.5 路由注册

#### 4.5.1 修改 `app/api/v1/autofill/__init__.py`

```python
from fastapi import APIRouter

from .autofill import app_router, dropdown_router, record_router, template_router
from .field_group import field_group_router
from .field_spec import field_spec_router
from .page import page_router

autofill_router = APIRouter()

# 注册各模块路由
autofill_router.include_router(app_router, prefix="/autofill", tags=["应用管理"])
autofill_router.include_router(template_router, prefix="/autofill", tags=["总结模板管理"])
autofill_router.include_router(dropdown_router, prefix="/autofill", tags=["下拉选项管理"])
autofill_router.include_router(record_router, prefix="/autofill", tags=["填单记录管理"])
autofill_router.include_router(page_router, prefix="/autofill", tags=["填单页面管理"])
autofill_router.include_router(field_group_router, prefix="/autofill", tags=["字段组配置管理"])
autofill_router.include_router(field_spec_router, prefix="/autofill", tags=["字段明细管理"])
```

#### 4.5.2 修改主路由文件

```python
# 在 app/api/__init__.py 或主应用文件中注册公开接口
from app.api.autofill_field_public import autofill_field_public_router
from app.api.autofill_public import autofill_public_router
from app.api.llm_proxy_public import llm_proxy_public_router

# 注册公开接口（不需要JWT认证）
app.include_router(autofill_public_router, prefix="/api")
app.include_router(autofill_field_public_router, prefix="/api")
app.include_router(llm_proxy_public_router, prefix="/api")
```

---

## 5. 前端实施

### 5.1 API接口定义

#### 5.1.1 修改 `frontend/src/api/index.ts`

```typescript
import request from '@/utils/request'

export default {
  // ... 现有接口 ...

  // autofill - 填单页面管理
  getPageList: (params: any = {}) => request.get('/autofill/page/list', { params }),
  getPageById: (params: any = {}) => request.get('/autofill/page/get', { params }),
  createPage: (data: any = {}) => request.post('/autofill/page/create', data),
  updatePage: (data: any = {}) => request.post('/autofill/page/update', data),
  deletePage: (params: any = {}) => request.delete('/autofill/page/delete', { params }),
  getPageSelect: (params: any = {}) => request.get('/autofill/page/select', { params }),
  generateManual: (params: any = {}) => request.get('/autofill/page/manual', { params }),

  // autofill - 字段组配置管理
  getFieldGroupList: (params: any = {}) => request.get('/autofill/field_group/list', { params }),
  getFieldGroupById: (params: any = {}) => request.get('/autofill/field_group/get', { params }),
  createFieldGroup: (data: any = {}) => request.post('/autofill/field_group/create', data),
  updateFieldGroup: (data: any = {}) => request.post('/autofill/field_group/update', data),
  deleteFieldGroup: (params: any = {}) => request.delete('/autofill/field_group/delete', { params }),
  getFieldGroupSelect: (params: any = {}) => request.get('/autofill/field_group/select', { params }),

  // autofill - 字段明细管理
  getFieldSpecList: (params: any = {}) => request.get('/autofill/field_spec/list', { params }),
  getFieldSpecById: (params: any = {}) => request.get('/autofill/field_spec/get', { params }),
  createFieldSpec: (data: any = {}) => request.post('/autofill/field_spec/create', data),
  updateFieldSpec: (data: any = {}) => request.post('/autofill/field_spec/update', data),
  deleteFieldSpec: (params: any = {}) => request.delete('/autofill/field_spec/delete', { params }),
}
```

### 5.2 填单页面管理页面

#### 5.2.1 创建 `frontend/src/views/autofill/page/index.vue`

```vue
<template>
  <div class="page-management">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      modal-width="700px" @search="handleSearch" @reset="handleReset" @table-change="handleTableChange"
      @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="页面名称" class="filter-item">
            <a-input v-model:value="queryParams.page_name" placeholder="请输入页面名称" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="应用名称" class="filter-item">
            <a-select v-model:value="queryParams.app_name" placeholder="请选择应用" allow-clear :options="appOptions"
              @change="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="租户" class="filter-item">
            <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear
              :options="tenantOptions" @change="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-button v-permission="'post/api/v1/autofill/page/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建页面
        </a-button>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'created_at'">
          <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click="handleViewManual(record)">说明书</a-button>
            <a-button v-permission="'post/api/v1/autofill/page/update'" type="link" size="small"
              @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除该页面吗？" @confirm="handleDelete(record)">
              <a-button v-permission="'delete/api/v1/autofill/page/delete'" type="link" danger
                size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-form-item label="页面名称" name="page_name">
          <a-input v-model:value="form.page_name" placeholder="请输入页面名称" />
        </a-form-item>
        <a-form-item label="页面编码" name="page_code">
          <a-input v-model:value="form.page_code" placeholder="请输入页面编码（英文、数字、下划线）"
            :disabled="modalAction === 'edit'" />
        </a-form-item>
        <a-form-item label="应用" name="app_id">
          <a-select v-model:value="form.app_id" placeholder="请选择应用" :options="appSelectOptions"
            @change="handleAppChange" />
        </a-form-item>
        <a-form-item v-if="userStore.isSuperUser" label="租户" name="tenant_id">
          <a-select v-model:value="form.tenant_id" placeholder="请选择租户" :options="tenantOptions" />
        </a-form-item>
        <a-form-item label="页面描述" name="description">
          <a-textarea v-model:value="form.description" placeholder="请输入页面描述" :rows="3" />
        </a-form-item>
        <a-form-item label="状态" name="is_active">
          <a-switch v-model:checked="form.is_active" />
        </a-form-item>
      </template>
    </CrudTable>

    <!-- 说明书弹窗 -->
    <a-modal v-model:open="manualModalVisible" title="填单说明书" width="800px" :footer="null">
      <a-spin :spinning="manualLoading">
        <pre class="manual-content">{{ manualContent }}</pre>
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'PageManagement' })

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  page_name: '',
  app_name: '',
  tenant_id: undefined as number | undefined,
})

// 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
})

// 弹窗数据
const modalTitle = ref('')
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalForm = reactive({
  id: undefined as number | undefined,
  page_name: '',
  page_code: '',
  app_id: undefined as number | undefined,
  app_name: '',
  tenant_id: undefined as number | undefined,
  description: '',
  is_active: true,
})

// 其他数据
const tenantOptions = ref<any[]>([])
const appOptions = ref<any[]>([])
const appSelectOptions = ref<any[]>([])

// 说明书弹窗
const manualModalVisible = ref(false)
const manualLoading = ref(false)
const manualContent = ref('')

// 计算属性
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '页面名称', dataIndex: 'page_name', key: 'page_name' },
  { title: '页面编码', dataIndex: 'page_code', key: 'page_code' },
  { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
  { title: '状态', key: 'is_active', width: 100 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 200, fixed: 'right' },
])

const filterItemCount = computed(() => {
  let count = 2
  if (userStore.isSuperUser) count++
  return count
})

const modalRules = {
  page_name: [{ required: true, message: '请输入页面名称', trigger: 'blur' }],
  page_code: [
    { required: true, message: '请输入页面编码', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '页面编码只能包含英文、数字、下划线', trigger: 'blur' },
  ],
  app_id: [{ required: true, message: '请选择应用', trigger: 'change', type: 'number' }],
  tenant_id: [{ required: true, message: '请选择租户', trigger: 'change', type: 'number' }],
}

// 方法
const handleAppChange = (value: number) => {
  const app = appSelectOptions.value.find(a => a.value === value)
  if (app) {
    modalForm.app_name = app.label
  }
}

// 加载数据
const fetchData = async () => {
  loading.value = true
  try {
    const res: any = await api.getPageList({
      page: pagination.current,
      page_size: pagination.pageSize,
      ...queryParams,
    })
    if (res.code === 200) {
      tableData.value = res.data || []
      pagination.total = res.total || 0
    }
  } finally {
    loading.value = false
  }
}

const fetchTenantOptions = async () => {
  if (!userStore.isSuperUser) return
  try {
    const res: any = await api.getTenantSelect()
    if (res.code === 200) {
      tenantOptions.value = (res.data || []).map((t: any) => ({
        label: t.name,
        value: t.id,
      }))
    }
  } catch (error) {
    console.error('获取租户列表失败:', error)
  }
}

const fetchAppOptions = async () => {
  try {
    const res: any = await api.getAppSelect()
    if (res.code === 200) {
      appOptions.value = res.data || []
      appSelectOptions.value = res.data || []
    }
  } catch (error) {
    console.error('获取应用列表失败:', error)
  }
}

// 事件处理
const handleSearch = () => {
  pagination.current = 1
  fetchData()
}

const handleReset = () => {
  queryParams.page_name = ''
  queryParams.app_name = ''
  queryParams.tenant_id = undefined
  handleSearch()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const handleAdd = () => {
  modalAction.value = 'add'
  modalTitle.value = '新建页面'
  modalForm.id = undefined
  modalForm.page_name = ''
  modalForm.page_code = ''
  modalForm.app_id = undefined
  modalForm.app_name = ''
  modalForm.tenant_id = userStore.isSuperUser ? undefined : userStore.userInfo?.current_tenant_id
  modalForm.description = ''
  modalForm.is_active = true
  crudTableRef.value?.openModal()
}

const handleEdit = (record: any) => {
  modalAction.value = 'edit'
  modalTitle.value = '编辑页面'
  modalForm.id = record.id
  modalForm.page_name = record.page_name
  modalForm.page_code = record.page_code
  modalForm.app_id = record.app_id
  modalForm.app_name = record.app_name
  modalForm.tenant_id = record.tenant_id
  modalForm.description = record.description
  modalForm.is_active = record.is_active
  crudTableRef.value?.openModal()
}

const handleSave = async () => {
  modalLoading.value = true
  try {
    const apiFunc = modalAction.value === 'add' ? api.createPage : api.updatePage
    const res: any = await apiFunc(modalForm)
    if (res.code === 200) {
      message.success(modalAction.value === 'add' ? '创建成功' : '更新成功')
      crudTableRef.value?.closeModal()
      fetchData()
    } else {
      message.error(res.msg || '操作失败')
    }
  } finally {
    modalLoading.value = false
  }
}

const handleDelete = async (record: any) => {
  try {
    const res: any = await api.deletePage({ id: record.id })
    if (res.code === 200) {
      message.success('删除成功')
      fetchData()
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (error) {
    message.error('删除失败')
  }
}

const handleViewManual = async (record: any) => {
  manualModalVisible.value = true
  manualLoading.value = true
  try {
    const res: any = await api.generateManual({ page_id: record.id })
    if (res.code === 200) {
      manualContent.value = res.data || ''
    } else {
      message.error(res.msg || '生成说明书失败')
    }
  } finally {
    manualLoading.value = false
  }
}

onMounted(() => {
  fetchData()
  fetchTenantOptions()
  fetchAppOptions()
})
</script>

<style scoped lang="less">
.page-management {
  padding: 16px;
}

.manual-content {
  background: #f6f8fa;
  padding: 16px;
  border-radius: 4px;
  max-height: 600px;
  overflow: auto;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
  line-height: 1.6;
}
</style>
```

### 5.3 字段组配置管理页面

#### 5.3.1 创建 `frontend/src/views/autofill/field_group/index.vue`

```vue
<template>
  <div class="field-group-management">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      modal-width="700px" @search="handleSearch" @reset="handleReset" @table-change="handleTableChange"
      @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="字段组名称" class="filter-item">
            <a-input v-model:value="queryParams.field_group_name" placeholder="请输入字段组名称" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="应用名称" class="filter-item">
            <a-select v-model:value="queryParams.app_name" placeholder="请选择应用" allow-clear :options="appOptions"
              @change="handleAppChange" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="页面名称" class="filter-item">
            <a-select v-model:value="queryParams.page_id" placeholder="请选择页面" allow-clear :options="pageOptions"
              @change="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="租户" class="filter-item">
            <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear
              :options="tenantOptions" @change="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-button v-permission="'post/api/v1/autofill/field_group/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建字段组
        </a-button>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'prompt_template_base'">
          <a-button type="link" size="small" @click="viewPrompt(record)">查看</a-button>
        </template>
        <template v-if="column.key === 'created_at'">
          <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button v-permission="'post/api/v1/autofill/field_group/update'" type="link" size="small"
              @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除该字段组吗？" @confirm="handleDelete(record)">
              <a-button v-permission="'delete/api/v1/autofill/field_group/delete'" type="link" danger
                size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-form-item label="字段组名称" name="field_group_name">
          <a-input v-model:value="form.field_group_name" placeholder="请输入字段组名称" />
        </a-form-item>
        <a-form-item label="应用" name="app_name">
          <a-select v-model:value="form.app_name" placeholder="请选择应用" :options="appOptions" />
        </a-form-item>
        <a-form-item label="页面" name="page_id">
          <a-select v-model:value="form.page_id" placeholder="请选择页面" :options="pageOptions" @change="handlePageChange" />
        </a-form-item>
        <a-form-item v-if="userStore.isSuperUser" label="租户" name="tenant_id">
          <a-select v-model:value="form.tenant_id" placeholder="请选择租户" :options="tenantOptions" />
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="form.description" placeholder="请输入字段组描述" :rows="3" />
        </a-form-item>
        <a-form-item label="状态" name="is_active">
          <a-switch v-model:checked="form.is_active" />
        </a-form-item>
      </template>
    </CrudTable>

    <!-- Prompt模板查看弹窗 -->
    <a-modal v-model:open="promptModalVisible" title="Prompt模板" width="800px" :footer="null">
      <a-spin :spinning="promptLoading">
        <pre class="prompt-content">{{ currentPrompt }}</pre>
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'FieldGroupManagement' })

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  field_group_name: '',
  app_name: '',
  page_id: undefined as number | undefined,
  tenant_id: undefined as number | undefined,
})

// 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
})

// 弹窗数据
const modalTitle = ref('')
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalForm = reactive({
  id: undefined as number | undefined,
  field_group_name: '',
  app_name: '',
  page_id: undefined as number | undefined,
  page_name: '',
  tenant_id: undefined as number | undefined,
  prompt_template_base: '',
  output_templates: {} as Record<string, { template: string; description: string }>,
  description: '',
  is_active: true,
})

// 其他数据
const tenantOptions = ref<any[]>([])
const appOptions = ref<any[]>([])
const pageOptions = ref<any[]>([])

// Prompt弹窗
const promptModalVisible = ref(false)
const promptLoading = ref(false)
const currentPrompt = ref('')

// 计算属性
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: 'Code', dataIndex: 'code', key: 'code', width: 180 },
  { title: '字段组名称', dataIndex: 'field_group_name', key: 'field_group_name' },
  { title: '应用名称', dataIndex: 'app_name', key: 'app_name' },
  { title: '页面名称', dataIndex: 'page_name', key: 'page_name' },
  { title: '模板数量', key: 'template_count', width: 100, customRender: ({ record }: any) => Object.keys(record.output_templates || {}).length },
  { title: '状态', key: 'is_active', width: 100 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
])

const filterItemCount = computed(() => {
  let count = 3
  if (userStore.isSuperUser) count++
  return count
})

const modalRules = {
  field_group_name: [{ required: true, message: '请输入字段组名称', trigger: 'blur' }],
  app_name: [{ required: true, message: '请选择应用', trigger: 'change' }],
  page_id: [{ required: true, message: '请选择页面', trigger: 'change', type: 'number' }],
  tenant_id: [{ required: true, message: '请选择租户', trigger: 'change', type: 'number' }],
}

// 方法
const handlePageChange = (value: number) => {
  const page = pageOptions.value.find(p => p.value === value)
  if (page) {
    modalForm.page_name = page.label
  }
}

const handleAppChange = async (value: string) => {
  queryParams.page_id = undefined
  await fetchPageOptions(value)
  handleSearch()
}

// 加载数据
const fetchData = async () => {
  loading.value = true
  try {
    const res: any = await api.getFieldGroupList({
      page: pagination.current,
      page_size: pagination.pageSize,
      ...queryParams,
    })
    if (res.code === 200) {
      tableData.value = res.data || []
      pagination.total = res.total || 0
    }
  } finally {
    loading.value = false
  }
}

const fetchTenantOptions = async () => {
  if (!userStore.isSuperUser) return
  try {
    const res: any = await api.getTenantSelect()
    if (res.code === 200) {
      tenantOptions.value = (res.data || []).map((t: any) => ({
        label: t.name,
        value: t.id,
      }))
    }
  } catch (error) {
    console.error('获取租户列表失败:', error)
  }
}

const fetchAppOptions = async () => {
  try {
    const res: any = await api.getAppSelect()
    if (res.code === 200) {
      appOptions.value = res.data || []
    }
  } catch (error) {
    console.error('获取应用列表失败:', error)
  }
}

const fetchPageOptions = async (appName?: string) => {
  try {
    const params: any = {}
    if (appName) params.app_name = appName
    const res: any = await api.getPageSelect(params)
    if (res.code === 200) {
      pageOptions.value = res.data || []
    }
  } catch (error) {
    console.error('获取页面列表失败:', error)
  }
}

// 事件处理
const handleSearch = () => {
  pagination.current = 1
  fetchData()
}

const handleReset = () => {
  queryParams.field_group_name = ''
  queryParams.app_name = ''
  queryParams.page_id = undefined
  queryParams.tenant_id = undefined
  handleSearch()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const handleAdd = () => {
  modalAction.value = 'add'
  modalTitle.value = '新建字段组'
  modalForm.id = undefined
  modalForm.field_group_name = ''
  modalForm.app_name = ''
  modalForm.page_id = undefined
  modalForm.page_name = ''
  modalForm.tenant_id = userStore.isSuperUser ? undefined : userStore.userInfo?.current_tenant_id
  modalForm.prompt_template_base = ''
  modalForm.output_templates = {}
  modalForm.description = ''
  modalForm.is_active = true
  crudTableRef.value?.openModal()
}

const handleEdit = (record: any) => {
  modalAction.value = 'edit'
  modalTitle.value = '编辑字段组'
  modalForm.id = record.id
  modalForm.field_group_name = record.field_group_name
  modalForm.app_name = record.app_name
  modalForm.page_id = record.page_id
  modalForm.page_name = record.page_name
  modalForm.tenant_id = record.tenant_id
  modalForm.prompt_template_base = record.prompt_template_base || ''
  modalForm.output_templates = record.output_templates || {}
  modalForm.description = record.description
  modalForm.is_active = record.is_active
  fetchPageOptions(record.app_name)
  crudTableRef.value?.openModal()
}

// 输出模板管理
const addOutputTemplate = () => {
  const key = `template_${Object.keys(modalForm.output_templates).length + 1}`
  modalForm.output_templates[key] = { template: '', description: '' }
}

const removeOutputTemplate = (key: string) => {
  delete modalForm.output_templates[key]
}

const handleSave = async () => {
  modalLoading.value = true
  try {
    const apiFunc = modalAction.value === 'add' ? api.createFieldGroup : api.updateFieldGroup
    const res: any = await apiFunc(modalForm)
    if (res.code === 200) {
      message.success(modalAction.value === 'add' ? '创建成功' : '更新成功')
      crudTableRef.value?.closeModal()
      fetchData()
    } else {
      message.error(res.msg || '操作失败')
    }
  } finally {
    modalLoading.value = false
  }
}

const handleDelete = async (record: any) => {
  try {
    const res: any = await api.deleteFieldGroup({ id: record.id })
    if (res.code === 200) {
      message.success('删除成功')
      fetchData()
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (error) {
    message.error('删除失败')
  }
}

const viewPrompt = (record: any) => {
  promptModalVisible.value = true
  currentPrompt.value = record.prompt_template_base || ''
}

onMounted(() => {
  fetchData()
  fetchTenantOptions()
  fetchAppOptions()
  fetchPageOptions()
})
</script>

<style scoped lang="less">
.field-group-management {
  padding: 16px;
}

.prompt-content {
  background: #f6f8fa;
  padding: 16px;
  border-radius: 4px;
  max-height: 600px;
  overflow: auto;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
```

### 5.4 字段明细管理页面

#### 5.4.1 创建 `frontend/src/views/autofill/field_spec/index.vue`

```vue
<template>
  <div class="field-spec-management">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      modal-width="700px" @search="handleSearch" @reset="handleReset" @table-change="handleTableChange"
      @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="字段名称" class="filter-item">
            <a-input v-model:value="queryParams.field_name" placeholder="请输入字段名称" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="字段组" class="filter-item">
            <a-select v-model:value="queryParams.field_group_id" placeholder="请选择字段组" allow-clear
              :options="fieldGroupOptions" @change="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="字段类型" class="filter-item">
            <a-select v-model:value="queryParams.field_type" placeholder="请选择字段类型" allow-clear
              :options="fieldTypeOptions" @change="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-button v-permission="'post/api/v1/autofill/field_spec/create'" type="primary" @click="handleAdd">
          <PlusOutlined />
          新建字段
        </a-button>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'field_type'">
          <a-tag>{{ getFieldTypeText(record.field_type) }}</a-tag>
        </template>
        <template v-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'created_at'">
          <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button v-permission="'post/api/v1/autofill/field_spec/update'" type="link" size="small"
              @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除该字段吗？" @confirm="handleDelete(record)">
              <a-button v-permission="'delete/api/v1/autofill/field_spec/delete'" type="link" danger
                size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-form-item label="字段组" name="field_group_id">
          <a-select v-model:value="form.field_group_id" placeholder="请选择字段组" :options="fieldGroupOptions" />
        </a-form-item>
        <a-form-item label="字段名称" name="field_name">
          <a-input v-model:value="form.field_name" placeholder="请输入字段英文名（如：business_type）" :disabled="modalAction === 'edit'" />
        </a-form-item>
        <a-form-item label="字段标签" name="field_label">
          <a-input v-model:value="form.field_label" placeholder="请输入字段显示名称（如：业务类型）" />
        </a-form-item>
        <a-form-item label="字段类型" name="field_type">
          <a-select v-model:value="form.field_type" placeholder="请选择字段类型" :options="fieldTypeOptions" :disabled="modalAction === 'edit'" />
        </a-form-item>
        <a-form-item label="填写指引" name="fill_instruction">
          <a-textarea v-model:value="form.fill_instruction" placeholder="请输入字段填写指引，用于生成LLM描述" :rows="3" />
        </a-form-item>
        
        <!-- Select类型选项配置 -->
        <template v-if="form.field_type === 'select'">
          <a-divider>选项配置</a-divider>
          <a-form-item label="选项来源" name="options.source">
            <a-radio-group v-model:value="form.options.source">
              <a-radio value="static">静态配置</a-radio>
              <a-radio value="api">三方接口</a-radio>
            </a-radio-group>
          </a-form-item>
          <a-form-item v-if="form.options.source === 'api'" label="API标识符" name="api_identifier">
            <a-input v-model:value="form.options.api_identifier" placeholder="如：business_types" />
            <a-button type="link" size="small" @click="syncOptionsFromApi">从接口同步</a-button>
          </a-form-item>
          <a-form-item label="选项列表">
            <a-table :dataSource="form.options.items" :columns="optionColumns" size="small" :pagination="false">
              <template #bodyCell="{ column, record, index }">
                <template v-if="column.key === 'label'">
                  <a-input v-model:value="record.label" size="small" />
                </template>
                <template v-if="column.key === 'value'">
                  <a-input v-model:value="record.value" size="small" />
                </template>
                <template v-if="column.key === 'base_annotation'">
                  <a-input v-model:value="record.base_annotation" size="small" placeholder="选项说明" />
                </template>
                <template v-if="column.key === 'corrections'">
                  <a-button type="link" size="small" @click="editOptionCorrections(record)">
                    批注({{ record.corrections?.length || 0 }})
                  </a-button>
                </template>
                <template v-if="column.key === 'action'">
                  <a-button type="link" danger size="small" @click="removeOption(index)">删除</a-button>
                </template>
              </template>
            </a-table>
            <a-button type="dashed" block style="margin-top: 8px" @click="addOption">
              <PlusOutlined /> 添加选项
            </a-button>
          </a-form-item>
        </template>
        
        <!-- Text类型全局批注 -->
        <template v-if="form.field_type === 'text'">
          <a-divider>全局批注 (Corrections)</a-divider>
          <div v-for="(corr, index) in form.corrections" :key="corr.id || index" class="correction-item">
            <a-card size="small">
              <div class="correction-content">{{ corr.text }}</div>
              <div class="correction-meta">
                <span>by {{ corr.created_by }} at {{ corr.created_at }}</span>
                <a-button type="link" danger size="small" @click="removeCorrection(index)">删除</a-button>
              </div>
            </a-card>
          </div>
          <a-button type="dashed" block @click="addCorrection">
            <PlusOutlined /> 添加批注
          </a-button>
        </template>
        
        <a-form-item label="状态" name="is_active" style="margin-top: 16px">
          <a-switch v-model:checked="form.is_active" />
        </a-form-item>
      </template>
    </CrudTable>
    
    <!-- 选项批注编辑弹窗 -->
    <a-modal v-model:open="correctionModalVisible" title="编辑批注" @ok="saveCorrections">
      <div v-for="(corr, index) in editingCorrections" :key="index" class="correction-edit-item">
        <a-textarea v-model:value="corr.text" placeholder="请输入批注内容" :rows="2" />
        <a-button type="link" danger @click="removeEditingCorrection(index)">删除</a-button>
      </div>
      <a-button type="dashed" block @click="addEditingCorrection">
        <PlusOutlined /> 添加批注
      </a-button>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'

defineOptions({ name: 'FieldSpecManagement' })

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  field_name: '',
  field_group_id: undefined as number | undefined,
  field_type: undefined as string | undefined,
})

// 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
})

// 弹窗数据
const modalTitle = ref('')
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const modalForm = reactive({
  id: undefined as number | undefined,
  field_group_id: undefined as number | undefined,
  field_name: '',
  field_label: '',
  field_type: 'text',
  fill_instruction: '',
  options: {
    source: 'static',
    api_identifier: '',
    last_sync_at: '',
    items: [] as Array<{
      value: string
      label: string
      base_annotation: string
      corrections: Array<{ id: string; text: string; created_by: string; created_at: string }>
      is_deleted: boolean
    }>,
  },
  corrections: [] as Array<{ id: string; text: string; created_by: string; created_at: string }>,
  is_active: true,
})

// 选项表格列
const optionColumns = [
  { title: '显示文本', key: 'label', width: 120 },
  { title: '选项值', key: 'value', width: 100 },
  { title: '基础标注', key: 'base_annotation', width: 150 },
  { title: '批注', key: 'corrections', width: 80 },
  { title: '操作', key: 'action', width: 60 },
]

// 批注编辑弹窗
const correctionModalVisible = ref(false)
const editingOption = ref<any>(null)
const editingCorrections = ref<Array<{ text: string; created_by: string; created_at: string }>>([])

// 其他数据
const fieldGroupOptions = ref<any[]>([])

const fieldTypeOptions = [
  { label: '文本', value: 'text' },
  { label: '下拉选择', value: 'select' },
  { label: '多行文本', value: 'textarea' },
  { label: '数字', value: 'number' },
  { label: '日期', value: 'date' },
  { label: '日期时间', value: 'datetime' },
]

// 计算属性
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '字段名称', dataIndex: 'field_name', key: 'field_name' },
  { title: '字段标签', dataIndex: 'field_label', key: 'field_label' },
  { title: '字段类型', key: 'field_type', width: 100 },
  { title: '状态', key: 'is_active', width: 100 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
])

const filterItemCount = computed(() => 3)

const modalRules = {
  field_group_id: [{ required: true, message: '请选择字段组', trigger: 'change', type: 'number' }],
  field_name: [
    { required: true, message: '请输入字段名称', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '字段名称只能包含英文、数字、下划线', trigger: 'blur' },
  ],
  field_label: [{ required: true, message: '请输入字段标签', trigger: 'blur' }],
  field_type: [{ required: true, message: '请选择字段类型', trigger: 'change' }],
}

// 方法
const getFieldTypeText = (type: string) => {
  const map: Record<string, string> = {
    text: '文本',
    select: '下拉选择',
    textarea: '多行文本',
    number: '数字',
    date: '日期',
    datetime: '日期时间',
  }
  return map[type] || type
}

// 加载数据
const fetchData = async () => {
  loading.value = true
  try {
    const res: any = await api.getFieldSpecList({
      page: pagination.current,
      page_size: pagination.pageSize,
      ...queryParams,
    })
    if (res.code === 200) {
      tableData.value = res.data || []
      pagination.total = res.total || 0
    }
  } finally {
    loading.value = false
  }
}

const fetchFieldGroupOptions = async () => {
  try {
    const res: any = await api.getFieldGroupSelect()
    if (res.code === 200) {
      fieldGroupOptions.value = res.data || []
    }
  } catch (error) {
    console.error('获取字段组列表失败:', error)
  }
}

// 事件处理
const handleSearch = () => {
  pagination.current = 1
  fetchData()
}

const handleReset = () => {
  queryParams.field_name = ''
  queryParams.field_group_id = undefined
  queryParams.field_type = undefined
  handleSearch()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const handleAdd = () => {
  modalAction.value = 'add'
  modalTitle.value = '新建字段'
  modalForm.id = undefined
  modalForm.field_group_id = undefined
  modalForm.field_name = ''
  modalForm.field_label = ''
  modalForm.field_type = 'text'
  modalForm.fill_instruction = ''
  modalForm.options = {
    source: 'static',
    api_identifier: '',
    last_sync_at: '',
    items: [],
  }
  modalForm.corrections = []
  modalForm.is_active = true
  crudTableRef.value?.openModal()
}

const handleEdit = (record: any) => {
  modalAction.value = 'edit'
  modalTitle.value = '编辑字段'
  modalForm.id = record.id
  modalForm.field_group_id = record.field_group_id
  modalForm.field_name = record.field_name
  modalForm.field_label = record.field_label
  modalForm.field_type = record.field_type
  modalForm.fill_instruction = record.fill_instruction || ''
  modalForm.options = record.options || {
    source: 'static',
    api_identifier: '',
    last_sync_at: '',
    items: [],
  }
  modalForm.corrections = record.corrections || []
  modalForm.is_active = record.is_active
  crudTableRef.value?.openModal()
}

// 选项管理方法
const addOption = () => {
  modalForm.options.items.push({
    value: '',
    label: '',
    base_annotation: '',
    corrections: [],
    is_deleted: false,
  })
}

const removeOption = (index: number) => {
  modalForm.options.items.splice(index, 1)
}

const editOptionCorrections = (option: any) => {
  editingOption.value = option
  editingCorrections.value = [...(option.corrections || [])]
  correctionModalVisible.value = true
}

const saveCorrections = () => {
  if (editingOption.value) {
    editingOption.value.corrections = editingCorrections.value.map(c => ({
      ...c,
      created_by: c.created_by || userStore.userInfo?.username || 'unknown',
      created_at: c.created_at || new Date().toISOString(),
    }))
  }
  correctionModalVisible.value = false
}

const addEditingCorrection = () => {
  editingCorrections.value.push({
    text: '',
    created_by: userStore.userInfo?.username || 'unknown',
    created_at: new Date().toISOString(),
  })
}

const removeEditingCorrection = (index: number) => {
  editingCorrections.value.splice(index, 1)
}

// 全局批注管理
const addCorrection = () => {
  modalForm.corrections.push({
    id: Date.now().toString(),
    text: '',
    created_by: userStore.userInfo?.username || 'unknown',
    created_at: new Date().toISOString(),
  })
}

const removeCorrection = (index: number) => {
  modalForm.corrections.splice(index, 1)
}

// 从API同步选项
const syncOptionsFromApi = async () => {
  if (!modalForm.options.api_identifier) {
    message.warning('请先输入API标识符')
    return
  }
  message.info('同步功能需要后端实现对应的API调用')
}

const handleSave = async () => {
  modalLoading.value = true
  try {
    const apiFunc = modalAction.value === 'add' ? api.createFieldSpec : api.updateFieldSpec
    const res: any = await apiFunc(modalForm)
    if (res.code === 200) {
      message.success(modalAction.value === 'add' ? '创建成功' : '更新成功')
      crudTableRef.value?.closeModal()
      fetchData()
    } else {
      message.error(res.msg || '操作失败')
    }
  } finally {
    modalLoading.value = false
  }
}

const handleDelete = async (record: any) => {
  try {
    const res: any = await api.deleteFieldSpec({ id: record.id })
    if (res.code === 200) {
      message.success('删除成功')
      fetchData()
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (error) {
    message.error('删除失败')
  }
}

onMounted(() => {
  fetchData()
  fetchFieldGroupOptions()
})
</script>

<style scoped lang="less">
.field-spec-management {
  padding: 16px;
}
</style>
```

### 5.5 路由配置

#### 5.5.1 修改 `frontend/src/router/routes.ts`

```typescript
import type { RouteRecordRaw } from 'vue-router'

export const asyncRoutes: RouteRecordRaw[] = [
  // ... 现有路由 ...

  // 智能填单模块
  {
    path: '/autofill',
    name: 'Autofill',
    meta: { title: '智能填单', icon: 'FormOutlined' },
    children: [
      {
        path: 'app',
        name: 'AutofillApp',
        component: () => import('@/views/autofill/app/index.vue'),
        meta: { title: '应用管理', icon: 'AppstoreOutlined' },
      },
      {
        path: 'page',
        name: 'AutofillPage',
        component: () => import('@/views/autofill/page/index.vue'),
        meta: { title: '填单页面', icon: 'FileTextOutlined' },
      },
      {
        path: 'field_group',
        name: 'AutofillFieldGroup',
        component: () => import('@/views/autofill/field_group/index.vue'),
        meta: { title: '字段组配置', icon: 'GroupOutlined' },
      },
      {
        path: 'field_spec',
        name: 'AutofillFieldSpec',
        component: () => import('@/views/autofill/field_spec/index.vue'),
        meta: { title: '字段明细', icon: 'FieldStringOutlined' },
      },
      {
        path: 'template',
        name: 'AutofillTemplate',
        component: () => import('@/views/autofill/template/index.vue'),
        meta: { title: '总结模板', icon: 'FileTextOutlined' },
      },
      {
        path: 'dropdown',
        name: 'AutofillDropdown',
        component: () => import('@/views/autofill/dropdown/index.vue'),
        meta: { title: '下拉选项', icon: 'DownCircleOutlined' },
      },
      {
        path: 'record',
        name: 'AutofillRecord',
        component: () => import('@/views/autofill/record/index.vue'),
        meta: { title: '填单记录', icon: 'HistoryOutlined' },
      },
    ],
  },
]
```

---

## 6. 菜单配置

### 6.1 数据库菜单数据

```sql
-- 智能填单模块菜单
INSERT INTO menus (name, path, component, icon, title, hidden, keep_alive, permission_id, parent_id, created_at, updated_at) VALUES
('Autofill', '/autofill', 'Layout', 'FormOutlined', '智能填单', 0, 1, NULL, 0, NOW(), NOW()),
('AutofillApp', 'app', '/autofill/app/index', 'AppstoreOutlined', '应用管理', 0, 1, NULL, LAST_INSERT_ID(), NOW(), NOW()),
('AutofillPage', 'page', '/autofill/page/index', 'FileTextOutlined', '填单页面', 0, 1, NULL, (SELECT id FROM menus WHERE name='Autofill'), NOW(), NOW()),
('AutofillFieldGroup', 'field_group', '/autofill/field_group/index', 'GroupOutlined', '字段组配置', 0, 1, NULL, (SELECT id FROM menus WHERE name='Autofill'), NOW(), NOW()),
('AutofillFieldSpec', 'field_spec', '/autofill/field_spec/index', 'FieldStringOutlined', '字段明细', 0, 1, NULL, (SELECT id FROM menus WHERE name='Autofill'), NOW(), NOW()),
('AutofillTemplate', 'template', '/autofill/template/index', 'FileTextOutlined', '总结模板', 0, 1, NULL, (SELECT id FROM menus WHERE name='Autofill'), NOW(), NOW()),
('AutofillDropdown', 'dropdown', '/autofill/dropdown/index', 'DownCircleOutlined', '下拉选项', 0, 1, NULL, (SELECT id FROM menus WHERE name='Autofill'), NOW(), NOW()),
('AutofillRecord', 'record', '/autofill/record/index', 'HistoryOutlined', '填单记录', 0, 1, NULL, (SELECT id FROM menus WHERE name='Autofill'), NOW(), NOW());
```

---

## 7. 测试计划

### 7.1 单元测试

| 测试项 | 测试内容 | 预期结果 |
|--------|----------|----------|
| 模型测试 | 创建/更新/删除 FillPage | 数据库操作成功 |
| 模型测试 | 创建/更新/删除 FieldGroupConfig | 数据库操作成功 |
| 模型测试 | 创建/更新/删除 FieldSpec | 数据库操作成功，Prompt自动更新 |
| 服务测试 | Prompt组装逻辑 | 生成正确格式的Prompt |

### 7.2 接口测试

| 测试项 | 测试内容 | 预期结果 |
|--------|----------|----------|
| 页面管理API | CRUD操作 | 返回正确数据 |
| 字段组API | CRUD操作 | 返回正确数据 |
| 字段明细API | CRUD操作 | Prompt自动更新 |
| 公开接口 | API Key认证 | 正确返回字段组配置 |

### 7.3 集成测试

| 测试项 | 测试内容 | 预期结果 |
|--------|----------|----------|
| 端到端流程 | 创建页面→字段组→字段→生成说明书 | 说明书内容正确 |
| Prompt更新 | 修改字段→查看字段组Prompt | Prompt自动更新 |
| 权限控制 | 跨租户访问 | 返回403错误 |

---

## 8. 部署检查清单

### 8.1 部署前检查

- [ ] 数据库迁移已执行
- [ ] 后端代码已更新
- [ ] 前端代码已构建
- [ ] 菜单数据已插入
- [ ] API权限已配置

### 8.2 部署后验证

- [ ] 页面管理功能正常
- [ ] 字段组配置功能正常
- [ ] 字段明细功能正常
- [ ] 说明书生成功能正常
- [ ] 公开接口可正常访问
- [ ] 多租户隔离正常

---

## 9. 附录

### 9.1 目录结构

```
autofill/
├── app/
│   ├── api/
│   │   ├── autofill_field_public.py    # 字段组公开接口
│   │   └── v1/autofill/
│   │       ├── __init__.py             # 路由注册
│   │       ├── page.py                 # 页面管理接口
│   │       ├── field_group.py          # 字段组接口
│   │       └── field_spec.py           # 字段明细接口
│   ├── controllers/
│   │   └── autofill.py                 # 控制器（已更新）
│   ├── models/
│   │   └── autofill.py                 # 模型（已更新）
│   ├── schemas/
│   │   └── fill_page.py                # 新增Schema
│   └── services/
│       └── prompt_service.py           # Prompt服务
├── frontend/src/
│   ├── api/index.ts                    # API接口（已更新）
│   └── views/autofill/
│       ├── page/index.vue              # 页面管理
│       ├── field_group/index.vue       # 字段组管理
│       └── field_spec/index.vue        # 字段明细管理
└── docs/autofill/
    ├── DESIGN.md                       # 设计文档
    └── IMPLEMENTATION.md               # 实施文档
```

### 9.2 相关文档

- [设计文档](./DESIGN.md)
- [技术文档](./tech.md)
- [架构文档](../architecture/architecture.md)
