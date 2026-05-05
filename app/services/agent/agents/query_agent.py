"""
Query Agent - 智能查询 Agent

使用 Function Calling 实现多轮交互：
- call_api: 发起 API 请求
- validate_result: 验证结果并决定是否继续

流程：
1. 第一轮：LLM 输出 call_api 参数
2. 第二轮：将 API 结果返回给 LLM
3. 第三轮：LLM 使用 validate_result 判断是否需要继续调整
"""
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.log import logger
from app.services.llm.llm_config_utils import get_default_llm_config
from app.services.llm.llm_proxy_service import llm_proxy_service

from ..base.agent import BaseAgent
from ..base.types import AgentInput, AgentOutput, AgentStatus, AttemptRecord, APIResult, AgentContext, SelectedData
from ..base.exceptions import AgentError
from ..core.curl_parser import CurlParser, ParsedCurl, ParamSchema
from ..core.api_executor import APIExecutor
from ..core.result_validator import ResultValidator


class QueryAgent(BaseAgent):
    """
    查询 Agent

    通过自然语言查询外部 API，使用多轮 Function Calling 自动提取参数、
    执行查询并验证结果，直到获得满意结果。
    """

    def __init__(self, context: Optional[AgentContext] = None):
        super().__init__(name="query_agent")
        self.context = context or AgentContext()

        # 初始化组件
        self.curl_parser = CurlParser()
        self.api_executor = APIExecutor()
        self.result_validator = ResultValidator(
            tenant_id=self.context.tenant_id,
            app_name=self.context.app_name
        )

    async def run(self, input_data: AgentInput) -> AgentOutput:
        """
        执行查询

        Args:
            input_data: Agent 输入

        Returns:
            AgentOutput: 查询结果
        """
        logger.info(f"[QueryAgent] 开始执行查询: {input_data.query}")
        start_time = time.time()

        try:
            # 1. 解析 curl
            parsed = self.curl_parser.parse(input_data.curl)
            logger.info(f"[QueryAgent] 解析 curl 完成: {parsed.method} {parsed.url}")

            # 2. 检查是否有参数需要提取
            if not parsed.param_schemas:
                result = await self._execute_without_params(parsed)
                execution_time = int((time.time() - start_time) * 1000)
                return AgentOutput(
                    success=result.success,
                    status=AgentStatus.SUCCESS if result.success else AgentStatus.FAILED,
                    data=result.data,
                    error=result.error,
                    total_attempts=1,
                    execution_time_ms=execution_time
                )

            # 3. 使用多轮对话执行查询
            return await self._execute_with_conversation(input_data, parsed)

        except Exception as e:
            logger.error(f"[QueryAgent] 执行失败: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            return AgentOutput(
                success=False,
                status=AgentStatus.FAILED,
                error=str(e),
                total_attempts=0,
                execution_time_ms=execution_time
            )

    async def _execute_without_params(self, parsed: ParsedCurl) -> APIResult:
        """无需参数，直接执行"""
        return await self.api_executor.execute(parsed, {})

    async def _execute_with_conversation(
        self,
        input_data: AgentInput,
        parsed: ParsedCurl
    ) -> AgentOutput:
        """
        使用多轮对话执行查询

        每轮对话：
        1. LLM 决定调用 call_api（输出参数）或 finish（结束）
        2. 如果是 call_api，执行 API 并将结果返回给 LLM
        3. LLM 验证结果，决定继续调整参数或结束
        """
        start_time = time.time()
        attempts = []
        session_id = str(uuid.uuid4())

        # 获取 LLM 配置
        config = await get_default_llm_config(
            tenant_id=self.context.tenant_id,
            app_name=self.context.app_name
        )

        if not config:
            raise AgentError("未找到 LLM 配置")

        # 构建 tools
        tools = self._build_tools(parsed.param_schemas)

        # 初始查询
        current_query = input_data.query
        if input_data.expected_result:
            current_query = f"{current_query}\n\n预期结果: {input_data.expected_result}"

        for attempt in range(input_data.max_attempts):
            logger.info(f"[QueryAgent] 第 {attempt + 1} 次尝试")

            try:
                # 调用 LLM，让 LLM 决定下一步
                # 使用 bind_tools_stream 方法支持多 tool 选择
                result = await llm_proxy_service.process_request(
                    query=current_query,
                    tools=tools,
                    system_prompt=input_data.system_prompt or self._build_system_prompt(parsed),
                    tool_choice="auto",
                    method=input_data.llm_method,
                    config=config,
                    session_id=session_id,
                    memory_rounds=input_data.max_attempts * 3
                )

                # 解析 LLM 的决策
                # result 包含 tool 调用的参数和 _meta 元数据
                action = None
                params = {}
                reason = result.get("reason", "")

                logger.info(f"[QueryAgent] LLM 返回结果: {result}")

                # 获取期望的参数名称
                param_names = {p.name for p in parsed.param_schemas}
                logger.info(f"[QueryAgent] 期望参数: {param_names}")

                # 根据返回的参数判断是哪个工具被调用
                # finish 工具特有的参数
                finish_params = {"selected_index", "selected_data"}
                has_finish_params = bool(finish_params & set(result.keys()))

                # call_api 工具的参数（排除 finish 特有的参数）
                call_api_params = param_names - finish_params
                has_call_api_params = any(
                    p in result and result[p] is not None and result[p] != ""
                    for p in call_api_params
                )

                if has_finish_params:
                    # 优先判断为 finish（有 selected_data 或 selected_index）
                    action = "finish"
                    logger.info(f"[QueryAgent] 识别为 finish 动作")
                elif has_call_api_params:
                    # 有 API 调用参数，判断为 call_api
                    action = "call_api"
                    for p in param_names:
                        if p in result and result[p] is not None:
                            params[p] = result[p]
                    logger.info(f"[QueryAgent] 识别为 call_api 动作, 参数: {params}")
                else:
                    # 没有识别到工具调用，记录警告并继续下一次尝试
                    logger.warning(f"[QueryAgent] 无法识别动作, result keys: {list(result.keys())}, 将继续重试")
                    # 添加重试记录
                    record = AttemptRecord(
                        attempt_number=attempt + 1,
                        params={},
                        api_result=APIResult(success=False, status_code=0, error="LLM 未返回有效的工具调用参数"),
                        is_valid=False,
                        reason="LLM 未返回有效的工具调用参数，需要重试"
                    )
                    attempts.append(record)
                    # 更新查询，提示 LLM 需要使用工具
                    current_query = f"{input_data.query}\n\n注意：请使用 call_api 工具传入参数，或在没有结果时使用 finish 工具结束。"
                    continue

                if action == "finish":
                    # LLM 决定结束，返回结果
                    execution_time = int((time.time() - start_time) * 1000)
                    logger.info(f"[QueryAgent] LLM 决定结束查询: {reason}")

                    last_attempt = attempts[-1] if attempts else None

                    # 提取选中的数据信息
                    selected_index = result.get("selected_index", -1)
                    selected_data = result.get("selected_data")
                    selected_reason = result.get("reason", "")

                    selected = SelectedData(
                        index=selected_index,
                        data=selected_data,
                        reason=selected_reason
                    )

                    return AgentOutput(
                        success=True,
                        status=AgentStatus.SUCCESS,
                        data=last_attempt.api_result.data if last_attempt else {},
                        attempts=attempts,
                        total_attempts=attempt + 1,
                        execution_time_ms=execution_time,
                        selected=selected
                    )

                elif action == "call_api":
                    # LLM 决定调用 API
                    logger.info(f"[QueryAgent] LLM 决定调用 API: {params}")

                    # 执行 API
                    api_result = await self.api_executor.execute(parsed, params)

                    # 记录尝试
                    record = AttemptRecord(
                        attempt_number=attempt + 1,
                        params=params.copy(),
                        api_result=api_result,
                        is_valid=False,  # 待验证
                        reason=""
                    )
                    attempts.append(record)

                    # 将 API 结果返回给 LLM，让它决定下一步
                    current_query = self._build_result_feedback(api_result)

                else:
                    # 未知的 action，尝试结束
                    logger.warning(f"[QueryAgent] 未知的 action: {action}")
                    break

            except Exception as e:
                logger.exception(f"[QueryAgent] 第 {attempt + 1} 次尝试失败: {e}")
                record = AttemptRecord(
                    attempt_number=attempt + 1,
                    params={},
                    api_result=APIResult(success=False, status_code=0, error=str(e)),
                    is_valid=False,
                    reason=str(e)
                )
                attempts.append(record)

        # 达到最大尝试次数
        execution_time = int((time.time() - start_time) * 1000)
        logger.warning(f"[QueryAgent] 达到最大尝试次数: {input_data.max_attempts}")

        last_attempt = attempts[-1] if attempts else None
        return AgentOutput(
            success=False,
            status=AgentStatus.MAX_ATTEMPTS_REACHED,
            data=last_attempt.api_result.data if last_attempt else None,
            error="达到最大尝试次数，未能获得满意结果",
            attempts=attempts,
            total_attempts=len(attempts),
            execution_time_ms=execution_time
        )

    def _build_tools(self, param_schemas: List[ParamSchema]) -> List[Dict[str, Any]]:
        """构建 Function Calling tools"""
        # 构建 call_api 的参数 schema
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
                    "name": "call_api",
                    "description": "调用 API 查询数据",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            **properties,
                            "reason": {
                                "type": "string",
                                "description": "选择这些参数的原因（可选）"
                            }
                        },
                        "required": required
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "finish",
                    "description": "结束查询，返回最终结果。当 API 返回结果满足用户需求，或确认无法找到结果时，必须调用此函数结束查询。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "结束查询的原因，说明是否找到满足需求的结果"
                            },
                            "selected_index": {
                                "type": "integer",
                                "description": "选中的数据在结果列表中的索引位置（从0开始），如果找到多条匹配数据，选择最符合用户需求的那一条"
                            },
                            "selected_data": {
                                "type": "object",
                                "description": "选中的完整数据对象，包含该条数据的所有字段"
                            }
                        },
                        "required": ["reason"]
                    }
                }
            }
        ]

    def _build_system_prompt(self, parsed: ParsedCurl) -> str:
        """构建系统提示词"""
        # 构建参数说明
        param_descriptions = []
        for schema in parsed.param_schemas:
            if schema.required:
                param_descriptions.append(f"- {schema.name}: {schema.description} (必填)")
            else:
                param_descriptions.append(f"- {schema.name}: {schema.description} (可选，示例: {schema.example})")

        params_text = "\n".join(param_descriptions) if param_descriptions else "无参数"

        return f"""你是一个智能信息提取助手。你的任务是分析用户提供的查询语句，从中提取关键信息，然后调用 API 获取相关数据。

API 信息:
- 方法: {parsed.method}
- URL: {parsed.url}

需要从查询中提取的参数:
{params_text}

你必须使用以下两个工具之一来响应：
1. call_api: 调用 API 查询数据，传入提取的参数
2. finish: 结束查询，当获得结果或确认无法找到结果时必须调用

你的工作流程:
1. 仔细分析用户的查询语句，理解用户需要查询什么
2. 从查询中提取上述参数的具体值（不要返回 null，必须提取实际值）
3. 使用 call_api 工具调用 API，传入提取的参数值
4. 查看 API 返回结果（API 返回的数据格式可能各不相同，请自行分析数据结构）
5. 如果结果满足需求，必须使用 finish 工具结束查询，并返回选中的数据
6. 如果结果不满足（如返回空数据），分析原因并调整参数再次调用 call_api
7. 无论如何，最终必须通过调用 finish 工具来结束整个查询流程

重要规则:
- **每次响应只能调用一个工具**（call_api 或 finish），绝对不能同时调用两个工具
- 如果需要调用 API，只返回 call_api 的参数，不要返回 finish 的参数
- 如果要结束查询，只返回 finish 的参数（selected_index, selected_data, reason），不要返回 call_api 的参数
- 必须从查询中提取具体的参数值，不能返回 null
- 例如查询"重庆沙坪坝的比亚迪门店"，应该提取: city="重庆", address="沙坪坝", name="比亚迪"
- 如果查询中没有提到某个参数，可以返回空字符串 "" 或省略该参数
- 如果首次查询无结果，尝试使用更通用的关键词（如去掉区域限制）
- 用户输入可能是直接查询，也可能是聊天记录，需要你从中提取查询意图
- 最终必须通过调用 finish 工具来结束查询，这是唯一正确的退出方式
- API 返回的数据格式不固定，可能是 {{"data": [...]}}、{{"items": [...]}}、{{"results": [...]}} 或直接是数组 [...]
- 你需要自行分析 API 返回的数据结构，找到其中的数据列表或对象
- 调用 finish 时，请根据 API 返回的数据结构，选择最符合用户需求的数据，并返回:
  * selected_index: 选中数据在列表中的索引（从0开始，如果是单条数据则为0）
  * selected_data: 选中的完整数据对象（从 API 返回的数据中直接提取）
  * reason: 选择这条数据的原因"""

    def _build_result_feedback(self, api_result: APIResult, max_length: int = 8000) -> str:
        """构建 API 结果反馈

        Args:
            api_result: API 调用结果
            max_length: 最大内容长度，超出将截断
        """
        # 处理响应内容，确保是字符串格式
        if api_result.raw_response:
            response_content = api_result.raw_response
        elif api_result.data:
            try:
                response_content = json.dumps(api_result.data, ensure_ascii=False, indent=2)
            except:
                response_content = str(api_result.data)
        else:
            response_content = "无响应数据"

        # 截断过长的内容
        if len(response_content) > max_length:
            truncated_length = len(response_content) - max_length
            response_content = response_content[:max_length] + f"\n... (已截断 {truncated_length} 字符)"

        return f"""API 调用结果：

```
{response_content}
```

请分析这个结果是否满足用户的需求。
- 首先分析 API 返回的数据结构，找到其中的数据列表或对象
- 如果满足需求，请使用 finish 工具结束，并返回：
  * selected_index: 选中数据在列表中的索引（从0开始，如果是单条数据则为0）
  * selected_data: 选中的完整数据对象（从 API 返回的数据中直接提取）
  * reason: 选择原因
- 如果不满足，请分析原因并使用 call_api 工具调整参数重新查询"""
