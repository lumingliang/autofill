---
name: "autofill-form"
description: "400汽车客服工单自动填单。按级联顺序选择事件类型、获取模板、填写服务记录总结并提交。Invoke when user needs to fill a 400 car customer service work order."
---

# 400 汽车客服工单自动填单

## 目标

帮助用户完成 400 汽车客服工单填写，最终必须调用 `submit_form` 提交并返回工单号。

## 字段 ID

- `event_type_level1`：一级事件类型
- `event_type_level2`：二级事件类型
- `event_type_level3`：三级事件类型
- `service_summary`：服务记录总结

## 完整执行流程（必须按顺序，不能跳过，不能提前结束）

```
第1批：一级事件类型选项 + 一级规则
   ↓
选择一级 ID（匹配用户描述）
   ↓
第2批：二级事件类型选项 + 二级规则
   ↓
选择二级 ID（匹配用户描述）
   ↓
第3批：三级事件类型选项 + 三级规则
   ↓
选择三级 ID（匹配用户描述）
   ↓
第4批：获取服务记录模板
   ↓
第5批：提交表单（必须执行）
   ↓
返回 form_id
```

**重要：必须完整执行到第 5 批并拿到 form_id，才能回复用户。不得在拿到模板后停止。**

## 行为守则（必须严格遵守）

1. **全程禁止输出解释性文字**：在选择每一级事件类型后，不要输出“我将选择...”等说明，直接继续下一批工具调用。
2. **禁止重复查询同一级别**：每个级别只需调用一次 `get_field_options` 和一次 `rule_engine_manipulate`。
3. **拿到三级 ID 后必须立即获取模板**，拿到模板后必须立即生成 `service_summary` 并调用 `submit_form`。
4. **只有 `submit_form` 返回成功（含 form_id）后，才能停止工具调用并回复用户。**
5. **如果某一级没有完美匹配用户描述的选项，选择最接近的一个并继续。**

## 执行批次

同批次内的两个调用可以并行；不同批次必须等待结果后再继续。

### 第1批：一级事件类型

```json
{"server_name": "mcp_form_field", "tool_name": "get_field_options", "args": {"field_id": "event_type_level1"}}
{"server_name": "mcp_rule_engine", "tool_name": "rule_engine_manipulate", "args": {"rule_name": "400汽车客服工单事件类型", "op": "select", "filters": {}, "fields": ["level1_label", "level1_instruction"]}}
```

选择一级 ID：将用户描述与 `level1_label` 匹配，选择最接近的 `value`（如 EVT001、EVT003 等）。

### 第2批：二级事件类型（依赖一级 ID）

```json
{"server_name": "mcp_form_field", "tool_name": "get_field_options", "args": {"field_id": "event_type_level2", "parent_id": "<一级ID>"}}
{"server_name": "mcp_rule_engine", "tool_name": "rule_engine_manipulate", "args": {"rule_name": "400汽车客服工单事件类型", "op": "select", "filters": {"level1_label": "<一级标签>"}, "fields": ["level2_label", "level2_instruction"]}}
```

选择二级 ID：将用户描述与 `level2_label` 匹配，选择最接近的 `value`。

### 第3批：三级事件类型（依赖二级 ID）

```json
{"server_name": "mcp_form_field", "tool_name": "get_field_options", "args": {"field_id": "event_type_level3", "parent_id": "<二级ID>"}}
{"server_name": "mcp_rule_engine", "tool_name": "rule_engine_manipulate", "args": {"rule_name": "400汽车客服工单事件类型", "op": "select", "filters": {"level1_label": "<一级标签>", "level2_label": "<二级标签>"}, "fields": ["level3_label", "level3_instruction"]}}
```

选择三级 ID：将用户描述与 `level3_label` 匹配，选择最接近的 `value`。

### 第4批：服务记录模板（依赖三级 ID）

```json
{"server_name": "mcp_form_field", "tool_name": "get_template", "args": {"level3_event_type_id": "<三级ID>"}}
```

### 第5批：提交表单（必须执行）

```json
{"server_name": "mcp_form_field", "tool_name": "submit_form", "args": {"data": {"event_type_level1": "<一级ID>", "event_type_level2": "<二级ID>", "event_type_level3": "<三级ID>", "service_summary": "<填充后的服务记录总结>"}}}
```

## service_summary 生成要求

基于第4批返回的模板内容，填充以下信息：

- 客户信息：姓名、联系电话
- 车辆信息：车型、车牌/车架号、行驶里程等
- 问题描述：故障现象、发生位置等
- 处理措施：已安排/建议的处理方式
- 客服备注：客户情绪、特殊说明等

如果用户未提供某项信息，基于模板字段自动生成合理内容。

## 关键约束

- 必须按批次顺序执行，不能跨批次并行。
- 选择事件类型时结合 `mcp_form_field` 返回的选项和 `mcp_rule_engine` 返回的填写说明。
- **拿到模板后必须继续生成 `service_summary` 并调用 `submit_form`。**
- **只有 `submit_form` 返回成功（含 form_id）后，才能停止工具调用并回复用户。**
