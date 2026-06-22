---
name: "autofill-form"
description: "执行自动填单流程，按顺序填写：一级事件类型→二级事件类型→三级事件类型→选择模板→填写服务记录总结。Invoke when user needs to fill a form, process service records, or complete event type classification."
---

# 自动填单 Skill

## 概述

本 Skill 用于执行自动填单，按固定顺序填写：
1. **一级事件类型** (event_type_level1) - 下拉选择
2. **二级事件类型** (event_type_level2) - 下拉选择，依赖一级ID
3. **三级事件类型** (event_type_level3) - 下拉选择，依赖二级ID
4. **服务记录模板** - 根据一级事件类型选择
5. **服务记录总结** (service_summary) - 文本输入，基于模板生成

**填写顺序：一级 → 二级 → 三级 → 选择模板 → 填写服务记录总结**

## 何时调用

- 用户需要填写服务记录表单
- 用户提到"填单"、"记录"、"事件类型"等关键词
- 需要处理客户投诉、救援请求、保养预约等业务

## CLI 脚本

所有脚本位于：`/Users/lu/code/code/py/autofill/scripts/cli/`

| 脚本 | 功能 | 用法 |
|------|------|------|
| `get_field.py` | 获取字段列表/选项/模板列表/模板内容 | `get_field.py [field_name] [--parent_id] [--list_templates] [--template_id]` |
| `get_field_rules.py` | 获取字段/选项/模板规则 | `get_field_rules.py field_id [option_id] [--parent_id] [--template_id]` |
| `submit_form.py` | 提交表单 | `submit_form.py JSON_DATA` |

## 填单步骤

### 第1步：获取字段列表

```bash
python /Users/lu/code/code/py/autofill/scripts/cli/get_field.py --format json
```

**返回：** 4个字段的ID、名称、类型

### 第2步：填写一级事件类型

**2.1 并行获取下拉选项与字段规则**

一级事件类型的选项列表和对应规则相互独立，可以在同一次工具调用中并行执行，以减少等待时间：

```bash
python /Users/lu/code/code/py/autofill/scripts/cli/get_field.py event_type_level1 --format json
python /Users/lu/code/code/py/autofill/scripts/cli/get_field_rules.py event_type_level1 --format json
```

如果后续需要查看单个选项的详细规则，可再执行：
```bash
python /Users/lu/code/code/py/autofill/scripts/cli/get_field_rules.py event_type_level1 EVT001 --format json
```

**2.2 根据用户对话选择**
- 从对话提取关键词匹配选项
- 记录选择的一级ID（如 EVT001）

### 第3步：填写二级事件类型

**3.1 并行获取下拉选项与字段规则（传入一级ID）**

```bash
python /Users/lu/code/code/py/autofill/scripts/cli/get_field.py event_type_level2 --parent_id EVT001 --format json
python /Users/lu/code/code/py/autofill/scripts/cli/get_field_rules.py event_type_level2 --parent_id EVT001 --format json
```

如果只想查看单个选项规则，可再执行：
```bash
python /Users/lu/code/code/py/autofill/scripts/cli/get_field_rules.py event_type_level2 EVT001001 --format json
```

**3.2 根据用户对话选择**
- 记录选择的二级ID（如 EVT001001）

### 第4步：填写三级事件类型

**4.1 并行获取下拉选项与字段规则（传入二级ID）**

```bash
python /Users/lu/code/code/py/autofill/scripts/cli/get_field.py event_type_level3 --parent_id EVT001001 --format json
python /Users/lu/code/code/py/autofill/scripts/cli/get_field_rules.py event_type_level3 --parent_id EVT001001 --format json
```

如果只想查看单个选项规则，可再执行：
```bash
python /Users/lu/code/code/py/autofill/scripts/cli/get_field_rules.py event_type_level3 EVT001001001 --format json
```

**4.2 根据用户对话选择**
- 记录选择的三级ID（如 EVT001001002）

### 第5步：选择服务记录模板

**5.1 获取模板列表（传入一级事件类型ID）**
```bash
python /Users/lu/code/code/py/autofill/scripts/cli/get_field.py service_summary --list_templates EVT001 --format json
```

**5.2 获取模板规则（必须执行！用于了解模板要求和变量规则）**
```bash
python /Users/lu/code/code/py/autofill/scripts/cli/get_field_rules.py service_summary --template_id 1 --format json
python /Users/lu/code/code/py/autofill/scripts/cli/get_field_rules.py service_summary --template_id 5 --format json
```

**5.3 根据三级事件类型选择模板**
- 道路救援类 → 选择模板 1（道路救援请求）
- 保养预约类 → 选择模板 2（保养预约）
- 质量问题类 → 根据具体问题选择模板 3/4/9
- 记录选择的模板ID（如 1）

### 第6步：填写服务记录总结

**6.1 获取模板内容（传入模板ID）**
```bash
python /Users/lu/code/code/py/autofill/scripts/cli/get_field.py service_summary --template_id 1 --format json
```

**6.2 从对话提取变量填充模板**
- 必需变量：customer_name, contact_phone, vehicle_system
- 根据事件类型提取其他变量
- 将 `${variable}` 替换为实际值

### 第7步：提交表单

```bash
python /Users/lu/code/code/py/autofill/scripts/cli/submit_form.py '{"event_type_level1":"EVT001","event_type_level2":"EVT001001","event_type_level3":"EVT001001002","service_summary":"填充后的服务记录总结"}' --format json
```

## 完整执行流程（必须严格按此顺序执行）

```bash
# ========== 第1步：获取字段列表 ==========
python /Users/lu/code/code/py/autofill/scripts/cli/get_field.py --format json

# ========== 第2步：填写一级事件类型（并行执行） ==========
python /Users/lu/code/code/py/autofill/scripts/cli/get_field.py event_type_level1 --format json
python /Users/lu/code/code/py/autofill/scripts/cli/get_field_rules.py event_type_level1 --format json

# ========== 第3步：填写二级事件类型（并行执行） ==========
python /Users/lu/code/code/py/autofill/scripts/cli/get_field.py event_type_level2 --parent_id EVT001 --format json
python /Users/lu/code/code/py/autofill/scripts/cli/get_field_rules.py event_type_level2 --parent_id EVT001 --format json

# ========== 第4步：填写三级事件类型（并行执行） ==========
python /Users/lu/code/code/py/autofill/scripts/cli/get_field.py event_type_level3 --parent_id EVT001001 --format json
python /Users/lu/code/code/py/autofill/scripts/cli/get_field_rules.py event_type_level3 --parent_id EVT001001 --format json

# ========== 第5步：选择服务记录模板 ==========
python /Users/lu/code/code/py/autofill/scripts/cli/get_field.py service_summary --list_templates EVT001 --format json
python /Users/lu/code/code/py/autofill/scripts/cli/get_field_rules.py service_summary --template_id 1 --format json

# ========== 第6步：获取模板内容并填写服务记录总结 ==========
python /Users/lu/code/code/py/autofill/scripts/cli/get_field.py service_summary --template_id 1 --format json

# ========== 第7步：提交表单 ==========
python /Users/lu/code/code/py/autofill/scripts/cli/submit_form.py '{"event_type_level1":"EVT001","event_type_level2":"EVT001001","event_type_level3":"EVT001001002","service_summary":"填充后的服务记录总结"}' --format json
```

## 关键说明

1. **必须严格按顺序执行**：第1步 → 第2步 → 第3步 → 第4步 → 第5步 → 第6步 → 第7步
2. **每个步骤都必须调用规则获取**：`get_field.py` 之后**必须**调用 `get_field_rules.py`
3. **级联查询**：二级传一级ID，三级传二级ID
4. **并行执行**：相互独立的命令（如第2步的选项列表与规则）可以在同一次响应中并行调用
5. **所有调用**使用 RunCommand 工具执行
