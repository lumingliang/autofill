#!/usr/bin/env python3
"""模拟 autofill-form skill，使用 mcp_form_field 和 mcp_rule_engine 完成填单"""
import asyncio
import json

from langchain_mcp_adapters.client import MultiServerMCPClient


async def main():
    client = MultiServerMCPClient({
        "mcp_form_field": {
            "transport": "sse",
            "url": "http://localhost:9999/mcp/form_field/sse",
            "timeout": 30,
        },
        "mcp_rule_engine": {
            "transport": "sse",
            "url": "http://localhost:9999/mcp/rule_engine/sse",
            "timeout": 30,
        },
    })
    await client.get_tools()

    async def call(server: str, tool: str, args: dict):
        async with client.session(server) as session:
            result = await session.call_tool(tool, args)
            text = result.content[0].text if result.content else ""
            return json.loads(text)

    # 第1批：字段列表
    fields = await call("mcp_form_field", "get_form_fields", {})
    print("fields:", json.dumps(fields, ensure_ascii=False, indent=2))

    # 第2批：一级选项 + 规则
    level1_options, level1_rules = await asyncio.gather(
        call("mcp_form_field", "get_field_options", {"field_id": "event_type_level1"}),
        call("mcp_rule_engine", "rule_engine_manipulate", {"rule_name": "test", "op": "select", "filters": {}}),
    )
    print("level1_options:", json.dumps(level1_options, ensure_ascii=False))
    print("level1_rules:", json.dumps(level1_rules, ensure_ascii=False))

    selected_level1 = "EVT001"

    # 第3批：二级选项 + 规则
    level2_options, level2_rules = await asyncio.gather(
        call("mcp_form_field", "get_field_options", {"field_id": "event_type_level2", "parent_id": selected_level1}),
        call("mcp_rule_engine", "rule_engine_manipulate", {"rule_name": "test", "op": "select", "filters": {"name_level1": selected_level1}}),
    )
    print("level2_options:", json.dumps(level2_options, ensure_ascii=False))
    print("level2_rules:", json.dumps(level2_rules, ensure_ascii=False))

    selected_level2 = "EVT001001"

    # 第4批：三级选项 + 规则
    level3_options, level3_rules = await asyncio.gather(
        call("mcp_form_field", "get_field_options", {"field_id": "event_type_level3", "parent_id": selected_level2}),
        call("mcp_rule_engine", "rule_engine_manipulate", {"rule_name": "test", "op": "select", "filters": {"name_level2": selected_level2}}),
    )
    print("level3_options:", json.dumps(level3_options, ensure_ascii=False))
    print("level3_rules:", json.dumps(level3_rules, ensure_ascii=False))

    selected_level3 = "EVT001001001"

    # 第5批：模板
    template = await call("mcp_form_field", "get_template", {"level3_event_type_id": selected_level3})
    print("template:", json.dumps(template, ensure_ascii=False, indent=2))

    # 第6批：提交
    summary = (
        "【客户信息】张三，联系电话：13800000001\n"
        "【车辆信息】车系：SUV，车架号：LSV1234567890，行驶里程：5000公里\n"
        "【故障现象】车辆无法启动\n"
        "【车辆位置】北京市朝阳区\n"
        "【救援需求】标准拖车，期望到达时间：30分钟内\n"
        "【现场情况】是否安全停放：是，是否影响交通：否，车上人数：1人\n"
        "【处理措施】已安排拖车，预计到达时间：15分钟，拖车目的地：4S店\n"
        "【客服备注】客户情绪稳定"
    )
    submit_result = await call("mcp_form_field", "submit_form", {
        "data": {
            "event_type_level1": selected_level1,
            "event_type_level2": selected_level2,
            "event_type_level3": selected_level3,
            "service_summary": summary,
        }
    })
    print("submit_result:", json.dumps(submit_result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
