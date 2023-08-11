"""
Autofill 服务全局常量
"""

# 默认的字段组提示词模板
DEFAULT_PROMPT_TEMPLATE_BASE = """你是一个智能填单助手。请根据输入内容，提取指定字段的信息。

需要提取的字段：
{fields_instructions}

请严格按照字段要求提取信息，并以JSON格式返回结果。"""
