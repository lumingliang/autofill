"""
工作流节点实现
"""
import json
from typing import Any, Dict, List

import httpx
from langchain_openai import ChatOpenAI

from app.log import getLogger

from .types import QueryAgentState, SearchAttempt, LLMResponseError
from .utils import (
    replace_placeholders,
    replace_placeholders_in_curl,
    clean_json_response,
    truncate_data_for_llm,
    extract_by_selector
)
from .prompts import (
    format_extract_params_prompt,
    format_analyze_results_prompt,
    format_optimize_params_prompt
)
from .parser import CurlParser

logger = getLogger(__name__)


class QueryNodes:
    """查询 Agent 工作流节点"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def extract_params(self, state: QueryAgentState) -> QueryAgentState:
        """从用户 query 中提取初始搜索参数 - 使用 Function Calling"""
        logger.info("[extract_params] 开始提取参数")

        parsed_curl = state["parsed_curl"]
        placeholder_fields = parsed_curl.placeholder_fields

        if not placeholder_fields:
            logger.warning("[extract_params] 没有可用的占位符字段")
            return {
                **state,
                "current_parameters": {},
                "attempt_count": 0,
                "search_history": []
            }

        # 从 curl 解析结果中获取参数结构，动态构建 FC 调用的参数
        param_schema = parsed_curl.param_schema or {}

        # 构建 Function Calling 的 properties
        properties = {}
        required = []

        for field in placeholder_fields:
            if field in param_schema:
                # 使用从 curl 解析出的参数描述
                schema = param_schema[field]
                properties[field] = {
                    "type": schema.get("type", "string"),
                    "description": schema.get("description", f"{field}参数的值")
                }
            else:
                # 默认描述
                properties[field] = {
                    "type": "string",
                    "description": f"从用户输入中提取的 {field} 信息"
                }
            # 所有占位符字段都设为必填
            required.append(field)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "extract_search_params",
                    "description": f"从用户输入中提取搜索参数，用于调用 {parsed_curl.url} 接口",
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            }
        ]

        try:
            # 构建 system_prompt，指导 LLM 如何从聊天记录中提取参数
            param_descriptions = []
            for field in placeholder_fields:
                prop = properties.get(field, {})
                if isinstance(prop, dict):
                    desc = prop.get("description", f"{field}参数的值")
                else:
                    desc = f"{field}参数的值"
                param_descriptions.append(f"- {field}: {desc}")

            fc_system_prompt = f"""{state["system_prompt"]}

你的任务是从用户的输入中提取以下参数，用于调用搜索接口：

{chr(10).join(param_descriptions)}

请仔细分析用户的输入，提取最准确的参数值，以便能够查询到正确的结果。
如果某个参数无法从输入中直接获取，请根据上下文推断最可能的值。
"""

            # 使用 Function Calling
            messages = [
                {"role": "system", "content": fc_system_prompt},
                {"role": "user", "content": state["query"]}
            ]

            response = self.llm.invoke(
                messages,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "extract_search_params"}}
            )

            # 提取 FC 调用参数
            parameters = {}

            # 方式1: 从 response.tool_calls 获取 (LangChain 新版本)
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_call = response.tool_calls[0]
                parameters = tool_call.get("args", {})
                reasoning = f"FC提取参数: {list(parameters.keys())}"
            # 方式2: 从 additional_kwargs 获取 (旧版本)
            elif response.additional_kwargs.get("tool_calls"):
                tool_calls = response.additional_kwargs.get("tool_calls", [])
                function_args = tool_calls[0]["function"]["arguments"]
                if isinstance(function_args, str):
                    parameters = json.loads(function_args)
                else:
                    parameters = function_args
                reasoning = f"FC提取参数: {list(parameters.keys())}"
            else:
                reasoning = "FC未返回参数"

            logger.info(f"[extract_params] 提取参数: {parameters}, 原因: {reasoning}")

            return {
                **state,
                "current_parameters": parameters,
                "attempt_count": 0,
                "search_history": []
            }
        except Exception as e:
            logger.error(f"[extract_params] 提取参数失败: {e}")
            return {
                **state,
                "current_parameters": {},
                "attempt_count": 0,
                "search_history": []
            }

    def search(self, state: QueryAgentState) -> QueryAgentState:
        """执行 HTTP 搜索"""
        logger.info("[search] 开始执行搜索")

        parsed_curl = state["parsed_curl"]
        parameters = state["current_parameters"]
        timeout = state.get("timeout", 30)

        # 构建请求数据
        request_data = None
        if parsed_curl.body_template:
            request_data = replace_placeholders(parsed_curl.body_template, parameters)

        # 构建查询参数
        query_params = None
        if parsed_curl.query_params_template:
            query_params = replace_placeholders(parsed_curl.query_params_template, parameters)

        try:
            # 使用 curl-session 发送请求
            results = self._execute_with_curl_session(
                curl_template=state["curl_template"],
                parameters=parameters,
                timeout=timeout
            )

            # 提取结果列表
            result_list = self._extract_result_list(results)

            logger.info(f"[search] 搜索成功，返回 {len(result_list)} 条结果")

            # 记录搜索历史
            attempt = SearchAttempt(
                attempt_number=state["attempt_count"] + 1,
                parameters=parameters.copy(),
                result_count=len(result_list),
                selected_indices=[],
                reasoning="",
                raw_response=results if state.get("return_raw_response") else None
            )

            return {
                **state,
                "current_results": results,
                "attempt_count": state["attempt_count"] + 1,
                "search_history": state["search_history"] + [attempt]
            }

        except httpx.TimeoutException:
            logger.error(f"[search] 请求超时")
            # 记录失败的历史
            attempt = SearchAttempt(
                attempt_number=state["attempt_count"] + 1,
                parameters=parameters.copy(),
                result_count=0,
                selected_indices=[],
                reasoning="请求超时"
            )
            return {
                **state,
                "current_results": {"error": "timeout"},
                "attempt_count": state["attempt_count"] + 1,
                "search_history": state["search_history"] + [attempt]
            }
        except Exception as e:
            logger.error(f"[search] 搜索失败: {e}")
            # 记录失败的历史
            attempt = SearchAttempt(
                attempt_number=state["attempt_count"] + 1,
                parameters=parameters.copy(),
                result_count=0,
                selected_indices=[],
                reasoning=f"请求失败: {str(e)}"
            )
            return {
                **state,
                "current_results": {"error": str(e)},
                "attempt_count": state["attempt_count"] + 1,
                "search_history": state["search_history"] + [attempt]
            }

    def _execute_with_curl_session(
        self,
        curl_template: str,
        parameters: Dict[str, Any],
        timeout: int = 30
    ) -> Any:
        """
        使用 curl-session 执行 HTTP 请求

        Args:
            curl_template: curl 命令模板
            parameters: 要替换的参数字典
            timeout: 超时时间（秒）

        Returns:
            解析后的 JSON 响应
        """
        # 替换 curl 模板中的占位符
        curl_command = replace_placeholders_in_curl(curl_template, parameters)

        # 使用 curl-session 创建 session
        cs = CurlParser.create_session(curl_command)

        # 使用 httpx 发送请求（curl-session 支持 httpx）
        with cs.get_httpx_client() as client:
            # 构建请求
            method = cs._parsed.method
            url = cs._parsed.url

            # 准备请求参数
            request_kwargs = {
                "headers": cs._parsed.headers,
                "timeout": timeout,
            }

            # 添加 body 数据
            if cs._parsed.data and method != "GET":
                if isinstance(cs._parsed.data, str):
                    try:
                        import json
                        request_kwargs["json"] = json.loads(cs._parsed.data)
                    except json.JSONDecodeError:
                        request_kwargs["content"] = cs._parsed.data
                else:
                    request_kwargs["data"] = cs._parsed.data

            # 发送请求
            response = client.request(method, url, **request_kwargs)
            response.raise_for_status()
            return response.json()

    def _extract_result_list(self, results: Any) -> List:
        """从响应中提取结果列表"""
        if isinstance(results, list):
            return results
        if isinstance(results, dict):
            # 常见的响应格式
            for key in ["data", "items", "list", "results", "records"]:
                if key in results:
                    data = results[key]
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and "list" in data:
                        return data["list"]
            # 如果没有找到列表，返回空列表
            return []
        return []

    def analyze_results(self, state: QueryAgentState) -> QueryAgentState:
        """分析搜索结果"""
        logger.info("[analyze_results] 开始分析结果")

        current_results = state.get("current_results", {})

        # 如果有错误，直接标记为不满意
        if isinstance(current_results, dict) and "error" in current_results:
            logger.warning(f"[analyze_results] 搜索结果有误: {current_results['error']}")
            return {
                **state,
                "is_satisfied": False,
                "final_reasoning": f"搜索失败: {current_results['error']}"
            }

        # 提取结果列表
        result_list = self._extract_result_list(current_results)

        if not result_list:
            logger.info("[analyze_results] 没有搜索结果")
            return {
                **state,
                "is_satisfied": False,
                "final_reasoning": "没有找到任何结果"
            }

        # 截断数据以适应 LLM
        truncated_results = truncate_data_for_llm(result_list, max_length=4000)

        prompt = format_analyze_results_prompt(
            query=state["query"],
            system_prompt=state["system_prompt"],
            current_parameters=state["current_parameters"],
            results=truncated_results,
            result_count=len(result_list)
        )

        try:
            response = self.llm.invoke([("system", prompt)])
            content = clean_json_response(response.content)
            analysis = json.loads(content)

            is_satisfied = analysis.get("is_satisfied", False)
            selected_indices = analysis.get("selected_indices", [])
            reasoning = analysis.get("reasoning", "")
            suggestion = analysis.get("suggestion", "")

            logger.info(f"[analyze_results] 分析结果: satisfied={is_satisfied}, indices={selected_indices}")

            # 更新最后一次搜索历史的 reasoning
            search_history = state["search_history"]
            if search_history:
                last_attempt = search_history[-1]
                last_attempt.reasoning = reasoning
                last_attempt.selected_indices = selected_indices

            # 如果满意，提取最终结果
            final_result = None
            final_raw_response = None
            if is_satisfied and selected_indices:
                if len(selected_indices) == 1:
                    idx = selected_indices[0]
                    if 0 <= idx < len(result_list):
                        final_result = result_list[idx]
                else:
                    final_result = [result_list[i] for i in selected_indices if 0 <= i < len(result_list)]

                # 保存原始响应
                final_raw_response = current_results

            return {
                **state,
                "is_satisfied": is_satisfied,
                "final_result": final_result,
                "final_raw_response": final_raw_response,
                "final_reasoning": reasoning,
                "_analysis": analysis,  # 临时存储，用于优化节点
                "search_history": search_history
            }

        except json.JSONDecodeError as e:
            logger.error(f"[analyze_results] JSON 解析失败: {e}, content: {content}")
            return {
                **state,
                "is_satisfied": False,
                "final_reasoning": f"分析结果解析失败: {e}"
            }
        except Exception as e:
            logger.error(f"[analyze_results] 分析失败: {e}")
            return {
                **state,
                "is_satisfied": False,
                "final_reasoning": f"分析失败: {e}"
            }

    def optimize_params(self, state: QueryAgentState) -> QueryAgentState:
        """优化搜索参数"""
        logger.info("[optimize_params] 开始优化参数")

        parsed_curl = state["parsed_curl"]
        analysis = state.get("_analysis", {})

        # 格式化搜索历史
        history_str = "\n".join([
            f"尝试 {a.attempt_number}: 参数={a.parameters}, 结果数={a.result_count}, 原因={a.reasoning}"
            for a in state["search_history"]
        ])

        prompt = format_optimize_params_prompt(
            query=state["query"],
            system_prompt=state["system_prompt"],
            search_history=history_str,
            last_analysis=json.dumps(analysis, ensure_ascii=False),
            placeholder_fields=parsed_curl.placeholder_fields
        )

        try:
            response = self.llm.invoke([("system", prompt)])
            content = clean_json_response(response.content)
            result = json.loads(content)

            new_parameters = result.get("parameters", {})
            optimization_reasoning = result.get("optimization_reasoning", "")
            expected_improvement = result.get("expected_improvement", "")

            logger.info(f"[optimize_params] 优化后参数: {new_parameters}")
            logger.info(f"[optimize_params] 优化原因: {optimization_reasoning}")

            return {
                **state,
                "current_parameters": new_parameters
            }

        except json.JSONDecodeError as e:
            logger.error(f"[optimize_params] JSON 解析失败: {e}, content: {content}")
            # 如果解析失败，稍微修改参数继续尝试
            current_params = state["current_parameters"]
            # 尝试清空一些参数来扩大搜索范围
            new_params = {k: v for k, v in current_params.items() if k == "keyword"}
            return {
                **state,
                "current_parameters": new_params
            }
        except Exception as e:
            logger.error(f"[optimize_params] 优化失败: {e}")
            return state

    def should_continue(self, state: QueryAgentState) -> str:
        """判断是否继续搜索"""
        # 如果已满足，结束
        if state.get("is_satisfied", False):
            logger.info("[should_continue] 已找到满意结果，结束")
            return "end"

        # 如果达到最大尝试次数，结束
        max_attempts = state.get("max_attempts", 5)
        if state["attempt_count"] >= max_attempts:
            logger.info(f"[should_continue] 达到最大尝试次数 {max_attempts}，结束")
            return "end"

        # 继续优化
        logger.info(f"[should_continue] 继续优化，当前尝试 {state['attempt_count']}/{max_attempts}")
        return "optimize"
