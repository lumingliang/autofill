"""
参数提取器 - 复用 llm_proxy 的 FC 能力
"""
from typing import Any, Dict, List, Optional

from app.log import logger
from app.controllers.llm_config import llm_config_controller
from app.services.llm_proxy_service import llm_proxy_service

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
            config = await llm_config_controller.get_default_config(
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
            Dict[str, Any]: 优化后的参数
        """
        logger.info("[ParamExtractor] 开始优化参数")

        # 构建优化提示词
        context = f"""
之前的参数: {previous_params}
API 返回结果: {previous_result[:500]}
反馈: {feedback}

请根据反馈调整参数值，以获得更好的结果。
"""

        return await self.extract(
            query=query,
            param_schemas=param_schemas,
            system_prompt="你是一个参数优化助手，根据反馈调整参数值。",
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            context=context
        )

    def _build_tools(self, param_schemas: List[ParamSchema]) -> List[Dict[str, Any]]:
        """构建 Function Calling tools"""
        properties = {}
        required = []

        for schema in param_schemas:
            properties[schema.name] = {
                "type": schema.param_type,
                "description": schema.description
            }
            if schema.required:
                required.append(schema.name)

        return [
            {
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
            }
        ]

    def _build_prompt(
        self,
        query: str,
        param_schemas: List[ParamSchema],
        system_prompt: str,
        context: str
    ) -> str:
        """构建提示词"""
        param_desc = "\n".join([
            f"- {s.name} ({s.param_type}): {s.description}"
            for s in param_schemas
        ])

        prompt = f"""用户查询: {query}

需要从查询中提取以下参数:
{param_desc}

重要提示:
1. 提取关键词时，只保留最核心的词汇，去除修饰词
2. 例如"海洋网系列"应提取为"海洋网"，"王朝网车型"应提取为"王朝网"
3. 城市名称保持完整，如"重庆"、"广州"
4. 区域/地址提取核心地名，如"沙坪坝区"提取为"沙坪坝"
5. 如果参数未提及，返回空字符串""，不要猜测
"""

        if context:
            prompt += f"\n额外上下文:\n{context}"

        return prompt

    def _parse_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """解析 llm_proxy 返回结果"""
        # 检查是否有函数调用结果
        if "function_call" in result:
            import json
            try:
                args = result["function_call"].get("arguments", "{}")
                if isinstance(args, str):
                    return json.loads(args)
                return args
            except json.JSONDecodeError:
                logger.error(f"[ParamExtractor] 解析函数调用参数失败: {args}")
                return {}

        # 直接返回结果中的数据
        if "data" in result:
            return result["data"]

        # 返回整个结果（去除元信息）
        return {k: v for k, v in result.items() if not k.startswith("_")}
