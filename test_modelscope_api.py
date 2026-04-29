#!/usr/bin/env python3
"""
测试魔搭社区 API 是否可用
"""

import asyncio
from openai import AsyncOpenAI
import json


async def test_modelscope_api():
    """测试魔搭社区 API"""

    # 创建客户端
    client = AsyncOpenAI(
        api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
        base_url="https://api-inference.modelscope.cn/v1/"
    )

    try:
        print("测试魔搭社区 API...")
        print("=" * 80)

        # 简单对话测试
        response = await client.chat.completions.create(
            model="Qwen/QwQ-32B",
            messages=[
                {"role": "system", "content": "你是一个 helpful assistant."},
                {"role": "user", "content": "你好，请用一句话介绍自己。"}
            ],
            temperature=0.7,
            max_tokens=100
        )

        print("✅ API 调用成功!")
        print(f"\n完整响应:")
        print(json.dumps(response.model_dump(), ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_modelscope_api())
