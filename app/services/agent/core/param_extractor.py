"""
参数提取器 - 复用 llm_proxy 的 FC 能力
"""
from typing import Any, Dict, List, Optional

from app.log import logger
from app.services.llm.llm_config_utils import get_default_llm_config
from app.services.llm.llm_proxy_service import llm_proxy_service

from ..base.exceptions import AgentError
from .curl_parser import ParamSchema


class ParamExtractor:
    """参数提取器 - 使用 llm_proxy 提取参数值"""

    def __init__(self, tenant_id: int = 0, app_name: Optional[str] = None):
        self.tenant_id = tenant_id
        self.app_name = app_name

    async def extract(
        self,
        query: str,
        param_schemas: List[ParamSchema],
        system_prompt: str = "",
        llm_model: str = "",
        llm_temperature: float = 0.0,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        从 query 中提取参数值

        Args:
            query: 用户查询
            param_schemas: 参数 schema 列表
            system_prompt: 系统提示词
            llm_model: 模型名称
            llm_temperature: 温度参数
            context: 额外上下文

        Returns:
            Dict[str, Any]: 提取的参数值
        """
        logger.info(f"[ParamExtractor] 开始提取参数: {len(param_schemas)} 个")

        if not param_schemas:
            logger.warning("[ParamExtractor] 没有参数需要提取")
            return {}

        # 构建 tools
        tools = self._build_tools(param_schemas)

        # 构建提示词
        prompt = self._build_prompt(query, param_schemas, system_prompt, context)

        try:
            # 获取 LLM 配置
            config = await get_default_llm_config(
                tenant_id=self.tenant_id,
                app_name=self.app_name
            )

            if not config:
                raise AgentError("未找到 LLM 配置")

            # 调用 llm_proxy 提取参数
            result = await llm_proxy_service.process_request(
                query=prompt,
                tools=tools,
                system_prompt=system_prompt or "你是一个参数提取助手，从用户输入中提取指定参数。",
                tool_choice="auto",
                config=config
            )

            # 解析结果
            params = self._parse_result(result)

            logger.info(f"[ParamExtractor] 提取完成: {params}")
            return params

        except Exception as e:
            logger.error(f"[ParamExtractor] 提取失败: {e}")
            raise AgentError(f"参数提取失败: {e}")

    async def refine(
        self,
        query: str,
        param_schemas: List[ParamSchema],
        previous_params: Dict[str, Any],
        previous_result: str,
        feedback: str,
        llm_model: str = "gpt-4o-mini",
        llm_temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        根据反馈优化参数

        Args:
            query: 用户查询
            param_schemas: 参数 schema 列表
            previous_params: 上一次的参数
            previous_result: 上一次的 API 结果
            feedback: 反馈信息
            llm_model: 模型名称
            llm_temperature: 温度参数

        Returns:
            Dict[str, Any]: 优化后的参数值
        """
        logger.info("[ParamExtractor] 开始优化参数")

        # 构建 tools
        tools = self._build_tools(param_schemas)

        # 构建优化提示词
        prompt = f"""基于以下信息优化参数：

原始查询: {query}

上一次参数: {previous_params}

上一次结果: {previous_result}

反馈信息: {feedback}

请根据反馈调整参数，以获取更好的结果。"""

        try:
            # 获取 LLM 配置
            config = await get_default_llm_config(
                tenant_id=self.tenant_id,
                app_name=self.app_name
            )

            if not config:
                raise AgentError("未找到 LLM 配置")

            # 调用 llm_proxy 优化参数
            result = await llm_proxy_service.process_request(
                query=prompt,
                tools=tools,
                system_prompt="你是一个参数优化助手，根据反馈调整参数。",
                tool_choice="auto",
                config=config
            )

            # 解析结果
            params = self._parse_result(result)

            logger.info(f"[ParamExtractor] 优化完成: {params}")
            return params

        except Exception as e:
            logger.error(f"[ParamExtractor] 优化失败: {e}")
            raise AgentError(f"参数优化失败: {e}")

    def _build_tools(self, param_schemas: List[ParamSchema]) -> List[Dict[str, Any]]:
        """构建 Function Calling tools"""
        properties = {}
        required = []

        for schema in param_schemas:
            properties[schema.name] = {
                "type": schema.type,
                "description": schema.description
            }
            if schema.required:
                required.append(schema.name)

        return [{
            "type": "function",
            "function": {
                "name": "extract_params",
                "description": "从用户输入中提取参数",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }]

    def _build_prompt(
        self,
        query: str,
        param_schemas: List[ParamSchema],
        system_prompt: str,
        context: str
    ) -> str:
        """构建提取提示词"""
        params_desc = "\n".join([
            f"- {s.name} ({s.type}): {s.description}"
            for s in param_schemas
        ])

        prompt = f"""{system_prompt}

需要从以下查询中提取参数：

{query}

需要提取的参数：
{params_desc}

{context}

请使用 extract_params 函数提取参数。"""

        return prompt

    def _parse_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """解析 llm_proxy 返回的结果"""
        # 从 function call 结果中提取参数
        if "function_call" in result:
            function_call = result["function_call"]
            if "arguments" in function_call:
                import json
                return json.loads(function_call["arguments"])

        # 直接返回结果中的参数
        return result.get("arguments", {})
