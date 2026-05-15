"""
结构化输出服务工具函数
"""
import json
import re
from typing import Any, Dict, List, Optional, Type

from pydantic import Field, create_model


def parse_text_function_call(content: str, tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    解析文本格式的 function call

    某些模型（如 DeepSeek）可能返回文本格式的 function call，例如：
    ▶︎call_api
    {
      "name": "比亚迪",
      "city": "重庆",
      ...
    }

    Args:
        content: LLM 返回的文本内容
        tools: 工具定义列表

    Returns:
        解析后的参数字典，如果不是 function call 格式则返回 None
    """
    if not content or not tools:
        return None

    # 获取第一个工具的名称
    first_tool = tools[0]
    if "function" in first_tool:
        tool_name = first_tool.get("function", {}).get("name", "")
    else:
        tool_name = first_tool.get("name", "")

    # 匹配 function call 标记和 JSON 内容
    # 支持格式: ▶︎call_api { ... } 或 ```json\n{...}\n```
    patterns = [
        # 匹配 ▶︎call_api {...} 格式
        rf'▶︎\s*{re.escape(tool_name)}\s*\n?({{.*?}})',
        rf'▶︎\s*call_\w+\s*\n?({{.*?}})',
        # 匹配 ```json\n{...}\n``` 格式
        r'```json\s*\n(.*?)\n```',
        # 匹配 ```\n{...}\n``` 格式
        r'```\s*\n(.*?)\n```',
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            try:
                parsed = json.loads(json_str)
                # 验证解析结果是否包含工具的参数
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

    return None


def create_dynamic_model(tools: List[Dict[str, Any]]) -> Type:
    """
    根据 tools 定义创建动态 Pydantic 模型

    合并所有工具的参数，所有字段都设为可选（Optional），
    以支持多工具场景下不同工具返回不同参数的情况。
    """
    if not tools:
        raise ValueError("tools 不能为空")

    # 收集所有工具的参数
    all_properties = {}
    for tool in tools:
        # 支持两种格式：OpenAI 格式（有 function 字段）和简化格式（直接有 parameters）
        if "function" in tool:
            function_def = tool.get("function", {})
        else:
            function_def = tool
        parameters = function_def.get("parameters", {})
        properties = parameters.get("properties", {})
        all_properties.update(properties)

    # 构建字段定义 - 所有字段都设为 Optional，以支持多工具场景
    fields = {}
    for field_name, field_schema in all_properties.items():
        from typing import Optional
        field_type = json_schema_to_python_type(field_schema)
        field_desc = field_schema.get("description", "")
        # 所有字段都设为 Optional，默认值为 None
        fields[field_name] = (Optional[field_type], Field(default=None, description=field_desc))

    # 创建动态模型
    model_name = "DynamicOutput"
    return create_model(model_name, **fields)


def json_schema_to_python_type(schema: Dict[str, Any]) -> Type:
    """将 JSON Schema 类型转换为 Python 类型"""
    from typing import Any, Dict, List, Literal

    json_type = schema.get("type", "string")

    if json_type == "string":
        enum = schema.get("enum")
        if enum:
            return Literal[tuple(enum)]
        return str
    elif json_type == "integer":
        return int
    elif json_type == "number":
        return float
    elif json_type == "boolean":
        return bool
    elif json_type == "array":
        items = schema.get("items", {})
        item_type = json_schema_to_python_type(items)
        return List[item_type]
    elif json_type == "object":
        return Dict[str, Any]
    else:
        return str


def build_tools_description(tools: List[Dict[str, Any]]) -> str:
    """构建工具描述文本"""
    descriptions = []
    for tool in tools:
        if "function" in tool:
            func = tool["function"]
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            params = func.get("parameters", {})
            param_desc = ""
            if "properties" in params:
                for prop_name, prop_info in params["properties"].items():
                    prop_desc = prop_info.get("description", "")
                    param_desc += f"\n      - {prop_name}: {prop_desc}"
            descriptions.append(f"  - {name}: {desc}{param_desc}")
    return "\n".join(descriptions)
