#!/usr/bin/env python3
"""
测试 LangChain 的 with_structured_output 与魔搭社区 API
"""

import asyncio
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


class CustomerInfo(BaseModel):
    """客户信息"""
    customer_name: str = Field(description="客户姓名")
    vehicle_model: str = Field(description="车辆型号")
    issue: str = Field(description="问题描述")


async def test_with_structured_output():
    """测试 with_structured_output"""

    # 创建 ChatOpenAI 实例
    chat_model = ChatOpenAI(
        model="Qwen/QwQ-32B",
        api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
        base_url="https://api-inference.modelscope.cn/v1/",
        temperature=0.7,
        max_tokens=2048,
    )

    # 使用 with_structured_output
    structured_llm = chat_model.with_structured_output(CustomerInfo)

    messages = [
        SystemMessage(content="你是一个信息提取助手，请从用户输入中提取客户信息。"),
        HumanMessage(content="客户张三说他的2024款极越01充电到80%就停了。")
    ]

    try:
        print("测试 with_structured_output...")
        result = await structured_llm.ainvoke(messages)
        print(f"✅ 成功!")
        print(f"结果: {result}")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()


async def test_direct_invoke():
    """测试直接调用"""

    # 创建 ChatOpenAI 实例
    chat_model = ChatOpenAI(
        model="Qwen/QwQ-32B",
        api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
        base_url="https://api-inference.modelscope.cn/v1/",
        temperature=0.7,
        max_tokens=2048,
    )

    messages = [
        SystemMessage(content="你是一个信息提取助手，请从用户输入中提取客户信息，以JSON格式返回。"),
        HumanMessage(content="客户张三说他的2024款极越01充电到80%就停了。")
    ]

    try:
        print("\n测试直接调用...")
        result = await chat_model.ainvoke(messages)
        print(f"✅ 成功!")
        print(f"结果: {result}")
        print(f"内容: {result.content}")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_with_structured_output())
    asyncio.run(test_direct_invoke())
