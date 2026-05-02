"""
结果验证器
"""
from typing import Any, Dict, List, Optional, Tuple

from app.log import getLogger
from app.controllers.llm_config import llm_config_controller
from app.services.llm_proxy_service import llm_proxy_service

from ..base.types import APIResult
from ..base.exceptions import AgentError

logger = getLogger(__name__)


class ResultValidator:
    """结果验证器"""

    def __init__(self, tenant_id: int = 0, app_name: Optional[str] = None):
        self.tenant_id = tenant_id
        self.app_name = app_name

    async def validate(
        self,
        api_result: APIResult,
        query: str,
        expected_result: str = "",
        llm_model: str = "gpt-4o-mini",
        llm_temperature: float = 0.0
    ) -> Tuple[bool, str]:
        """
        验证 API 结果是否符合预期

        Args:
            api_result: API 调用结果
            query: 用户查询
            expected_result: 期望结果描述
            llm_model: 模型名称
            llm_temperature: 温度参数

        Returns:
            Tuple[bool, str]: (是否有效, 原因)
        """
        logger.info("[ResultValidator] 开始验证结果")

        # 首先检查 API 调用是否成功
        if not api_result.success:
            return False, f"API 调用失败: {api_result.error}"

        # 如果没有期望结果描述，直接返回成功
        if not expected_result:
            return True, "API 调用成功"

        try:
            # 构建验证提示
            prompt = self._build_validation_prompt(
                query=query,
                api_result=api_result,
                expected_result=expected_result
            )

            # 获取 LLM 配置
            config = await llm_config_controller.get_default_config(
                tenant_id=self.tenant_id,
                app_name=self.app_name
            )

            if not config:
                logger.warning("[ResultValidator] 未找到 LLM 配置，跳过验证")
                return True, "未配置验证，直接返回"

            # 调用 LLM 验证
            tools = [self._build_validation_tool()]

            result = await llm_proxy_service.process_request(
                query=prompt,
                tools=tools,
                system_prompt="你是一个结果验证助手，判断 API 返回结果是否符合用户查询的预期。",
                tool_choice="auto",
                config=config
            )

            # 解析验证结果
            is_valid, reason = self._parse_validation_result(result)

            logger.info(f"[ResultValidator] 验证完成: valid={is_valid}, reason={reason}")
            return is_valid, reason

        except Exception as e:
            logger.error(f"[ResultValidator] 验证失败: {e}")
            # 验证失败时默认返回成功，避免阻塞
            return True, f"验证过程出错，默认接受: {e}"

    def _build_validation_prompt(
        self,
        query: str,
        api_result: APIResult,
        expected_result: str
    ) -> str:
        """构建验证提示"""
        import json

        result_str = json.dumps(api_result.data, ensure_ascii=False, indent=2)
        if len(result_str) > 2000:
            result_str = result_str[:2000] + "..."

        return f"""用户查询: {query}

期望结果: {expected_result}

API 返回结果:
```json
{result_str}
```

请判断 API 返回的结果是否符合用户的查询预期。
"""

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
                            "description": "验证理由，说明为什么符合或不符合"
                        },
                        "suggestion": {
                            "type": "string",
                            "description": "如果不符合，建议如何调整查询参数"
                        }
                    },
                    "required": ["is_valid", "reason"]
                }
            }
        }

    def _parse_validation_result(self, result: Dict[str, Any]) -> Tuple[bool, str]:
        """解析验证结果"""
        import json

        # 检查函数调用结果
        if "function_call" in result:
            try:
                args = result["function_call"].get("arguments", "{}")
                if isinstance(args, str):
                    args = json.loads(args)

                is_valid = args.get("is_valid", True)
                reason = args.get("reason", "未提供理由")
                return is_valid, reason
            except json.JSONDecodeError:
                logger.error(f"[ResultValidator] 解析验证结果失败: {args}")
                return True, "解析验证结果失败，默认接受"

        # 直接检查结果
        if "is_valid" in result:
            return result["is_valid"], result.get("reason", "")

        # 默认接受
        return True, "未获取到验证结果，默认接受"

    async def extract_feedback(
        self,
        api_result: APIResult,
        query: str,
        expected_result: str
    ) -> str:
        """
        提取优化建议

        Args:
            api_result: API 结果
            query: 用户查询
            expected_result: 期望结果

        Returns:
            str: 优化建议
        """
        is_valid, reason = await self.validate(
            api_result=api_result,
            query=query,
            expected_result=expected_result
        )

        if is_valid:
            return ""

        return reason
