#!/usr/bin/env python3
"""
测试魔搭社区 API 流式输出
"""

import asyncio
from openai import AsyncOpenAI


async def test_modelscope_stream():
    """测试魔搭社区 API 流式输出"""

    # 创建客户端
    client = AsyncOpenAI(
        api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
        base_url="https://api-inference.modelscope.cn/v1/"
    )

    try:
        print("测试魔搭社区 API 流式输出...")
        print("=" * 80)

        # 流式对话测试
        stream = await client.chat.completions.create(
            model="Qwen/QwQ-32B",
            messages=[
                {"role": "system", "content": "你是一个 helpful assistant."},
                {"role": "user", "content": "你好，请用一句话介绍自己。"}
            ],
            temperature=0.7,
            max_tokens=100,
            stream=True
        )

        print("✅ API 流式调用成功!")
        print("\n回复内容:")

        content = ""
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
                print(chunk.choices[0].delta.content, end="", flush=True)

        print(f"\n\n完整回复: {content}")

    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_modelscope_stream())
