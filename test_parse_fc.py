#!/usr/bin/env python3
"""测试 _parse_text_function_call 方法"""
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.services.llm.structured_output import StructuredOutputService
from app.models.llm_config import LLMConfig

# 模拟配置
config = LLMConfig(
    name="test",
    model_provider="openai",
    litellm_params={"model": "test-model"}
)

# 创建服务实例
service = StructuredOutputService(config)

# 测试工具
tools = [{
    "type": "function",
    "function": {
        "name": "call_api",
        "description": "调用 API",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "city": {"type": "string"}
            }
        }
    }
}]

# 测试内容
test_contents = [
    '''根据用户查询"重庆的比亚迪门店"，我将调用API搜索重庆地区的比亚迪门店信息：

```json
▶︎call_api
{
  "name": "比亚迪",
  "city": "重庆",
  "address": "",
  "app_key": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
  "limit": 5,
  "reason": "用户明确要求查询重庆的比亚迪门店，故填充name为'比亚迪'，city为'重庆'，address留空扩大搜索范围"
}
```''',
    '''▶︎call_api
{
  "name": "test",
  "city": "北京"
}''',
    '''```json
{
  "name": "test",
  "city": "上海"
}
```''',
    '普通文本，没有 function call'
]

print("=" * 80)
print("测试 _parse_text_function_call 方法")
print("=" * 80)

for i, content in enumerate(test_contents, 1):
    print(f"\n测试 {i}:")
    print("-" * 80)
    print(f"输入: {content[:100]}...")
    
    result = service._parse_text_function_call(content, tools)
    
    if result:
        print(f"✅ 解析成功: {result}")
    else:
        print(f"❌ 未解析到 function call")
