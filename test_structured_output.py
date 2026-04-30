import asyncio
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

class PersonInfo(BaseModel):
    """人员信息"""
    name: str = Field(description="姓名")
    age: int = Field(description="年龄")
    email: str = Field(description="邮箱")

async def test_structured_output():
    """测试结构化输出"""
    # 初始化模型
    llm = ChatOpenAI(
        model="LLM-Research/c4ai-command-r-plus-08-2024",
        api_key="ms-919b1188-52f3-4654-b3bd-c46ab3bcf738",
        base_url="https://api-inference.modelscope.cn/v1/",
        temperature=0.1
    )
    
    # 测试 with_structured_output 方法
    print("Testing with_structured_output method...")
    try:
        structured_llm = llm.with_structured_output(PersonInfo)
        result = await structured_llm.ainvoke(
            "请提取以下信息：姓名张三，年龄25岁，邮箱zhangsan@example.com"
        )
        print(f"Result: {result}")
        print(f"Name: {result.name}")
        print(f"Age: {result.age}")
        print(f"Email: {result.email}")
        print("✓ with_structured_output method works!")
    except Exception as e:
        print(f"✗ with_structured_output failed: {e}")

if __name__ == '__main__':
    asyncio.run(test_structured_output())
