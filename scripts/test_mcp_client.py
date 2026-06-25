#!/usr/bin/env python3
"""测试 MultiServerMCPClient 连接规则引擎 MCP（共享 9999 端口）"""
import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient


async def main():
    connections = {
        "mcp_rule_engine": {
            "transport": "sse",
            "url": "http://localhost:9999/mcp/rule_engine/sse",
            "timeout": 60,
        }
    }
    client = MultiServerMCPClient(connections)
    tools = await client.get_tools()
    print("Available tools:")
    for tool in tools:
        print(f"  - {tool.name}")
    if tools:
        result = await tools[0].ainvoke({
            "rule_name": "test",
            "op": "select",
            "filters": {"name_level1": "EVT001"},
        })
        print("Result:", result)


if __name__ == "__main__":
    asyncio.run(main())
