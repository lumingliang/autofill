#!/usr/bin/env python3
"""
测试使用流式输出实现结构化输出
"""

import asyncio
import json
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


class CustomerInfo(BaseModel):
    """客户信息"""
    customer_name: str = Field(description="客户姓名")
    vehicle_model: str = Field(description="车辆型号")
    issue: str = Field(description="问题描述")


async def test_streaming_with_structured():
    """测试流式输出 + 结构化解析"""

    # 创建 ChatOpenAI 实例，启用流式输出
    chat_model = ChatOpenAI(
        model="Qwen/QwQ-32B",
        api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
        base_url="https://api-inference.modelscope.cn/v1/",
        temperature=0.7,
        max_tokens=2048,
        streaming=True,  # 启用流式输出
    )

    # 使用 with_structured_output
    structured_llm = chat_model.with_structured_output(CustomerInfo)

    messages = [
        SystemMessage(content="你是一个信息提取助手，请从用户输入中提取客户信息。"),
        HumanMessage(content="客户张三说他的2024款极越01充电到80%就停了。")
    ]

    try:
        print("测试流式 with_structured_output...")
        result = await structured_llm.ainvoke(messages)
        print(f"✅ 成功!")
        print(f"结果: {result}")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()


async def test_streaming_manual_parse():
    """测试流式输出 + 手动解析"""

    # 创建 ChatOpenAI 实例，启用流式输出
    chat_model = ChatOpenAI(
        model="Qwen/QwQ-32B",
        api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
        base_url="https://api-inference.modelscope.cn/v1/",
        temperature=0.7,
        max_tokens=2048,
        streaming=True,
    )

    messages = [
        SystemMessage(content="""你是一个信息提取助手，请从用户输入中提取客户信息。
请严格按照以下JSON格式返回：
{
    "customer_name": "客户姓名",
    "vehicle_model": "车辆型号",
    "issue": "问题描述"
}"""),
        HumanMessage(content="客户张三说他的2024款极越01充电到80%就停了。")
    ]

    try:
        print("\n测试流式输出 + 手动解析...")

        # 使用流式输出
        content = ""
        async for chunk in chat_model.astream(messages):
            if chunk.content:
                content += chunk.content
                print(chunk.content, end="", flush=True)

        print(f"\n\n完整内容: {content}")

        # 尝试解析 JSON
        try:
            data = json.loads(content)
            print(f"✅ JSON 解析成功!")
            print(f"数据: {data}")

            # 验证数据
            customer = CustomerInfo(**data)
            print(f"✅ Pydantic 验证成功!")
            print(f"客户: {customer}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
        except Exception as e:
            print(f"❌ Pydantic 验证失败: {e}")

    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_streaming_with_structured())
    asyncio.run(test_streaming_manual_parse())
