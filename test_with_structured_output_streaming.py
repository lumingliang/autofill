#!/usr/bin/env python3
"""
测试让 with_structured_output 与流式输出一起工作
"""

import asyncio
import json
from typing import Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.output_parsers import JsonOutputParser


class CustomerInfo(BaseModel):
    """客户信息"""
    customer_name: str = Field(description="客户姓名")
    vehicle_model: str = Field(description="车辆型号")
    issue: str = Field(description="问题描述")


async def test_custom_structured_output():
    """
    测试自定义实现：使用流式输出 + with_structured_output 的逻辑
    """
    
    chat_model = ChatOpenAI(
        model="Qwen/QwQ-32B",
        api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
        base_url="https://api-inference.modelscope.cn/v1/",
        temperature=0.7,
        max_tokens=2048,
        streaming=True,  # 启用流式
    )
    
    messages = [
        SystemMessage(content="你是一个信息提取助手，请从用户输入中提取客户信息。"),
        HumanMessage(content="客户张三说他的2024款极越01充电到80%就停了。")
    ]
    
    # 方法1: 使用 bind_tools + 流式
    print("方法1: bind_tools + 流式")
    try:
        model_with_tools = chat_model.bind_tools(
            [{
                "type": "function",
                "function": {
                    "name": "extract_info",
                    "description": "提取客户信息",
                    "parameters": CustomerInfo.model_json_schema()
                }
            }],
            tool_choice={"type": "function", "function": {"name": "extract_info"}}
        )
        
        # 手动收集流式输出
        content = ""
        tool_calls = []
        async for chunk in model_with_tools.astream(messages):
            print(f"Chunk: {chunk}")
            if chunk.content:
                content += chunk.content
            if chunk.tool_calls:
                tool_calls.extend(chunk.tool_calls)
        
        print(f"\nContent: {content}")
        print(f"Tool calls: {tool_calls}")
        
        # 如果有工具调用，解析参数
        if tool_calls:
            args = json.loads(tool_calls[0]['args'])
            result = CustomerInfo(**args)
            print(f"✅ 成功: {result}")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 方法2: 使用 with_structured_output 但强制使用流式
    print("\n方法2: with_structured_output + 自定义解析")
    try:
        # 创建模型，不启用流式（让 with_structured_output 处理）
        chat_model_non_stream = ChatOpenAI(
            model="Qwen/QwQ-32B",
            api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
            base_url="https://api-inference.modelscope.cn/v1/",
            temperature=0.7,
            max_tokens=2048,
            # streaming=False,  # 不启用流式
        )
        
        # 使用 with_structured_output
        structured_llm = chat_model_non_stream.with_structured_output(CustomerInfo)
        
        # 调用 - 这会失败，因为魔搭API非流式返回null
        result = await structured_llm.ainvoke(messages)
        print(f"✅ 成功: {result}")
    except Exception as e:
        print(f"❌ 失败: {e}")


async def test_with_structured_output_patch():
    """
    测试：通过monkey patch让 with_structured_output 使用流式
    """
    from langchain_openai.chat_models.base import ChatOpenAI as BaseChatOpenAI
    from langchain_core.language_models.chat_models import BaseChatModel
    
    # 保存原始方法
    original_agenerate = BaseChatOpenAI._agenerate
    
    # 创建一个使用流式的自定义实现
    async def patched_agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        # 如果是魔搭社区，使用流式
        if "modelscope" in str(self.base_url).lower() or "modelscope" in str(self.model_name).lower():
            print("使用流式输出...")
            # 使用流式生成
            chunks = []
            async for chunk in self._astream(messages, stop=stop, run_manager=run_manager, **kwargs):
                chunks.append(chunk)
            # 合并chunks
            from langchain_core.messages import AIMessage
            content = "".join([c.text for c in chunks if hasattr(c, 'text')])
            message = AIMessage(content=content)
            from langchain_core.outputs import ChatResult, ChatGeneration
            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])
        else:
            return await original_agenerate(self, messages, stop, run_manager, **kwargs)
    
    # 应用patch
    BaseChatOpenAI._agenerate = patched_agenerate
    
    try:
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
        
        print("\n方法3: Monkey patch with_structured_output")
        structured_llm = chat_model.with_structured_output(CustomerInfo)
        result = await structured_llm.ainvoke(messages)
        print(f"✅ 成功: {result}")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 恢复原始方法
        BaseChatOpenAI._agenerate = original_agenerate


if __name__ == "__main__":
    asyncio.run(test_custom_structured_output())
    asyncio.run(test_with_structured_output_patch())
