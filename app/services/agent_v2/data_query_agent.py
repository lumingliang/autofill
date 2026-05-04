"""
DataQueryAgent - 通用数据查询 Agent

基于 OpenAPI 规范自动生成工具，使用 LangChain Agent 进行多轮交互决策。
"""
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.log import logger
from app.services.llm.llm_config_utils import get_default_llm_config
from app.settings.config import settings

from .openapi_parser import OpenAPIParser
from .api_tool import APIToolManager


class AgentDecision(str, Enum):
    """Agent 决策结果"""
    COMPLETE = "complete"           # 结果满足需求，可以返回
    CONTINUE = "continue"           # 需要继续查询
    NEED_MORE_INFO = "need_more_info"  # 需要用户提供更多信息


@dataclass
class IterationRecord:
    """迭代记录"""
    round: int
    query: str
    tool_name: Optional[str]
    tool_params: Dict[str, Any]
    api_response: Any
    agent_decision: str
    reasoning: str


@dataclass
class QueryResult:
    """查询结果"""
    agent_decision: str
    api_response: Optional[Any]
    formatted_result: Optional[str]
    reasoning: str
    iterations: List[IterationRecord] = field(default_factory=list)
    execution_time_ms: int = 0
    total_tokens: int = 0


class DecisionOutput(BaseModel):
    """Agent 决策输出结构"""
    agent_decision: str = Field(
        description="决策结果: complete/continue/need_more_info"
    )
    formatted_result: Optional[str] = Field(
        default=None,
        description="格式化后的查询结果（仅当 decision 为 complete 时填写）"
    )
    reasoning: str = Field(
        description="决策理由，解释为什么做出这个决策"
    )


class DataQueryAgent:
    """通用数据查询 Agent"""

    def __init__(
        self,
        openapi_spec: str,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        max_iterations: int = 5,
        tenant_id: int = 0,
        app_name: Optional[str] = None,
        temperature: float = 0.0,
    ):
        """
        初始化 DataQueryAgent

        Args:
            openapi_spec: OpenAPI 规范来源（URL 或本地文件路径）
            api_key: API 认证密钥
            headers: 自定义请求头
            max_iterations: 最大迭代次数
            tenant_id: 租户 ID
            app_name: 应用名称
            temperature: LLM 温度参数
        """
        self.openapi_spec = openapi_spec
        self.max_iterations = max_iterations
        self.tenant_id = tenant_id
        self.app_name = app_name
        self.temperature = temperature

        # 解析 OpenAPI 并创建 Tools
        self.parser = OpenAPIParser(openapi_spec)
        self.tool_manager = APIToolManager(
            parser=self.parser,
            api_key=api_key,
            headers=headers
        )
        self.tools = self.tool_manager.create_tools()

        logger.info(f"[DataQueryAgent] 初始化完成，加载了 {len(self.tools)} 个工具")

    async def _create_llm(self) -> ChatOpenAI:
        """创建 LLM 实例"""
        # 获取 LLM 配置
        config = await get_default_llm_config(
            tenant_id=self.tenant_id,
            app_name=self.app_name
        )

        if config is None:
            raise ValueError("No LLM configuration found")

        # 使用 LiteLLM 网关
        litellm_config = settings.LITELLM_CONFIG
        base_url = litellm_config.get("base_url", "http://localhost:4000")
        master_key = litellm_config.get("master_key", "")

        # 使用配置名称作为模型名称
        model_name = config.name

        logger.info(f"[DataQueryAgent] 使用模型: {model_name}")

        return ChatOpenAI(
            model=model_name,
            api_key=master_key,
            base_url=f"{base_url}/v1",
            temperature=self.temperature,
            timeout=60
        )

    def _create_system_prompt(self) -> str:
        """创建系统提示词"""
        tool_descriptions = []
        for tool in self.tools:
            desc = tool.description[:200] + "..." if len(tool.description) > 200 else tool.description
            tool_descriptions.append(f"- {tool.name}: {desc}")

        tools_text = "\n".join(tool_descriptions) if tool_descriptions else "暂无可用工具"

        return f"""你是一个智能数据查询助手。你的任务是根据用户需求调用工具查询数据，并判断结果是否满足需求。

## 可用工具

{tools_text}

## 工作流程

1. **分析用户需求**：理解用户想要什么数据
2. **调用工具**：选择合适的工具，从用户 query 中提取参数并调用
3. **接收结果**：获取 API 返回的原始数据
4. **决策判断**：
   - 如果结果满足用户需求 → 返回 complete
   - 如果结果不满足（需要更多数据、需要过滤等）→ 返回 continue
   - 如果缺少必要信息无法查询 → 返回 need_more_info

## 输出格式

你必须按以下 JSON 格式返回你的决策：

```json
{{
  "agent_decision": "complete|continue|need_more_info",
  "formatted_result": "格式化后的查询结果（仅当 decision 为 complete 时填写）",
  "reasoning": "你的决策理由"
}}
```

## 注意事项

- 参数值必须从用户 query 中提取，不要编造
- API 响应是原始 JSON，你需要解析并判断
- 如果用户 query 包含"前N条"、"显示X个"等限制，请遵守
- 如果查询无结果，说明情况并返回 complete
- 如果用户问题不涉及数据查询，返回 need_more_info
"""

    async def query(
        self,
        user_query: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> QueryResult:
        """
        执行查询

        Args:
            user_query: 用户查询语句
            chat_history: 聊天记录，格式为 [{"role": "user|assistant", "content": "..."}]

        Returns:
            QueryResult: 查询结果
        """
        start_time = time.time()
        logger.info(f"[DataQueryAgent] 开始查询: {user_query}")

        # 执行 Agent
        iterations = []
        final_api_response = None
        total_tokens = 0

        current_query = user_query

        for i in range(self.max_iterations):
            logger.info(f"[DataQueryAgent] 第 {i + 1} 轮迭代")

            try:
                # 创建系统提示词
                system_prompt = self._create_system_prompt()

                # 创建 LLM
                llm = await self._create_llm()

                # 绑定工具
                llm_with_tools = llm.bind_tools(self.tools)

                # 构建消息
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=current_query)
                ]

                # 调用 LLM
                response = await llm_with_tools.ainvoke(messages)

                # 解析结果
                tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
                content = response.content if hasattr(response, 'content') else ""

                logger.info(f"[DataQueryAgent] LLM 响应: tool_calls={len(tool_calls)}, content={content[:100]}")

                tool_name = None
                tool_params = {}
                api_response = None

                # 执行工具调用
                if tool_calls and len(tool_calls) > 0:
                    tool_call = tool_calls[0]
                    tool_name = tool_call.get("name", "")
                    tool_params = tool_call.get("args", {})

                    # 找到对应的工具并执行
                    for tool in self.tools:
                        if tool.name == tool_name:
                            logger.info(f"[DataQueryAgent] 执行工具: {tool_name}, 参数: {tool_params}")
                            tool_result = await tool.ainvoke(tool_params)
                            api_response = tool_result
                            final_api_response = tool_result
                            break

                # 解析决策
                # 如果 LLM 返回了文本内容，尝试解析为决策
                decision = self._parse_decision(content)

                # 如果没有工具调用且没有明确决策，让 LLM 做决策
                if not tool_calls and not decision.get("agent_decision"):
                    # 调用决策 LLM
                    decision = await self._make_decision(
                        user_query=user_query,
                        api_response=api_response,
                        reasoning=""
                    )

                iteration = IterationRecord(
                    round=i + 1,
                    query=current_query,
                    tool_name=tool_name,
                    tool_params=tool_params if isinstance(tool_params, dict) else {},
                    api_response=api_response,
                    agent_decision=decision.get("agent_decision", "unknown"),
                    reasoning=decision.get("reasoning", "")
                )
                iterations.append(iteration)

                logger.info(f"[DataQueryAgent] 决策: {iteration.agent_decision}")

                # 判断是否需要继续
                if decision.get("agent_decision") == AgentDecision.COMPLETE:
                    execution_time = int((time.time() - start_time) * 1000)
                    return QueryResult(
                        agent_decision=AgentDecision.COMPLETE,
                        api_response=final_api_response,
                        formatted_result=decision.get("formatted_result"),
                        reasoning=decision.get("reasoning", ""),
                        iterations=iterations,
                        execution_time_ms=execution_time,
                        total_tokens=total_tokens
                    )

                elif decision.get("agent_decision") == AgentDecision.NEED_MORE_INFO:
                    execution_time = int((time.time() - start_time) * 1000)
                    return QueryResult(
                        agent_decision=AgentDecision.NEED_MORE_INFO,
                        api_response=final_api_response,
                        formatted_result=None,
                        reasoning=decision.get("reasoning", ""),
                        iterations=iterations,
                        execution_time_ms=execution_time,
                        total_tokens=total_tokens
                    )

                # 继续下一轮：构建反馈 query
                current_query = self._build_feedback_query(
                    user_query=user_query,
                    api_response=api_response,
                    reasoning=decision.get("reasoning", "")
                )

            except Exception as e:
                logger.error(f"[DataQueryAgent] 迭代异常: {e}")
                import traceback
                traceback.print_exc()
                execution_time = int((time.time() - start_time) * 1000)
                return QueryResult(
                    agent_decision=AgentDecision.NEED_MORE_INFO,
                    api_response=final_api_response,
                    formatted_result=None,
                    reasoning=f"执行异常: {str(e)}",
                    iterations=iterations,
                    execution_time_ms=execution_time,
                    total_tokens=total_tokens
                )

        # 达到最大迭代次数
        execution_time = int((time.time() - start_time) * 1000)
        return QueryResult(
            agent_decision=AgentDecision.CONTINUE,
            api_response=final_api_response,
            formatted_result=None,
            reasoning="达到最大迭代次数，需要人工介入",
            iterations=iterations,
            execution_time_ms=execution_time,
            total_tokens=total_tokens
        )

    async def _make_decision(
        self,
        user_query: str,
        api_response: Any,
        reasoning: str
    ) -> Dict[str, Any]:
        """让 LLM 做出决策"""
        try:
            llm = await self._create_llm()

            response_str = json.dumps(api_response, ensure_ascii=False) if isinstance(api_response, (dict, list)) else str(api_response)

            prompt = f"""你是一个智能数据查询助手。请根据以下信息做出决策：

用户查询: {user_query}

API 响应: {response_str}

请判断：
1. 这个结果是否满足原始用户需求？
2. 如果不满足，还需要做什么？
3. 如果满足，请格式化结果。

请按以下 JSON 格式返回你的决策：

```json
{{
  "agent_decision": "complete|continue|need_more_info",
  "formatted_result": "格式化后的查询结果（仅当 decision 为 complete 时填写）",
  "reasoning": "你的决策理由"
}}
```
"""

            messages = [
                SystemMessage(content="你是一个智能数据查询助手，请严格按照 JSON 格式返回决策。"),
                HumanMessage(content=prompt)
            ]

            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else ""

            return self._parse_decision(content)

        except Exception as e:
            logger.error(f"[DataQueryAgent] 决策失败: {e}")
            return {
                "agent_decision": AgentDecision.COMPLETE,
                "formatted_result": None,
                "reasoning": f"决策过程出错: {str(e)}"
            }

    def _format_chat_history(
        self,
        chat_history: List[Dict[str, str]]
    ) -> List[Any]:
        """格式化聊天记录为 LangChain 消息格式"""
        messages = []

        for msg in chat_history:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))

        return messages

    def _parse_decision(self, output: Any) -> Dict[str, Any]:
        """解析 Agent 输出的决策"""
        try:
            # 尝试直接解析 JSON
            if isinstance(output, str):
                output = output.strip()
                if not output:
                    return {}

                # 尝试从 Markdown 代码块中提取
                if "```json" in output:
                    json_str = output.split("```json")[1].split("```")[0].strip()
                elif "```" in output:
                    json_str = output.split("```")[1].strip()
                else:
                    json_str = output

                try:
                    parsed = json.loads(json_str)
                    return {
                        "agent_decision": parsed.get("agent_decision", ""),
                        "formatted_result": parsed.get("formatted_result"),
                        "reasoning": parsed.get("reasoning", "")
                    }
                except json.JSONDecodeError:
                    pass

            # 如果已经是字典格式
            if isinstance(output, dict):
                # 检查是否有直接的决策字段
                if "agent_decision" in output:
                    return {
                        "agent_decision": output.get("agent_decision", ""),
                        "formatted_result": output.get("formatted_result"),
                        "reasoning": output.get("reasoning", "")
                    }

        except Exception as e:
            logger.warning(f"[DataQueryAgent] 无法解析决策输出: {e}")

        # 默认返回空，让调用者处理
        return {}

    def _build_feedback_query(
        self,
        user_query: str,
        api_response: Any,
        reasoning: str
    ) -> str:
        """构建反馈 query 用于下一轮迭代"""
        response_str = json.dumps(api_response, ensure_ascii=False) if isinstance(api_response, (dict, list)) else str(api_response)

        return f"""上一轮查询结果如下：

```json
{response_str}
```

上一轮决策理由：{reasoning}

请判断：
1. 这个结果是否满足原始用户需求"{user_query}"？
2. 如果不满足，还需要做什么？
3. 如果满足，请格式化结果并返回 complete。

请按指定 JSON 格式返回决策。"""

    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return [tool.name for tool in self.tools]

    def get_tool_details(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具详细信息"""
        for tool in self.tools:
            if tool.name == tool_name:
                return {
                    "name": tool.name,
                    "description": tool.description,
                }
        return None
