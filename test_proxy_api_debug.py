#!/usr/bin/env python3
"""
直接调用 LLM 代理接口测试 - 调试版本
"""

import asyncio
import json
import httpx


# API 配置
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
BASE_URL = "http://localhost:9999/api"

# 简化的测试数据
request_data = {
    "query": "客户张三说他的2024款极越01充电到80%就停了，车牌粤A12345D，预约了明天下午14:00去广州天河中路服务中心检查。",
    "function_schema": {
        "type": "function",
        "function": {
            "name": "extract_info",
            "description": "提取客户信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "客户姓名"},
                    "vehicle_model": {"type": "string", "description": "车辆型号"},
                    "issue": {"type": "string", "description": "问题描述"}
                },
                "required": ["customer_name"]
            }
        }
    },
    "app_key": API_KEY
}


async def test_proxy_api():
    """测试代理接口"""
    print("=" * 80)
    print("测试代理接口")
    print("=" * 80)

    print(f"\n请求数据:")
    print(json.dumps(request_data, ensure_ascii=False, indent=2))

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/llm/proxy",
                json=request_data,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                timeout=120.0
            )

            print(f"\n状态码: {response.status_code}")
            print(f"\n原始响应内容:")
            print(response.text)

            try:
                result = response.json()
                print(f"\n解析后的响应:")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            except:
                print("\n⚠️ 响应不是有效的 JSON")

        except Exception as e:
            print(f"\n❌ 请求异常: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_proxy_api())
