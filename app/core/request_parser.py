"""
通用请求参数解析组件
支持从 query、form-data、json body 中获取参数并合并
"""
import json
from typing import Any, Dict, Optional, Type, TypeVar
from fastapi import Request, Form
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


async def parse_request_params(
    request: Request,
    model_class: Optional[Type[T]] = None
) -> Dict[str, Any]:
    """
    从请求中解析参数，支持以下方式（优先级从高到低）：
    1. Query 参数 (URL 查询字符串)
    2. Form 数据 (multipart/form-data 或 application/x-www-form-urlencoded)
    3. JSON Body (application/json)
    
    所有来源的参数会合并到一个字典中，相同参数名后面的会覆盖前面的
    
    Args:
        request: FastAPI Request 对象
        model_class: 可选的 Pydantic 模型类，用于验证和转换参数
        
    Returns:
        合并后的参数字典
    """
    merged_params: Dict[str, Any] = {}
    
    # 1. 获取 Query 参数
    query_params = dict(request.query_params)
    merged_params.update(query_params)
    
    # 2. 根据 Content-Type 解析 Body
    content_type = request.headers.get("content-type", "").lower()
    
    try:
        if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
            # Form 数据
            form_data = await request.form()
            for key, value in form_data.items():
                # 处理多值字段（如数组）
                if key in merged_params:
                    existing = merged_params[key]
                    if isinstance(existing, list):
                        existing.append(value)
                    else:
                        merged_params[key] = [existing, value]
                else:
                    merged_params[key] = value
                    
        elif "application/json" in content_type:
            # JSON Body
            body = await request.body()
            if body:
                try:
                    json_data = json.loads(body)
                    if isinstance(json_data, dict):
                        merged_params.update(json_data)
                except json.JSONDecodeError:
                    pass
    except Exception:
        # 解析失败时忽略，使用已有的参数
        pass
    
    # 3. 如果提供了模型类，进行验证和转换
    if model_class:
        try:
            # 注意：不再自动转换数字类型，让Pydantic根据模型定义自行处理
            # 这样可以避免将本应作为字符串的数字（如手机号）错误地转换为整数
            validated = model_class(**merged_params)
            return validated.model_dump()
        except Exception as e:
            raise ValueError(f"参数验证失败: {str(e)}")
    
    return merged_params


async def get_merged_params(
    request: Request,
    model_class: Optional[Type[T]] = None
) -> T | Dict[str, Any]:
    """
    获取合并后的参数，如果提供了模型类则返回模型实例
    """
    params = await parse_request_params(request, model_class)
    if model_class:
        return model_class(**params)
    return params
