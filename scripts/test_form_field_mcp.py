#!/usr/bin/env python3
"""测试 form_field MCP"""
import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient


async def main():
    client = MultiServerMCPClient({
        "mcp_form_field": {
            "transport": "sse",
            "url": "http://localhost:9999/mcp/form_field/sse",
            "timeout": 30,
        }
    })
    tools = await client.get_tools()
    print("tools:", [t.name for t in tools])

    async with client.session("mcp_form_field") as session:
        for call in [
            ("get_form_fields", {}),
            ("get_field_options", {"field_id": "event_type_level1"}),
            ("get_field_options", {"field_id": "event_type_level2", "parent_id": "EVT001"}),
            ("get_field_options", {"field_id": "event_type_level3", "parent_id": "EVT001001"}),
            ("get_template", {"level3_event_type_id": "EVT001001001"}),
        ]:
            result = await session.call_tool(call[0], call[1])
            print(f"\n--- {call[0]} ---")
            print(result)


if __name__ == "__main__":
    asyncio.run(main())
