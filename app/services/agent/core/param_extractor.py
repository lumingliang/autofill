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
        session_id: str = None,
        memory_rounds: int = None
    ) -> Dict[str, Any]:
        """
        从 query 中提取参数值

        Args:
            query: 用户查询
            param_schemas: 参数 schema 列表
            system_prompt: 系统提示词
            session_id: 会话ID，用于多轮对话记忆
            memory_rounds: 记忆轮数限制

        Returns:
            Dict[str, Any]: 提取的参数值
        """
        logger.info(f"[ParamExtractor] 开始提取参数: {len(param_schemas)} 个")

        if not param_schemas:
            logger.warning("[ParamExtractor] 没有参数需要提取")
            return {}

        # 构建 tools
        tools = self._build_tools(param_schemas)

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
                query=query,
                tools=tools,
                system_prompt=system_prompt,
                tool_choice="auto",
                config=config,
                session_id=session_id,
                memory_rounds=memory_rounds
            )

            logger.info(f"[ParamExtractor] 提取完成: {result}")
            return result

        except Exception as e:
            logger.error(f"[ParamExtractor] 提取失败: {e}")
            raise AgentError(f"参数提取失败: {e}")

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
