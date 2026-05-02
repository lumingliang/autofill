"""
Query Agent 主类
"""
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from app.log import getLogger
from app.settings.config import settings

from .types import (
    QueryAgentState,
    QueryAgentOutput,
    QueryAgentInput,
    ParsedCurl,
    SearchAttempt
)
from .parser import CurlParser
from .utils import extract_by_selector
from .nodes import QueryNodes

logger = getLogger(__name__)


class QueryAgent:
    """通用查询 Agent"""

    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm
        self.nodes = None
        self.workflow = None

    def _get_or_create_llm(self, model: str, temperature: float = 0.0) -> ChatOpenAI:
        """获取或创建 LLM 实例，使用项目配置的 LiteLLM 网关"""
        # 使用 LiteLLM 网关配置
        litellm_config = settings.LITELLM_CONFIG
        base_url = litellm_config.get("base_url", "http://localhost:4000")
        master_key = litellm_config.get("master_key", "")

        return ChatOpenAI(
            model=model,
            api_key=master_key,
            base_url=f"{base_url}/v1",
            temperature=temperature,
            timeout=60
        )

    def _build_workflow(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        workflow = StateGraph(QueryAgentState)

        # 添加节点
        workflow.add_node("extract_params", self.nodes.extract_params)
        
        workflow.add_node("search", self.nodes.search)
        workflow.add_node("analyze_results", self.nodes.analyze_results)
        workflow.add_node("optimize_params", self.nodes.optimize_params)

        # 设置入口
        workflow.set_entry_point("extract_params")

        # 添加边
        workflow.add_edge("extract_params", "search")
        workflow.add_edge("search", "analyze_results")

        # 条件边
        workflow.add_conditional_edges(
            "analyze_results",
            self.nodes.should_continue,
            {
                "end": END,
                "optimize": "optimize_params"
            }
        )

        workflow.add_edge("optimize_params", "search")

        return workflow.compile()

    def run(
        self,
        query: str,
        curl: str,
        system_prompt: str,
        max_attempts: int = 5,
        timeout: int = 30,
        llm_model: str = "C4AI-Command-R-Plus",
        llm_temperature: float = 0.0,
        return_raw_response: bool = False,
        result_selector: Optional[str] = None,
        **kwargs
    ) -> QueryAgentOutput:
        """
        执行查询

        Args:
            query: 用户查询语句
            curl: curl 请求模板
            system_prompt: 系统提示词
            max_attempts: 最大尝试次数（默认5）
            timeout: HTTP 请求超时时间（默认30秒）
            llm_model: LLM 模型名称（默认gpt-4o）
            llm_temperature: LLM 温度参数（默认0）
            return_raw_response: 是否返回原始接口响应（默认False）
            result_selector: 结果选择器（JSONPath 或字段路径）

        Returns:
            QueryAgentOutput: 查询结果，data 字段保持与原接口数据结构一致
        """
        logger.info(f"[QueryAgent] 开始执行查询: {query[:50]}...")

        # 解析 curl
        try:
            parsed_curl = CurlParser.parse(curl)
            logger.info(f"[QueryAgent] Curl 解析成功，可用字段: {parsed_curl.placeholder_fields}")
        except Exception as e:
            logger.error(f"[QueryAgent] Curl 解析失败: {e}")
            return QueryAgentOutput(
                success=False,
                data=None,
                attempts=0,
                reasoning=f"Curl 解析失败: {e}",
                is_satisfied=False
            )

        # 根据配置初始化 LLM（每次调用都根据传入的模型参数创建）
        if self.llm is None or llm_model != getattr(self.llm, 'model_name', None) or llm_temperature != getattr(self.llm, 'temperature', None):
            logger.info(f"[QueryAgent] 初始化 LLM 模型: {llm_model}, temperature: {llm_temperature}")
            self.llm = self._get_or_create_llm(model=llm_model, temperature=llm_temperature)
            self.nodes = QueryNodes(self.llm)
            self.workflow = self._build_workflow()

        # 初始化状态
        initial_state: QueryAgentState = {
            "query": query,
            "curl_template": curl,  # 保存原始 curl 模板用于 curl-session
            "parsed_curl": parsed_curl,
            "system_prompt": system_prompt,
            "max_attempts": max_attempts,
            "timeout": timeout,
            "llm_model": llm_model,
            "llm_temperature": llm_temperature,
            "return_raw_response": return_raw_response,
            "result_selector": result_selector,
            "current_parameters": {},
            "current_results": None,
            "search_history": [],
            "attempt_count": 0,
            "final_result": None,
            "final_raw_response": None,
            "final_reasoning": "",
            "is_satisfied": False,
            "messages": []
        }

        try:
            # 执行工作流
            result = self.workflow.invoke(initial_state)

            # 构建输出 - 保持与原接口数据结构一致
            output_data = result.get("final_result")

            # 如果配置了 result_selector，尝试提取特定字段
            if result_selector and output_data:
                output_data = extract_by_selector(output_data, result_selector)

            final_output = QueryAgentOutput(
                success=result.get("is_satisfied", False),
                data=output_data,
                raw_response=result.get("final_raw_response") if return_raw_response else None,
                attempts=result.get("attempt_count", 0),
                history=result.get("search_history", []),
                reasoning=result.get("final_reasoning", ""),
                final_parameters=result.get("current_parameters", {}),
                is_satisfied=result.get("is_satisfied", False)
            )

            logger.info(f"[QueryAgent] 查询完成: success={final_output.success}, attempts={final_output.attempts}")
            return final_output

        except Exception as e:
            logger.error(f"[QueryAgent] 工作流执行失败: {e}")
            return QueryAgentOutput(
                success=False,
                data=None,
                attempts=0,
                reasoning=f"执行失败: {e}",
                is_satisfied=False
            )

    async def arun(
        self,
        query: str,
        curl: str,
        system_prompt: str,
        max_attempts: int = 5,
        timeout: int = 30,
        llm_model: str = "C4AI-Command-R-Plus",
        llm_temperature: float = 0.0,
        return_raw_response: bool = False,
        result_selector: Optional[str] = None,
        **kwargs
    ) -> QueryAgentOutput:
        """异步执行查询（当前版本使用同步方式）"""
        # 当前版本使用同步实现
        return self.run(
            query=query,
            curl=curl,
            system_prompt=system_prompt,
            max_attempts=max_attempts,
            timeout=timeout,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            return_raw_response=return_raw_response,
            result_selector=result_selector,
            **kwargs
        )

    def run_with_input(self, input_data: QueryAgentInput) -> QueryAgentOutput:
        """
        使用 QueryAgentInput 对象执行查询

        Args:
            input_data: QueryAgentInput 对象

        Returns:
            QueryAgentOutput: 查询结果
        """
        return self.run(
            query=input_data.query,
            curl=input_data.curl,
            system_prompt=input_data.system_prompt,
            max_attempts=input_data.max_attempts,
            timeout=input_data.timeout,
            llm_model=input_data.llm_model,
            llm_temperature=input_data.llm_temperature,
            return_raw_response=input_data.return_raw_response,
            result_selector=input_data.result_selector
        )
