#!/usr/bin/env python3
"""直接测试 agent 的 run_mcp 工具"""
import asyncio

from app.services.agent.tools.mcp import execute_run_mcp


async def main():
    result = await execute_run_mcp(
        "mcp_rule_engine",
        "rule_engine_manipulate",
        {"rule_name": "test", "op": "select", "filters": {"name_level1": "EVT001"}},
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
