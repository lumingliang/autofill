"""
结果验证器
"""
import json
from typing import Any, Dict, List, Optional, Tuple

from app.log import logger
from app.services.llm.llm_config_service import llm_config_service
from app.services.llm.llm_proxy_service import llm_proxy_service

from ..base.types import APIResult
from ..base.exceptions import AgentError


class ResultValidator:
    """结果验证器"""

    def __init__(self, tenant_id: int = 0, app_name: Optional[str] = None):
        self.tenant_id = tenant_id
        self.app_name = app_name

    async def validate(
        self,
        api_result: APIResult,
        query: str,
        expected_result: str = ""
    ) -> Tuple[bool, str]:
        """
        验证 API 结果是否符合预期

        Args:
            api_result: API 执行结果
            query: 原始查询
            expected_result: 预期结果描述

        Returns:
            Tuple[bool, str]: (是否通过, 原因)
        """
        logger.info("[ResultValidator] 开始验证结果")

        try:
            # 构建验证提示词
            prompt = self._build_validation_prompt(
                query=query,
                api_result=api_result,
                expected_result=expected_result
            )

            # 获取 LLM 配置
            config = await llm_config_service.get_default_config()

            if not config:
                logger.warning("[ResultValidator] 未找到 LLM 配置，跳过验证")
                return True, "未配置验证，直接返回"

            # 调用 LLM 验证
            tools = [self._build_validation_tool()]

            result = await llm_proxy_service.process_request(
                query=prompt,
                tools=tools,
                system_prompt="你是一个结果验证助手，判断 API 结果是否符合预期。",
                tool_choice="auto",
                config=config
            )

            # 解析验证结果
            is_valid, reason = self._parse_validation_result(result)

            logger.info(f"[ResultValidator] 验证完成: {is_valid}, {reason}")
            return is_valid, reason

        except Exception as e:
            logger.error(f"[ResultValidator] 验证失败: {e}")
            # 验证失败时默认通过，避免阻塞流程
            return True, f"验证过程出错: {e}"

    def _build_validation_prompt(
        self,
        query: str,
        api_result: APIResult,
        expected_result: str
    ) -> str:
        """构建验证提示词"""
        expected_section = f"\n预期结果: {expected_result}\n" if expected_result else ""

        return f"""请验证以下 API 结果是否符合预期：

原始查询: {query}
{expected_section}
API 结果:
```json
{api_result.raw_response}
```

请判断 API 结果是否满足用户的查询需求。"""

    def _build_validation_tool(self) -> Dict[str, Any]:
        """构建验证工具"""
        return {
            "type": "function",
            "function": {
                "name": "validate_result",
                "description": "验证 API 结果是否符合预期",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "is_valid": {
                            "type": "boolean",
                            "description": "结果是否符合预期"
                        },
                        "reason": {
                            "type": "string",
                            "description": "验证原因"
                        }
                    },
                    "required": ["is_valid", "reason"]
                }
            }
        }

    def _parse_validation_result(self, result: Dict[str, Any]) -> Tuple[bool, str]:
        """解析验证结果"""
        if "function_call" in result:
            function_call = result["function_call"]
            if "arguments" in function_call:
                args = json.loads(function_call["arguments"])
                return args.get("is_valid", True), args.get("reason", "")

        return True, "无法解析验证结果，默认通过"
