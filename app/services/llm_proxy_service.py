"""
LLM 代理服务
基于 LangChain + LiteLLM 实现结构化输出
"""
import json
import logging
from typing import Any, Dict, Optional, Type

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, create_model

from app.core.redis import redis_client
from app.models.llm_config import LLMConfig

logger = logging.getLogger(__name__)


class LLMProxyService:
    """LLM代理服务"""

    def __init__(self):
        self._chat_models = {}

    def _get_chat_model(self, config: LLMConfig):
        """
        获取或创建ChatModel实例
        使用LiteLLM作为统一的模型适配层
        """
        cache_key = f"{config.model_provider}:{config.model_name}:{config.id}"

        if cache_key not in self._chat_models:
            try:
                from langchain_community.chat_models import ChatLiteLLM

                # 构建LiteLLM配置
                # 对于OpenAI兼容的API（如魔搭社区），使用 openai/ 前缀
                if config.model_provider == "modelscope":
                    # 魔搭社区使用 OpenAI 兼容格式
                    model_string = f"openai/{config.model_name}"
                else:
                    model_string = f"{config.model_provider}/{config.model_name}"

                model_kwargs = {
                    "model": model_string,
                    "api_key": config.api_key,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                    "top_p": config.top_p,
                }

                # 如果有自定义API base
                if config.api_base:
                    model_kwargs["api_base"] = config.api_base

                chat_model = ChatLiteLLM(**model_kwargs)
                self._chat_models[cache_key] = chat_model

            except Exception as e:
                logger.error(f"Failed to create chat model: {e}")
                raise

        return self._chat_models[cache_key]

    def _create_pydantic_model(self, function_schema: dict) -> Type[BaseModel]:
        """
        根据函数schema动态创建Pydantic模型
        """
        function_def = function_schema.get("function", {})
        schema_name = function_def.get("name", "DynamicResponse")
        parameters = function_def.get("parameters", {})
        properties = parameters.get("properties", {})
        required = parameters.get("required", [])

        # 构建字段定义
        fields = {}
        for prop_name, prop_def in properties.items():
            field_type = self._get_field_type(prop_def)
            if prop_name in required:
                fields[prop_name] = (field_type, ...)
            else:
                fields[prop_name] = (Optional[field_type], None)

        # 创建动态模型
        DynamicModel = create_model(schema_name, **fields)
        return DynamicModel

    def _get_field_type(self, prop_def: dict) -> type:
        """
        根据schema定义获取Python类型
        """
        prop_type = prop_def.get("type", "string")

        if prop_type == "string":
            # 检查是否有enum
            if "enum" in prop_def:
                from enum import Enum

                enum_name = f"Enum_{id(prop_def)}"
                enum_values = {str(v): v for v in prop_def["enum"]}
                return Enum(enum_name, enum_values)
            return str
        elif prop_type == "integer":
            return int
        elif prop_type == "number":
            return float
        elif prop_type == "boolean":
            return bool
        elif prop_type == "array":
            item_type = self._get_field_type(prop_def.get("items", {}))
            return list[item_type]
        elif prop_type == "object":
            return dict
        else:
            return str

    async def invoke_structured(
        self,
        query: str,
        function_schema: dict,
        config: LLMConfig,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        调用LLM并返回结构化输出

        Args:
            query: 用户输入或上下文
            function_schema: 函数调用参数schema
            config: LLM配置
            context: 额外的上下文信息

        Returns:
            结构化输出结果
        """
        try:
            # 获取chat model
            chat_model = self._get_chat_model(config)

            # 创建动态Pydantic模型
            output_model = self._create_pydantic_model(function_schema)

            # 构建prompt
            function_def = function_schema.get("function", {})
            function_name = function_def.get("name", "function")
            function_desc = function_def.get("description", "")

            # 获取JSON schema用于提示
            json_schema = json.dumps(function_def.get("parameters", {}), ensure_ascii=False, indent=2)

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

            if context:
                system_prompt += "\n\n额外上下文：\n" + context

            # 使用字符串拼接避免f-string问题
            human_prompt = "用户输入：" + query + "\n\n请根据上述输入，生成符合要求的JSON输出。"

            # 使用消息对象直接构建，避免模板解析问题
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ]

            # 对于OpenAI兼容的API（如魔搭社区），使用ChatOpenAI的流式输出+工具调用
            if config.model_provider in ["modelscope"]:
                from langchain_openai import ChatOpenAI

                # 创建ChatOpenAI实例，启用流式输出
                chat_model = ChatOpenAI(
                    model=config.model_name,
                    api_key=config.api_key,
                    base_url=config.api_base,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    top_p=config.top_p,
                    streaming=True,
                )

                # 将function_schema转换为tool格式
                tools = [function_schema]

                # 使用流式输出+工具调用
                content = ""
                tool_calls_data = {}

                async for chunk in chat_model.astream(messages, tools=tools, tool_choice="auto"):
                    if chunk.content:
                        content += chunk.content
                    # 收集工具调用参数
                    if chunk.tool_calls:
                        for tc in chunk.tool_calls:
                            index = tc.get('index', 0)
                            if index not in tool_calls_data:
                                tool_calls_data[index] = {'id': tc.get('id', ''), 'name': tc.get('name', ''), 'arguments': ''}
                            if tc.get('function', {}).get('arguments'):
                                tool_calls_data[index]['arguments'] += tc['function']['arguments']

                # 如果有工具调用，解析参数
                if tool_calls_data:
                    # 获取第一个工具调用的参数
                    first_tool = tool_calls_data[0]
                    args_str = first_tool['arguments']

                    # 解析JSON参数
                    try:
                        result = json.loads(args_str)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse tool call arguments: {e}, args: {args_str}")
                        raise ValueError(f"无法解析工具调用参数: {args_str}")

                    # 使用Pydantic模型验证结果
                    validated_result = output_model(**result)
                    return validated_result.model_dump()
                else:
                    # 没有工具调用，尝试从content中解析JSON
                    try:
                        result = json.loads(content)
                    except json.JSONDecodeError:
                        # 尝试从markdown代码块中提取JSON
                        import re
                        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
                        if json_match:
                            result = json.loads(json_match.group(1))
                        else:
                            # 尝试匹配第一个JSON对象
                            json_match = re.search(r'\{.*\}', content, re.DOTALL)
                            if json_match:
                                result = json.loads(json_match.group())
                            else:
                                raise ValueError(f"无法从响应中解析JSON: {content}")

                    # 使用Pydantic模型验证结果
                    validated_result = output_model(**result)
                    return validated_result.model_dump()
            else:
                # 使用with_structured_output
                structured_llm = chat_model.with_structured_output(output_model)

                # 调用
                result = await structured_llm.ainvoke(messages)

                # 转换为字典
                if isinstance(result, BaseModel):
                    return result.model_dump()
                elif isinstance(result, dict):
                    return result
                else:
                    return {"result": str(result)}

        except Exception as e:
            logger.error(f"LLM invoke failed: {e}")
            raise

    async def invoke_with_fallback(
        self,
        query: str,
        function_schema: dict,
        app_key: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        带fallback的LLM调用
        先尝试使用租户配置，失败时使用全局配置
        """
        from app.controllers.llm_config import llm_config_controller

        # 获取配置
        config = await llm_config_controller.get_config_by_app_key(app_key)

        if not config:
            # 尝试获取全局默认配置
            config = await llm_config_controller.get_default_config(None)

        if not config:
            return {
                "success": False,
                "error": "未找到可用的LLM配置，请联系管理员配置",
                "data": None,
            }

        try:
            result = await self.invoke_structured(
                query=query,
                function_schema=function_schema,
                config=config,
                context=context,
            )
            return {"success": True, "data": result, "error": None}
        except Exception as e:
            logger.error(f"LLM invoke with config {config.name} failed: {e}")

            # 如果是租户配置失败，尝试全局配置
            if config.tenant_id is not None:
                global_config = await llm_config_controller.get_default_config(None)
                if global_config and global_config.id != config.id:
                    try:
                        result = await self.invoke_structured(
                            query=query,
                            function_schema=function_schema,
                            config=global_config,
                            context=context,
                        )
                        return {"success": True, "data": result, "error": None}
                    except Exception as e2:
                        logger.error(f"Fallback to global config failed: {e2}")

            return {"success": False, "error": str(e), "data": None}


# 全局服务实例
llm_proxy_service = LLMProxyService()
