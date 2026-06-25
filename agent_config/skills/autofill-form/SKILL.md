---
name: "autofill-form"
description: "400汽车客服工单自动填单。按级联顺序选择事件类型、获取模板、填写服务记录总结并提交。Invoke when user needs to fill a 400 car customer service work order."
---

# 400 汽车客服工单自动填单

按顺序完成：一级事件类型 → 二级事件类型 → 三级事件类型 → 获取模板 → 填写服务记录总结 → 提交。

字段 ID：
- `event_type_level1`：一级事件类型
- `event_type_level2`：二级事件类型
- `event_type_level3`：三级事件类型
- `service_summary`：服务记录总结

## 执行批次

同批次可并行调用，不同批次必须等待结果后再继续。

**第1批：一级事件类型**
```json
{"server_name": "mcp_form_field", "tool_name": "get_field_options", "args": {"field_id": "event_type_level1"}}
{"server_name": "mcp_rule_engine", "tool_name": "rule_engine_manipulate", "args": {"rule_name": "400汽车客服工单事件类型", "op": "select", "filters": {}, "fields": ["level1_label", "level1_instruction"]}}
```
选择一级 ID（如 EVT001）。

**第2批：二级事件类型（依赖一级）**
```json
{"server_name": "mcp_form_field", "tool_name": "get_field_options", "args": {"field_id": "event_type_level2", "parent_id": "EVT001"}}
{"server_name": "mcp_rule_engine", "tool_name": "rule_engine_manipulate", "args": {"rule_name": "400汽车客服工单事件类型", "op": "select", "filters": {"level1_label": "道路救援"}, "fields": ["level2_label", "level2_instruction"]}}
```
选择二级 ID（如 EVT001001）。

**第3批：三级事件类型（依赖二级）**
```json
{"server_name": "mcp_form_field", "tool_name": "get_field_options", "args": {"field_id": "event_type_level3", "parent_id": "EVT001001"}}
{"server_name": "mcp_rule_engine", "tool_name": "rule_engine_manipulate", "args": {"rule_name": "400汽车客服工单事件类型", "op": "select", "filters": {"level1_label": "道路救援", "level2_label": "拖车服务"}, "fields": ["level3_label", "level3_instruction"]}}
```
选择三级 ID（如 EVT001001002）。

**第4批：服务记录模板（依赖三级）**
```json
{"server_name": "mcp_form_field", "tool_name": "get_template", "args": {"level3_event_type_id": "EVT001001002"}}
```

**第5批：提交表单**
```json
{"server_name": "mcp_form_field", "tool_name": "submit_form", "args": {"data": {"event_type_level1": "EVT001", "event_type_level2": "EVT001001", "event_type_level3": "EVT001001002", "service_summary": "填充后的服务记录总结"}}}
```

## 关键约束

- 必须按批次顺序执行，不能跨批次并行。
- 选择事件类型时结合 `mcp_form_field` 返回的选项和 `mcp_rule_engine` 返回的填写说明。
- `service_summary` 基于模板内容生成，包含客户信息、车辆信息、问题描述、处理措施和客服备注。
