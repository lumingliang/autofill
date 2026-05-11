"""
智能填单服务模块
提供 AI 填单和 Prompt 模板组装功能
"""
from .ai_fill_service import AIFillService, get_ai_fill_service
from .prompt_service import (
    build_fields_instructions,
    build_function_schema,
    assemble_output_prompts,
    get_field_group_with_fields,
    get_field_group_by_code_with_fields,
)

__all__ = [
    "AIFillService",
    "get_ai_fill_service",
    "build_fields_instructions",
    "build_function_schema",
    "assemble_output_prompts",
    "get_field_group_with_fields",
    "get_field_group_by_code_with_fields",
]