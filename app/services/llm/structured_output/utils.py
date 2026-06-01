"""
结构化输出服务工具函数
"""
import json
import re
from typing import Any, Dict, List, Optional


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
