# 模板字段同步脚本实施文档

## 一、需求概述

根据总结模板自动创建/更新字段组和字段，实现模板与字段配置的同步。

### 核心流程
1. 查询总结模板列表，获取模板名称、摘要和模板内容
2. 创建/更新"场景分类"下拉字段（在default字段组）
3. 解析模板内容中的变量（如 `${customer_name}`），为每个模板创建对应的字段组和服务记录字段

---

## 二、现有架构分析

### 2.1 数据模型关系

```
AppManagement (应用)
    ├── api_key: 用于认证
    ├── tenant_id: 租户ID
    └── app_name: 应用名称

SummaryTemplate (总结模板)
    ├── name: 模板名称
    ├── summary: 模板摘要
    ├── template_content: 模板内容（含 ${变量}）
    ├── class_name: 分类名称
    ├── tenant_id: 租户ID
    └── app_name: 应用名称

FillPage (填单页面)
    ├── page_name: 页面名称（如"用户信息页"）
    ├── page_code: 页面编码
    ├── app_id: 应用ID
    ├── tenant_id: 租户ID
    └── app_name: 应用名称

FieldGroupConfig (字段组配置)
    ├── group_name: 字段组名称
    ├── group_code: 字段组编码（自动生成 fg_xxx）
    ├── page_id: 关联页面ID
    ├── page_name: 页面名称
    ├── output_templates: 输出模板配置（JSON）
    ├── tenant_id: 租户ID
    └── app_name: 应用名称

FieldSpec (字段明细)
    ├── field_name: 字段英文名（用于JSON输出）
    ├── field_label: 字段显示名称
    ├── field_type: 字段类型（select/text）
    ├── fill_instruction: 填写指引
    ├── options: 选项配置（select类型）
    ├── tenant_id: 租户ID
    └── app_name: 应用名称

FieldGroupFieldSpec (多对多关联表)
    ├── field_group_id: 字段组ID
    ├── field_spec_id: 字段明细ID
    ├── tenant_id: 租户ID
    └── app_name: 应用名称
```

### 2.2 现有Public接口

#### 2.2.1 模板相关接口

**查询模板列表**
```
GET/POST /api/public/autofill/summary_template/list
Authorization: Bearer {api_key}

请求参数:
{
    "class_name": "可选，分类名称"
}

响应:
{
    "code": 200,
    "data": [
        {
            "id": 1,
            "name": "模板名称",
            "summary": "模板摘要",
            "class_name": "分类"
        }
    ]
}
```

**查询模板详情**
```
GET/POST /api/public/autofill/summary_template
Authorization: Bearer {api_key}

请求参数:
{
    "id": 1
}

响应:
{
    "code": 200,
    "data": {
        "id": 1,
        "name": "模板名称",
        "summary": "模板摘要",
        "class_name": "分类",
        "template_content": "模板内容 ${变量名}"
    }
}
```

#### 2.2.2 字段组相关接口

**查询字段组配置** ⚠️ **需要改造**
```
GET/POST /api/public/autofill/field_group
Authorization: Bearer {api_key}

请求参数:
{
    "page_name": "用户信息页",      // 新增：通过页面名称查询
    "group_name": "default"         // 新增：通过字段组名称查询
}

响应:
{
    "code": 200,
    "data": [
        {
            "id": 1,
            "group_name": "字段组名称",
            "group_code": "fg_xxx",
            "page_id": 1,
            "page_name": "用户信息页",
            "prompt_template_base": "prompt模板",
            "output_templates": {},
            "version": 1
        }
    ]
}
```

**改造说明**:
- 原接口通过 `page_code` + `group_code` 查询
- 新接口改为通过 `page_name` + `group_name` 查询
- 需要在接口内部根据 `app_name` + `page_name` 查找 `page_id`
- 再根据 `page_id` + `group_name` 查找字段组

**查询字段明细列表** ⚠️ **需要改造**
```
GET/POST /api/public/autofill/field_spec/list
Authorization: Bearer {api_key}

请求参数:
{
    "page_name": "用户信息页",      // 新增：页面名称
    "group_name": "服务记录-xxx",   // 新增：字段组名称
    "field_name": "customer_name"   // 可选：字段名（精确匹配）
}

响应:
{
    "code": 200,
    "data": [
        {
            "id": 1,
            "field_name": "字段名",
            "field_label": "字段标签",
            "field_type": "select/text",
            "fill_instruction": "填写指引",
            "options": {},
            "corrections": [],
            "is_active": true,
            "field_group_ids": [1, 2]
        }
    ]
}
```

**改造说明**:
- 原接口通过 `field_group_id` 查询
- 新接口改为通过 `page_name` + `group_name` + `field_name` 查询
- 需要在接口内部：
  1. 根据 `app_name` + `page_name` 查找 `page_id`
  2. 根据 `page_id` + `group_name` 查找 `field_group_id`
  3. 通过中间表查询字段列表
  4. 如传入 `field_name`，则精确匹配字段名

#### 2.2.3 认证机制

```python
# API Key 认证流程
1. 请求头携带: Authorization: Bearer {api_key}
2. 通过 AppManagement 表查询 api_key 获取:
   - tenant_id: 租户ID
   - app_name: 应用名称
   - dify_url: Dify服务地址
   - dify_api_key: Dify API密钥
```

---

## 三、需求实现分析

### 3.1 需求拆解

#### 步骤1: 查询总结模板
- **接口**: `GET/POST /api/public/autofill/summary_template/list`
- **参数**: 可选 `class_name` 过滤
- **返回**: 模板列表（id, name, summary, class_name）
- **后续**: 根据模板id查询详情获取 `template_content`

#### 步骤2: 创建/更新"场景分类"字段

**当前问题分析**:
现有Public接口只有查询功能，没有创建/更新字段组和字段的接口。

**需要新增接口**:

```
POST /api/public/autofill/field_group/upsert
Authorization: Bearer {api_key}

请求参数:
{
    "page_name": "用户信息页",      // 用于查找页面
    "group_name": "default",        // 字段组名称
    "group_code": "",               // 可选，不传则自动生成
    "output_templates": {},         // 可选
    "fields": [                     // 字段列表（批量创建/更新）
        {
            "field_name": "场景分类",
            "field_label": "场景分类",
            "field_type": "select",
            "fill_instruction": "请选择场景分类",
            "options": {
                "source": "static",
                "items": [
                    {
                        "value": "模板名称1",
                        "label": "模板名称1",
                        "fill_instruction": "模板摘要1"
                    },
                    {
                        "value": "模板名称2",
                        "label": "模板名称2",
                        "fill_instruction": "模板摘要2"
                    }
                ]
            }
        }
    ]
}

逻辑:
1. 根据 app_name + page_name 查找页面ID
2. 根据 page_id + group_name 查找字段组
   - 存在: 返回现有字段组
   - 不存在: 创建新字段组（自动生成group_code）
3. 遍历 fields 列表批量处理字段:
   - 字段不存在: 创建字段 + 添加字段组关联
   - 字段已存在: 更新字段信息 + 添加字段组关联（如未关联）
   # 注：场景分类字段只有一个（"场景分类"），但使用批量接口统一处理
4. 返回字段组信息 + 处理后的字段列表
```

**场景分类字段说明**:
- **字段类型**: `select`（下拉类型）
- **options 结构**:
  - `source`: `"static"`（静态选项）
  - `items`: 下拉选项列表，每个选项包含:
    - `value`: 选项值（等于模板名称）
    - `label`: 显示标签（等于模板名称）
    - `fill_instruction`: 填写指引（等于模板摘要）
    - **注意**: 直接将 `base_annotation` 改为 `fill_instruction`，不需要兼容旧字段

#### 步骤3: 解析模板变量并创建字段

**模板内容解析**:
```python
import re

def extract_variables(template_content: str) -> list[str]:
    """提取模板中的变量名，如 ${customer_name} -> customer_name"""
    pattern = r'\$\{([^}]+)\}'
    matches = re.findall(pattern, template_content)
    return list(set(matches))  # 去重
```

**字段组命名规则**:
```
字段组名称 = f"服务记录-{模板名称}"
```

**字段创建规则**:
```python
for var in extracted_variables:
    field_data = {
        "page_name": "用户信息页",
        "group_name": f"服务记录-{template_name}",
        "field_name": var,                    # 变量名如 customer_name
        "field_label": var,                   # 使用变量名作为标签
        "field_type": "text",                 # 默认text类型
        "fill_instruction": f"请填写{var}字段",
        "options": {}
    }
```

**保存模板内容**:
```python
# 将模板内容保存到字段组的 output_templates 字段
output_templates = {
    "default": {
        "template": template_content,
        "description": "默认输出模板"
    }
}
```

---

## 四、接口开发计划

### 4.1 需要新增的Public接口

#### 接口1: 字段组批量创建/更新接口（含字段列表）

**文件**: `app/api/public/autofill.py`

```python
async def upsert_field_group_handler(
    request: Request,
    auth_info: dict
):
    """
    创建或更新字段组，并批量处理字段列表
    - 如果字段组不存在，自动创建
    - 如果页面不存在，返回错误
    - 遍历字段列表：字段不存在则创建并添加关联，存在则只添加关联关系
    """
    from pydantic import BaseModel
    from app.models.autofill import FieldGroupFieldSpec

    class FieldItem(BaseModel):
        field_name: str
        field_label: Optional[str] = None
        field_type: str = "text"
        fill_instruction: Optional[str] = None
        options: Optional[Dict] = None

    class UpsertFieldGroupRequest(BaseModel):
        page_name: str
        group_name: str
        group_code: Optional[str] = None
        output_templates: Optional[Dict] = None
        prompt_template_base: Optional[str] = None
        fields: List[FieldItem] = []  # 字段列表

    params = await parse_request_params(request, UpsertFieldGroupRequest)
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 1. 查找页面
    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params["page_name"]
    ).first()

    if not page:
        raise HTTPException(status_code=404, detail=f"Page '{params['page_name']}' not found")

    # 2. 查找或创建字段组
    field_group = await field_group_config_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_id=page.id,
        group_name=params["group_name"]
    ).first()

    if field_group:
        # 更新字段组
        update_data = {}
        if params.get("output_templates") is not None:
            update_data["output_templates"] = params["output_templates"]
        if params.get("prompt_template_base") is not None:
            update_data["prompt_template_base"] = params["prompt_template_base"]
        if update_data:
            update_data["version"] = field_group.version + 1
            await field_group_config_controller.update(id=field_group.id, obj_in=update_data)
            field_group = await field_group_config_controller.get(id=field_group.id)
    else:
        # 创建字段组
        from app.schemas.fill_page import FieldGroupConfigCreate, OutputTemplateItem

        group_code = params.get("group_code") or generate_field_group_code()
        output_templates = params.get("output_templates", {})

        # 转换output_templates格式
        formatted_templates = {}
        for key, value in output_templates.items():
            if isinstance(value, dict):
                formatted_templates[key] = OutputTemplateItem(**value)
            else:
                formatted_templates[key] = OutputTemplateItem(template=value, description="")

        create_data = FieldGroupConfigCreate(
            group_name=params["group_name"],
            group_code=group_code,
            page_id=page.id,
            page_name=page.page_name,
            app_name=app_name,
            tenant_id=tenant_id,
            output_templates=formatted_templates,
            prompt_template_base=params.get("prompt_template_base", "")
        )
        field_group = await field_group_config_controller.create_field_group(obj_in=create_data)

    # 3. 批量处理字段列表
    processed_fields = []
    fields = params.get("fields", [])

    for field_item in fields:
        field_name = field_item["field_name"]
        field_label = field_item.get("field_label") or field_name
        field_type = field_item.get("field_type", "text")
        fill_instruction = field_item.get("fill_instruction") or ""
        options = field_item.get("options", {})

        # 验证field_type
        if field_type not in ["select", "text"]:
            field_type = "text"

        # 查找或创建字段
        field_spec = await field_spec_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            field_name=field_name
        ).first()

        if field_spec:
            # 字段已存在，更新信息
            from app.schemas.fill_page import FieldSpecUpdate, FieldOptions

            update_data = FieldSpecUpdate(
                id=field_spec.id,
                field_label=field_label,
                field_type=field_type,
                fill_instruction=fill_instruction
            )

            # 处理options
            if options:
                if isinstance(options, dict):
                    update_data.options = FieldOptions(**options)
                else:
                    update_data.options = options

            field_spec = await field_spec_controller.update_field_spec(
                id=field_spec.id,
                obj_in=update_data,
                tenant_id=tenant_id,
                app_name=app_name
            )
        else:
            # 字段不存在，创建新字段
            from app.schemas.fill_page import FieldSpecCreate, FieldOptions

            create_data = FieldSpecCreate(
                field_name=field_name,
                field_label=field_label,
                field_type=field_type,
                fill_instruction=fill_instruction,
                field_group_ids=[field_group.id]
            )

            # 处理options
            if options:
                if isinstance(options, dict):
                    create_data.options = FieldOptions(**options)
                else:
                    create_data.options = options

            field_spec = await field_spec_controller.create_field_spec(
                obj_in=create_data,
                tenant_id=tenant_id,
                app_name=app_name
            )

        # 确保字段与当前字段组的关联关系
        existing_relation = await FieldGroupFieldSpec.filter(
            field_group_id=field_group.id,
            field_spec_id=field_spec.id
        ).first()

        if not existing_relation:
            await FieldGroupFieldSpec.create(
                field_group_id=field_group.id,
                field_spec_id=field_spec.id,
                tenant_id=tenant_id,
                app_name=app_name
            )

        # 获取字段关联的所有字段组
        relations = await FieldGroupFieldSpec.filter(field_spec_id=field_spec.id).all()
        group_ids = [r.field_group_id for r in relations]

        processed_fields.append({
            "id": field_spec.id,
            "field_name": field_spec.field_name,
            "field_label": field_spec.field_label,
            "field_type": field_spec.field_type,
            "field_group_ids": group_ids,
            "is_new": not existing_relation if field_spec else False
        })

    return Success(data={
        "id": field_group.id,
        "group_name": field_group.group_name,
        "group_code": field_group.group_code,
        "page_id": field_group.page_id,
        "output_templates": field_group.output_templates,
        "version": field_group.version,
        "fields": processed_fields,
        "field_count": len(processed_fields)
    })


@autofill_public_router.post("/autofill/field_group/upsert", summary="创建或更新字段组（含批量字段）")
async def upsert_field_group(
    request: Request,
    auth_info: dict = Depends(APIKeyAuth.authenticate)
):
    return await upsert_field_group_handler(request, auth_info)
```

#### 接口2: 查询接口改造（直接使用新参数，不兼容旧参数）

**改造1: 查询字段组配置接口** ⚠️ **需要改造**

**文件**: `app/api/public/autofill.py`

```python
async def get_field_group_handler(
    request: Request,
    auth_info: dict
):
    """
    查询字段组配置处理逻辑（改造后）
    - 只支持通过 page_name + group_name 查询
    """
    from pydantic import BaseModel

    class FieldGroupRequest(BaseModel):
        page_name: str                       # 页面名称（必填）
        group_name: str                      # 字段组名称（必填）

    params = await parse_request_params(request, FieldGroupRequest)
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 使用 page_name 查询页面
    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params["page_name"]
    ).first()

    if not page:
        return Success(data=[])

    # 构建字段组查询条件
    q = Q(page_id=page.id, group_name=params["group_name"])

    field_groups = await field_group_config_controller.model.filter(q).all()

    return Success(data=[
        {
            "id": fg.id,
            "group_name": fg.group_name,
            "group_code": fg.group_code,
            "page_id": fg.page_id,
            "page_name": page.page_name if page else "",
            "prompt_template_base": fg.prompt_template_base,
            "output_templates": fg.output_templates,
            "version": fg.version,
        }
        for fg in field_groups
    ])
```

**改造2: 查询字段明细列表接口** ⚠️ **需要改造**

**文件**: `app/api/public/autofill.py`

```python
async def list_field_spec_handler(
    request: Request,
    auth_info: dict
):
    """
    查询字段明细列表处理逻辑（改造后）
    - 只支持通过 page_name + group_name + field_name 查询
    """
    from pydantic import BaseModel
    from app.models.autofill import FieldGroupFieldSpec

    class FieldSpecListRequest(BaseModel):
        page_name: str                       # 页面名称（必填）
        group_name: str                      # 字段组名称（必填）
        field_name: Optional[str] = None     # 字段名（可选，精确匹配）

    params = await parse_request_params(request, FieldSpecListRequest)
    tenant_id = auth_info["tenant_id"]
    app_name = auth_info["app_name"]

    # 1. 查找页面
    page = await fill_page_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params["page_name"]
    ).first()

    if not page:
        return Success(data=[])

    # 2. 查找字段组
    field_group = await field_group_config_controller.model.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        page_id=page.id,
        group_name=params["group_name"]
    ).first()

    if not field_group:
        return Success(data=[])

    # 通过中间表查询关联的字段ID
    relations = await FieldGroupFieldSpec.filter(
        field_group_id=field_group_id,
        tenant_id=tenant_id,
        app_name=app_name
    ).all()

    field_spec_ids = [r.field_spec_id for r in relations]

    if not field_spec_ids:
        return Success(data=[])

    # 构建字段查询条件
    q = Q(id__in=field_spec_ids, is_active=True)

    # 如果传入了 field_name，精确匹配
    if params.get("field_name"):
        q &= Q(field_name=params["field_name"])

    field_specs = await field_spec_controller.model.filter(q).all()

    # 获取每个字段关联的字段组
    result = []
    for fs in field_specs:
        relations = await FieldGroupFieldSpec.filter(field_spec_id=fs.id).all()
        group_ids = [r.field_group_id for r in relations]
        result.append({
            "id": fs.id,
            "field_name": fs.field_name,
            "field_label": fs.field_label,
            "field_type": fs.field_type,
            "fill_instruction": fs.fill_instruction,
            "options": fs.options,
            "corrections": fs.corrections,
            "is_active": fs.is_active,
            "field_group_ids": group_ids,
        })

    return Success(data=result)
```

### 4.2 需要修改的后端逻辑

#### 修改1: 放宽字段名校验 + OptionItem字段统一

**文件**: `app/schemas/fill_page.py`

```python
# 1. 放宽字段名校验
# 原校验规则（只允许英文、数字、下划线）
field_name: str = Field(..., max_length=64, pattern=r"^[a-zA-Z0-9_]+$")

# 新校验规则（允许中文等字符，因为需求要求字段名可以是中文）
field_name: str = Field(..., max_length=64)


# 2. OptionItem 字段统一：将 base_annotation 改为 fill_instruction
# 原定义
class OptionItem(BaseModel):
    """选项项"""
    value: str = ""
    label: str = ""
    base_annotation: str = ""  # 改为 fill_instruction
    corrections: List[Dict] = []
    is_deleted: bool = False

# 新定义
class OptionItem(BaseModel):
    """选项项"""
    value: str = ""
    label: str = ""
    fill_instruction: str = ""  # 统一使用 fill_instruction
    corrections: List[Dict] = []
    is_deleted: bool = False
```

**文件**: `app/controllers/autofill.py` - `FieldSpecController`

```python
# 修改 create_field_spec：删除字段名唯一性检查
async def create_field_spec(self, obj_in: FieldSpecCreate, tenant_id: int = 0, app_name: str = "") -> FieldSpec:
    """创建字段明细"""
    # 删除字段名唯一性检查（同一字段可以关联多个字段组）

    # 创建字段（不包含关联关系）
    spec_data = obj_in.model_dump(exclude={'field_group_ids'})
    spec_data['tenant_id'] = tenant_id
    spec_data['app_name'] = app_name
    field_spec = await self.create(spec_data)

    # 创建关联关系
    if obj_in.field_group_ids:
        for group_id in obj_in.field_group_ids:
            await FieldGroupFieldSpec.create(
                field_group_id=group_id,
                field_spec_id=field_spec.id,
                tenant_id=tenant_id,
                app_name=app_name
            )

    return field_spec
```

同样修改 `update_field_spec` 中的唯一性检查逻辑（删除相关检查代码）

---

## 五、脚本实现

### 5.1 脚本结构

**文件**: `scripts/sync_template_fields.py`

```python
#!/usr/bin/env python3
"""
模板字段同步脚本
根据总结模板自动创建/更新字段组和字段

使用方法:
    python scripts/sync_template_fields.py --appkey af_xxx [--base-url http://localhost:9999]
"""

import argparse
import re
import sys
from typing import List, Dict, Optional
import httpx


class TemplateFieldSync:
    """模板字段同步器"""

    def __init__(self, appkey: str, base_url: str = "http://localhost:9999"):
        self.appkey = appkey
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {appkey}",
            "Content-Type": "application/json"
        }

    def extract_variables(self, template_content: str) -> List[str]:
        """提取模板中的变量名"""
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, template_content)
        return list(set(matches))

    async def get_summary_templates(self, class_name: str = "") -> List[Dict]:
        """获取总结模板列表"""
        url = f"{self.base_url}/api/public/autofill/summary_template/list"
        params = {}
        if class_name:
            params["class_name"] = class_name

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                raise Exception(f"API error: {result.get('msg')}")

            return result.get("data", [])

    async def get_template_detail(self, template_id: int) -> Dict:
        """获取模板详情"""
        url = f"{self.base_url}/api/public/autofill/summary_template"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params={"id": template_id})
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                raise Exception(f"API error: {result.get('msg')}")

            return result.get("data", {})

    async def upsert_field_group(self, page_name: str, group_name: str,
                                  output_templates: Optional[Dict] = None,
                                  fields: Optional[List[Dict]] = None) -> Dict:
        """创建或更新字段组（含批量字段）"""
        url = f"{self.base_url}/api/public/autofill/field_group/upsert"

        data = {
            "page_name": page_name,
            "group_name": group_name
        }
        if output_templates:
            data["output_templates"] = output_templates
        if fields:
            data["fields"] = fields

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                raise Exception(f"API error: {result.get('msg')}")

            return result.get("data", {})

    async def sync_scenario_field(self, templates: List[Dict]):
        """同步场景分类字段"""
        print("=" * 50)
        print("步骤2: 同步场景分类字段")
        print("=" * 50)

        # 准备下拉选项（从模板名称生成）
        # 注意：使用 fill_instruction 替代 base_annotation，保持与 text 类型字段一致
        items = []
        for t in templates:
            items.append({
                "value": t["name"],
                "label": t["name"],
                "fill_instruction": t.get("summary", ""),  # 使用 fill_instruction 替代 base_annotation
                "corrections": [],
                "is_deleted": False
            })

        options = {
            "source": "static",
            "items": items
        }

        # 创建/更新场景分类字段（使用批量接口）
        scenario_field = {
            "field_name": "场景分类",
            "field_label": "场景分类",
            "field_type": "select",
            "fill_instruction": "请选择场景分类",
            "options": options
        }

        result = await self.upsert_field_group(
            page_name="用户信息页",
            group_name="default",
            fields=[scenario_field]
        )

        print(f"场景分类字段已同步: ID={result['fields'][0]['id']}, Name={result['fields'][0]['field_name']}")
        print(f"选项数量: {len(items)}")

    async def sync_template_fields(self, templates: List[Dict]):
        """同步模板字段"""
        print("=" * 50)
        print("步骤3: 同步模板字段")
        print("=" * 50)

        for template in templates:
            template_id = template["id"]
            template_name = template["name"]

            print(f"\n处理模板: {template_name}")

            # 获取模板详情
            detail = await self.get_template_detail(template_id)
            template_content = detail.get("template_content", "")

            # 提取变量
            variables = self.extract_variables(template_content)
            print(f"  提取到 {len(variables)} 个变量: {variables}")

            if not variables:
                print(f"  跳过: 没有变量")
                continue

            # 准备字段列表
            fields = []
            for var in variables:
                fields.append({
                    "field_name": var,
                    "field_label": var,
                    "field_type": "text",
                    "fill_instruction": f"请填写{var}字段"
                })

            # 创建/更新字段组（含批量字段）
            group_name = f"服务记录-{template_name}"
            output_templates = {
                "default": {
                    "template": template_content,
                    "description": f"{template_name}的默认输出模板"
                }
            }

            group = await self.upsert_field_group(
                page_name="用户信息页",
                group_name=group_name,
                output_templates=output_templates,
                fields=fields
            )
            print(f"  字段组已同步: {group['group_name']} (ID={group['id']})")
            print(f"  字段数量: {group['field_count']}")
            for field in group['fields']:
                print(f"    字段已同步: {field['field_name']} (ID={field['id']})")

    async def run(self):
        """执行同步"""
        print("=" * 50)
        print("模板字段同步脚本")
        print("=" * 50)
        print(f"AppKey: {self.appkey}")
        print(f"Base URL: {self.base_url}")

        # 步骤1: 获取模板列表
        print("\n" + "=" * 50)
        print("步骤1: 获取总结模板列表")
        print("=" * 50)

        templates = await self.get_summary_templates()
        print(f"获取到 {len(templates)} 个模板")

        if not templates:
            print("没有模板需要处理")
            return

        for t in templates:
            print(f"  - {t['name']} (ID={t['id']}, class={t.get('class_name', '')})")

        # 步骤2: 同步场景分类字段
        await self.sync_scenario_field(templates)

        # 步骤3: 同步模板字段
        await self.sync_template_fields(templates)

        print("\n" + "=" * 50)
        print("同步完成!")
        print("=" * 50)


async def main():
    parser = argparse.ArgumentParser(description="模板字段同步脚本")
    parser.add_argument("--appkey", required=True, help="API Key (af_xxx)")
    parser.add_argument("--base-url", default="http://localhost:9999", help="API基础URL（默认: http://localhost:9999）")
    parser.add_argument("--class-name", default="", help="按分类名称过滤模板")

    args = parser.parse_args()

    sync = TemplateFieldSync(appkey=args.appkey, base_url=args.base_url)
    await sync.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 六、实施步骤

### 6.1 后端接口开发

1. **新增Public接口**
   - 在 `app/api/public/autofill.py` 中添加 `upsert_field_group` 接口（支持批量字段处理）

2. **修改字段名校验**
   - 修改 `app/schemas/fill_page.py` 中的 `FieldSpecCreate` 和 `FieldSpecUpdate`
   - 移除或放宽 `field_name` 的正则校验

3. **修改字段创建逻辑**
   - 修改 `app/controllers/autofill.py` 中的 `create_field_spec` 方法
   - 注释掉字段名唯一性检查（允许同名字段关联不同字段组）

### 6.2 脚本部署

1. 将脚本保存到 `scripts/sync_template_fields.py`
2. 添加执行权限: `chmod +x scripts/sync_template_fields.py`
3. 测试运行:
   ```bash
   python scripts/sync_template_fields.py --appkey af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR
   ```

### 6.3 执行流程

```
+-------------------+     +------------------------+     +-------------------+
|   1. 查询模板列表   | --> | 2. 同步场景分类字段      | --> | 3. 同步模板字段    |
+-------------------+     +------------------------+     +-------------------+
         |                            |                            |
         v                            v                            v
   GET /summary_template        POST /field_group            POST /field_group
         /list                      /upsert                      /upsert
         |                            |                            |
         |                            v                            v
         |                      创建/更新字段组+字段:          创建/更新字段组+字段:
         |                      - 页面: 用户信息页              - 页面: 用户信息页
         |                      - 字段组: default               - 字段组名: 服务记录-{模板名}
         |                      - 字段: 场景分类(select)        - output_templates:
         |                        选项来自模板名称列表            {default: {template}}
         |                                                      - 字段: 模板变量列表
         v
   返回模板列表:
   [{id, name, summary, class_name}]
```

---

## 七、接口调用示例

### 7.1 查询模板列表

```bash
curl -X GET "http://localhost:9999/api/public/autofill/summary_template/list" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
```

### 7.2 创建/更新字段组（含批量字段）

```bash
curl -X POST "http://localhost:9999/api/public/autofill/field_group/upsert" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/json" \
  -d '{
    "page_name": "用户信息页",
    "group_name": "服务记录-救援模板",
    "output_templates": {
      "default": {
        "template": "救援地址: ${address}, 联系人: ${contact}",
        "description": "默认输出模板"
      }
    },
    "fields": [
      {
        "field_name": "address",
        "field_label": "救援地址",
        "field_type": "text",
        "fill_instruction": "请填写救援地址"
      },
      {
        "field_name": "contact",
        "field_label": "联系人",
        "field_type": "text",
        "fill_instruction": "请填写联系人姓名"
      }
    ]
  }'
```

### 7.3 创建场景分类字段（select类型）

```bash
curl -X POST "http://localhost:9999/api/public/autofill/field_group/upsert" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/json" \
  -d '{
    "page_name": "用户信息页",
    "group_name": "default",
    "fields": [
      {
        "field_name": "场景分类",
        "field_label": "场景分类",
        "field_type": "select",
        "fill_instruction": "请选择场景分类",
        "options": {
          "source": "static",
          "items": [
            {
              "value": "救援场景",
              "label": "救援场景",
              "fill_instruction": "用于道路救援场景的服务记录"
            },
            {
              "value": "咨询场景",
              "label": "咨询场景",
              "fill_instruction": "用于客户咨询服务场景"
            }
          ]
        }
      }
    ]
  }'
```

---

## 八、注意事项

1. **字段名校验**: 需求要求字段名可以是中文，需要移除原有的正则校验 `^[a-zA-Z0-9_]+$`

2. **字段组自动创建**: `upsert_field_group` 接口会在字段组不存在时自动创建字段组，并批量处理字段列表

3. **字段关联**: 同名字段可以关联多个字段组，通过 `FieldGroupFieldSpec` 中间表管理。批量接口会自动添加字段与字段组的关联关系

4. **模板变量解析**: 使用正则 `\$\{([^}]+)\}` 提取 `${变量名}` 格式的变量

5. **output_templates 格式**: 字段组的 `output_templates` 字段是 JSON 格式，结构为:
   ```json
   {
     "default": {
       "template": "模板内容",
       "description": "描述"
     }
   }
   ```

6. **后端端口**: 项目后端服务运行在 **9999** 端口（不是默认的 8000），脚本和 curl 示例都已更新
