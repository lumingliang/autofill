# LLM 填单接口使用指南

## 接口概述

`/api/autofill/llm/fill` 接口支持两种传参方式，用于灵活地指定需要提取的字段。

---

## 方式一：传统传参（全局字段过滤）

使用 `group_names` 和 `field_names` 进行全局字段过滤。

### 适用场景
- 简单的字段提取需求
- 所有字段组使用相同的字段过滤规则

### 请求示例

```json
{
  "page_name": "用户信息页",
  "group_names": ["default"],
  "field_names": ["scene_category", "service_types"],
  "query": "用户对话内容..."
}
```

### 参数说明

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| page_name | string | 是 | 页面名称 |
| group_names | string[] | 否 | 字段组名称列表，不传则查询所有字段组 |
| field_names | string[] | 否 | 字段名称列表，不传则返回所有字段 |
| query | string | 是 | 用户对话内容 |

### 逻辑说明

1. 查询指定的 `group_names` 字段组
2. 在每个字段组中，只保留 `field_names` 指定的字段
3. 如果 `field_names` 为空，则返回该字段组的所有字段

---

## 方式二：分组传参（按字段组分别指定）

使用 `group_fields` 参数，按字段组分别指定需要查询的字段。

### 适用场景
- 分步骤填单场景
- 不同字段组需要不同的字段过滤规则
- 某些字段组需要查询所有字段，某些字段组只需要查询特定字段

### 请求示例

```json
{
  "page_name": "用户信息页",
  "group_fields": {
    "default": ["救援-二三级"],
    "服务记录-道路救援请求": []
  },
  "query": "用户对话内容..."
}
```

### 参数说明

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| page_name | string | 是 | 页面名称 |
| group_fields | object | 否 | 字段组与字段的映射关系 |
| query | string | 是 | 用户对话内容 |

### group_fields 格式

```json
{
  "字段组名1": ["字段1", "字段2"],  // 指定该字段组只查询这些字段
  "字段组名2": []                   // 空数组表示查询该字段组的所有字段
}
```

### 逻辑说明

1. 查询 `group_fields` 中指定的所有字段组
2. 对于每个字段组：
   - 如果值为非空数组，只查询数组中指定的字段
   - 如果值为空数组 `[]`，查询该字段组的所有字段
3. 最终合并所有字段组的字段，生成统一的 Function Calling Schema

---

## 两种方式的优先级

如果同时传入 `group_fields` 和 `group_names`/`field_names`：
- **优先使用 `group_fields`**
- `group_names` 和 `field_names` 会被忽略

---

## 分步骤填单测试流程

### 测试脚本位置
`/Users/lu/code/code/py/autofill/scripts/test_step_by_step_fill.py`

### 测试场景
模拟 400 客服对话，分两步提取表单字段：

#### 第一步：提取基础字段

**目标字段**：
- `一级事件类型` - 确定事件分类
- `service_types` - 服务类型
- `scene_category` - 场景分类

**传参方式**：传统传参

```json
{
  "page_name": "用户信息页",
  "group_names": ["default"],
  "field_names": ["一级事件类型", "service_types", "scene_category"],
  "query": "10轮客服对话..."
}
```

**预期结果**：
```json
{
  "一级事件类型": "救援",
  "scene_category": "道路救援请求",
  "service_types": ["拖车服务"]
}
```

#### 第二步：基于第一步结果动态提取

**逻辑**：
1. 根据 `scene_category` 的值（"道路救援请求"），确定服务记录字段组：`服务记录-道路救援请求`
2. 根据 `一级事件类型` 的值（"救援"），确定二级事件类型字段：`救援-二三级`

**传参方式**：分组传参（`group_fields`）

```json
{
  "page_name": "用户信息页",
  "group_fields": {
    "default": ["救援-二三级"],
    "服务记录-道路救援请求": []
  },
  "query": "10轮客服对话..."
}
```

**语义说明**：
- `default: ["救援-二三级"]` - 只查询 default 字段组下的 `救援-二三级` 字段
- `服务记录-道路救援请求: []` - 查询 `服务记录-道路救援请求` 字段组的**所有字段**

**预期结果**：
```json
{
  "救援-二三级": "拖车服务 - 高速拖车",
  "vin_code": null,
  "vehicle_system": "动力电池系统故障",
  "contact_phone": "13900139000",
  "customer_name": "李明"
}
```

---

## 关键实现逻辑

### 1. 请求模型定义

```python
# app/schemas/public/field_group.py
class LLMFillRequest(BasePublicRequest):
    page_name: str
    group_names: List[str] = []
    field_names: List[str] = []
    group_fields: Optional[Dict[str, List[str]]] = None  # 分组传参
    query: str
```

### 2. 参数处理逻辑

```python
# app/api/public/handlers/llm_handlers.py
async def llm_fill_handler(request: Request, auth_info: dict):
    params = await parse_request_params(request, LLMFillRequest)
    
    # 处理 group_fields 参数（新的传参格式）
    group_fields = params.get("group_fields")
    if group_fields:
        # 使用新的传参格式
        group_names = list(group_fields.keys())
        all_field_names = []
        for fields in group_fields.values():
            if fields:
                all_field_names.extend(fields)
        field_names = all_field_names if all_field_names else []
    else:
        # 使用旧的传参格式
        group_names = params.get("group_names", [])
        field_names = params.get("field_names", [])
    
    # 调用 fetch_field_groups
    result_data = await fetch_field_groups(
        tenant_id=tenant_id,
        app_name=app_name,
        page_name=params.get("page_name"),
        group_names=group_names,
        field_names=field_names,
        group_fields=group_fields  # 传递 group_fields 以支持按字段组分别过滤
    )
```

### 3. 字段组分别过滤逻辑

```python
# app/api/public/handlers/field_group_handlers.py
async def fetch_field_groups(..., group_fields: Dict[str, List[str]] = None):
    for fg in field_groups:
        # 优先使用 group_fields 按字段组分别过滤
        if group_fields and fg.group_name in group_fields:
            group_field_names = group_fields[fg.group_name]
            if group_field_names:  # 如果指定了字段列表，则过滤
                field_q &= Q(field_name__in=group_field_names)
            # 如果 group_field_names 是空列表，则不添加字段过滤
        elif field_names_filter:
            # 使用全局 field_names 过滤
            field_q &= Q(field_name__in=list(field_names_filter))
```

### 4. 统一 Schema 构建逻辑

```python
# 构建统一的 Function Calling Schema
if group_fields:
    # 使用 group_fields 时，all_properties 已经只包含需要的字段
    filtered_properties = all_properties
    required_fields = list(all_properties.keys())
elif field_names_filter:
    # 使用全局 field_names 过滤
    filtered_properties = {k: v for k, v in all_properties.items() if k in field_names_filter}
    required_fields = list(filtered_properties.keys())
```

---

## 测试执行

### 运行测试脚本

```bash
cd /Users/lu/code/code/py/autofill
python scripts/test_step_by_step_fill.py
```

### 预期输出

```
======================================================================
【第一步】提取基础字段
======================================================================
提取字段: 一级事件类型, service_types, scene_category
...
✅ 提取成功:
  一级事件类型: 救援
  scene_category: 道路救援请求
  service_types: ['拖车服务']

======================================================================
【第二步】动态提取字段
======================================================================
📋 default 字段组查询字段: 救援-二三级
📋 服务记录-道路救援请求 字段组查询字段: 所有字段
...
✅ 提取成功:
  救援-二三级: 拖车服务 - 高速拖车
  vin_code: None
  vehicle_system: 动力电池系统故障
  contact_phone: 13900139000
  customer_name: 李明
```

---

## 注意事项

1. **字段组名称匹配**：`group_fields` 中的字段组名称必须与数据库中的 `group_name` 完全匹配
2. **空数组语义**：`[]` 表示查询该字段组的所有字段，不是不查询
3. **优先级**：`group_fields` 优先级高于 `group_names` + `field_names`
4. **字段存在性检查**：如果指定的字段在字段组中不存在，该字段组会被跳过
