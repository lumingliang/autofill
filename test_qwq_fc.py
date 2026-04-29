#!/usr/bin/env python3
"""
测试 QwQ-32B 的 Function Calling 能力
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


async def test_fc_with_tools():
    """测试使用 tools 参数进行函数调用"""
    
    chat_model = ChatOpenAI(
        model="Qwen/QwQ-32B",
        api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
        base_url="https://api-inference.modelscope.cn/v1/",
        temperature=0.7,
        max_tokens=2048,
    )
    
    # 定义工具
    tools = [{
        "type": "function",
        "function": {
            "name": "extract_customer_info",
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
    }]
    
    messages = [
        SystemMessage(content="你是一个信息提取助手，请从用户输入中提取客户信息。"),
        HumanMessage(content="客户张三说他的2024款极越01充电到80%就停了。")
    ]
    
    try:
        print("测试使用 tools 参数...")
        # 绑定工具
        model_with_tools = chat_model.bind_tools(tools)
        result = await model_with_tools.ainvoke(messages)
        
        print(f"✅ 成功!")
        print(f"结果: {result}")
        print(f"工具调用: {result.tool_calls}")
        
        if result.tool_calls:
            for call in result.tool_calls:
                print(f"  函数名: {call['name']}")
                print(f"  参数: {call['args']}")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()


async def test_fc_with_json_mode():
    """测试使用 JSON 模式"""
    
    chat_model = ChatOpenAI(
        model="Qwen/QwQ-32B",
        api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
        base_url="https://api-inference.modelscope.cn/v1/",
        temperature=0.7,
        max_tokens=2048,
        model_kwargs={"response_format": {"type": "json_object"}}  # JSON 模式
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
        print("\n测试使用 JSON 模式...")
        result = await chat_model.ainvoke(messages)
        
        print(f"✅ 成功!")
        print(f"结果: {result}")
        print(f"内容: {result.content}")
        
        # 解析 JSON
        data = json.loads(result.content)
        print(f"解析后的数据: {data}")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()


async def test_fc_with_structured_output_and_tools():
    """测试 with_structured_output 配合工具"""
    
    chat_model = ChatOpenAI(
        model="Qwen/QwQ-32B",
        api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
        base_url="https://api-inference.modelscope.cn/v1/",
        temperature=0.7,
        max_tokens=2048,
    )
    
    messages = [
        SystemMessage(content="你是一个信息提取助手，请从用户输入中提取客户信息。"),
        HumanMessage(content="客户张三说他的2024款极越01充电到80%就停了。")
    ]
    
    try:
        print("\n测试 with_structured_output (include_raw=True)...")
        structured_llm = chat_model.with_structured_output(
            CustomerInfo,
            include_raw=True  # 包含原始响应
        )
        result = await structured_llm.ainvoke(messages)
        
        print(f"✅ 成功!")
        print(f"结果: {result}")
        print(f"解析后的数据: {result['parsed']}")
        print(f"原始响应: {result['raw']}")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_fc_with_tools())
    asyncio.run(test_fc_with_json_mode())
    asyncio.run(test_fc_with_structured_output_and_tools())
