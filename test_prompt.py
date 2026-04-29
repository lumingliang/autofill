#!/usr/bin/env python3
"""
测试 prompt 构建
"""

import json

function_schema = {
    "type": "function",
    "function": {
        "name": "extract_customer_service_info",
        "description": "从客服对话中提取客户信息、车辆问题、预约信息等结构化数据",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_info": {
                    "type": "object",
                    "description": "客户基本信息",
                    "properties": {
                        "name": {"type": "string", "description": "客户姓名"},
                        "phone": {"type": "string", "description": "客户电话（如有）"}
                    },
                    "required": ["name"]
                }
            },
            "required": ["customer_info"]
        }
    }
}

function_def = function_schema.get("function", {})
function_name = function_def.get("name", "function")
function_desc = function_def.get("description", "")
json_schema = json.dumps(function_def.get("parameters", {}), ensure_ascii=False, indent=2)

print("function_name:", repr(function_name))
print("function_desc:", repr(function_desc))
print("json_schema:", repr(json_schema[:200]))

# 构建system prompt，使用字符串拼接避免f-string嵌套问题
system_prompt_parts = [
    f"你是一个智能助手。请根据用户输入，调用函数 `{function_name}` 来生成结构化输出。",
    "",
    f"函数描述：{function_desc}",
    "",
    "请确保输出符合以下JSON Schema要求：",
    "```json",
    json_schema,
    "```",
    "",
    "重要提示：",
    "1. 必须返回有效的JSON格式",
    "2. 不要包含任何解释性文字，只返回JSON",
    "3. 确保所有必填字段都有值",
    "4. 如果某些信息在对话中没有提及，使用null或空数组/对象"
]
system_prompt = "\n".join(system_prompt_parts)

print("\n" + "="*80)
print("system_prompt:")
print(system_prompt[:500])
