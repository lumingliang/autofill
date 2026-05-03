"""
结果验证器
"""
from typing import Any, Dict, List, Optional, Tuple

from app.log import logger
from app.controllers.llm_config import llm_config_controller
from app.services.llm_proxy_service import llm_proxy_service

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
                system_prompt="你是一个结果验证助手，判断 API 返回结果是否符合用户查询的预期，并提取最匹配的数据项。",
                tool_choice="auto",
                config=config
            )

            # 解析验证结果
            is_valid, reason, best_match = self._parse_validation_result(result)

            logger.info(f"[ResultValidator] 验证完成: valid={is_valid}, reason={reason[:100]}...")
            if best_match:
                logger.info(f"[ResultValidator] 最匹配项: {best_match.get('name')} (ID: {best_match.get('id')}, 匹配度: {best_match.get('match_score')})")
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

请完成以下任务：
1. 判断 API 返回的结果是否符合用户的查询预期
2. 如果结果中有多个数据项，找出最匹配的一个，并提取其关键信息：
   - id: 数据项的唯一标识符
   - name: 数据项的名称
   - key_data: 关键数据字段（如地址、电话、状态等）
   - match_score: 匹配度评分（0-1）
   - match_reason: 匹配理由说明

注意：即使整体结果不完全符合预期，也要返回最匹配的数据项信息，以便用户参考。
"""

    def _build_validation_tool(self) -> Dict[str, Any]:
        """构建验证工具"""
        return {
            "type": "function",
            "function": {
                "name": "validate_result",
                "description": "验证 API 结果是否符合预期，并返回最匹配的数据项",
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
                        },
                        "best_match": {
                            "type": "object",
                            "description": "最匹配的数据项，包含关键标识信息",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "数据项的唯一标识符（如 id、code 等）"
                                },
                                "name": {
                                    "type": "string",
                                    "description": "数据项的名称或标题"
                                },
                                "key_data": {
                                    "type": "object",
                                    "description": "关键数据字段，根据数据类型动态提取（如地址、电话、状态等）"
                                },
                                "match_score": {
                                    "type": "number",
                                    "description": "匹配度评分（0-1），表示该数据项与用户查询的匹配程度"
                                },
                                "match_reason": {
                                    "type": "string",
                                    "description": "匹配理由，说明为什么这个数据项最符合用户查询"
                                }
                            },
                            "required": ["id", "name", "match_score", "match_reason"]
                        }
                    },
                    "required": ["is_valid", "reason"]
                }
            }
        }

    def _parse_validation_result(self, result: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """解析验证结果
        
        Returns:
            Tuple[bool, str, Optional[Dict]]: (是否有效, 原因, 最匹配数据项)
        """
        import json

        # 检查函数调用结果
        if "function_call" in result:
            try:
                args = result["function_call"].get("arguments", "{}")
                if isinstance(args, str):
                    args = json.loads(args)

                is_valid = args.get("is_valid", True)
                reason = args.get("reason", "未提供理由")
                best_match = args.get("best_match")
                
                # 构建包含最匹配数据的详细原因
                if best_match:
                    match_info = f"\n最匹配项: {best_match.get('name', 'N/A')}"
                    match_info += f"\nID: {best_match.get('id', 'N/A')}"
                    match_info += f"\n匹配度: {best_match.get('match_score', 0):.2f}"
                    match_info += f"\n匹配理由: {best_match.get('match_reason', 'N/A')}"
                    if best_match.get('key_data'):
                        match_info += f"\n关键数据: {json.dumps(best_match['key_data'], ensure_ascii=False)}"
                    reason += match_info
                
                return is_valid, reason, best_match
            except json.JSONDecodeError:
                logger.error(f"[ResultValidator] 解析验证结果失败: {args}")
                return True, "解析验证结果失败，默认接受", None

        # 直接检查结果
        if "is_valid" in result:
            return result["is_valid"], result.get("reason", ""), result.get("best_match")

        # 默认接受
        return True, "未获取到验证结果，默认接受", None

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
