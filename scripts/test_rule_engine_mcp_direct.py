#!/usr/bin/env python3
"""
直接测试规则引擎 MCP 服务器的脚本
"""
import asyncio
import json

import httpx


async def call_mcp_tool(server_url: str, tool_name: str, arguments: dict) -> dict:
    base_url = server_url.rstrip("/")
    if base_url.endswith("/sse"):
        base_url = base_url[:-4]

    async with httpx.AsyncClient(timeout=60.0) as client:
        pending = {}
        endpoint_future = asyncio.get_running_loop().create_future()

        async def sse_reader():
            async with client.stream("GET", f"{base_url}/sse") as response:
                event_type = None
                async for line in response.aiter_lines():
                    if line.startswith("event: "):
                        event_type = line[7:]
                    elif line.startswith("data: "):
                        data_str = line[6:]
                        if event_type == "endpoint" and not endpoint_future.done():
                            ep = data_str
                            if ep.startswith("/"):
                                ep = f"{base_url}{ep}"
                            endpoint_future.set_result(ep)
                        elif event_type == "message":
                            data = json.loads(data_str)
                            msg_id = data.get("id")
                            if isinstance(msg_id, int) and msg_id in pending:
                                pending[msg_id].set_result(data)
                        event_type = None

        reader_task = asyncio.create_task(sse_reader())

        try:
            endpoint = await asyncio.wait_for(endpoint_future, timeout=10.0)

            init_id = 1
            init_future = asyncio.get_running_loop().create_future()
            pending[init_id] = init_future
            await client.post(
                endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": init_id,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "0.1.0"},
                    },
                },
            )
            await asyncio.wait_for(init_future, timeout=10.0)

            await client.post(
                endpoint,
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )

            call_id = 2
            call_future = asyncio.get_running_loop().create_future()
            pending[call_id] = call_future
            await client.post(
                endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": call_id,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
            )
            response = await asyncio.wait_for(call_future, timeout=30.0)
            return response
        finally:
            reader_task.cancel()
            try:
                await reader_task
            except asyncio.CancelledError:
                pass


async def main():
    server_url = "http://localhost:8002/sse"

    print("=== 1. select 测试 ===")
    resp = await call_mcp_tool(
        server_url,
        "rule_engine_manipulate",
        {"rule_name": "test", "op": "select", "filters": {"name_level1": "EVT001"}},
    )
    result = resp.get("result", {})
    content = result.get("content", [])
    text = next((item.get("text", "") for item in content if item.get("type") == "text"), "")
    print(json.loads(text))

    print("\n=== 2. update 测试 ===")
    resp = await call_mcp_tool(
        server_url,
        "rule_engine_manipulate",
        {
            "rule_name": "test",
            "op": "update",
            "filters": {"name_level1": "EVT001"},
            "update_values": {"summary_level1": "道路救援-已更新"},
        },
    )
    result = resp.get("result", {})
    content = result.get("content", [])
    text = next((item.get("text", "") for item in content if item.get("type") == "text"), "")
    print(json.loads(text))

    print("\n=== 3. select 验证 update ===")
    resp = await call_mcp_tool(
        server_url,
        "rule_engine_manipulate",
        {"rule_name": "test", "op": "select", "filters": {"name_level1": "EVT001"}},
    )
    result = resp.get("result", {})
    content = result.get("content", [])
    text = next((item.get("text", "") for item in content if item.get("type") == "text"), "")
    data = json.loads(text)
    print(data)

    # 恢复数据
    print("\n=== 4. rollback update ===")
    resp = await call_mcp_tool(
        server_url,
        "rule_engine_manipulate",
        {
            "rule_name": "test",
            "op": "update",
            "filters": {"name_level1": "EVT001"},
            "update_values": {"summary_level1": "道路救援"},
        },
    )
    result = resp.get("result", {})
    content = result.get("content", [])
    text = next((item.get("text", "") for item in content if item.get("type") == "text"), "")
    print(json.loads(text))


if __name__ == "__main__":
    asyncio.run(main())
