# 通用查询 Agent 设计文档

## 1. 概述

本设计文档描述一个基于 LangGraph 的通用查询 Agent，用于通过 HTTP 接口查询数据。Agent 支持动态解析 curl 请求，自动识别可搜索字段，并根据用户 query 智能地进行多次尝试直到找到满意结果。

## 2. 核心接口设计

### 2.1 Agent 输入参数

```python
class QueryAgentInput(BaseModel):
    """Agent 输入参数 - 支持调用方自定义关键参数"""
    query: str                          # 用户查询语句
    curl: str                           # curl 请求模板（包含占位符）
    system_prompt: str                  # 系统提示词，定义查询目标和结果判断标准

    # 可配置的关键参数
    max_attempts: int = 5               # 最大尝试次数（可选，默认5次）
    timeout: int = 30                   # HTTP 请求超时时间（秒，可选，默认30秒）
    llm_model: str = "gpt-4o"           # LLM 模型名称（可选）
    llm_temperature: float = 0.0        # LLM 温度参数（可选，默认0）
    return_raw_response: bool = False   # 是否返回原始接口响应（默认False，返回提取的数据）
    result_selector: Optional[str] = None  # 结果选择器（JSONPath 或特定字段路径）
```

### 2.2 Agent 输出结果

```python
class QueryAgentOutput(BaseModel):
    """Agent 输出结果 - 保持与原接口数据结构一致"""
    success: bool                       # 是否找到满意结果
    data: Optional[Any]                 # 最终选中的数据（与原接口返回结构一致）
    raw_response: Optional[Dict]        # 原始接口完整响应（当 return_raw_response=True 时）
    attempts: int                       # 实际尝试次数
    history: List[SearchAttempt]        # 搜索历史记录
    reasoning: str                      # 结果选择的推理说明
    final_parameters: Dict[str, str]    # 最终使用的搜索参数
    is_satisfied: bool                  # 是否满足查询条件

class SearchAttempt(BaseModel):
    """单次搜索尝试记录"""
    attempt_number: int                 # 尝试序号
    parameters: Dict[str, str]          # 本次使用的搜索参数
    result_count: int                   # 返回结果数量
    selected_indices: List[int]         # 选中的结果索引
    reasoning: str                      # 本次选择的推理
    raw_response: Optional[Dict]        # 本次请求的原始响应（可选）
```

## 3. Curl 模板规范

### 3.1 占位符定义

Curl 请求中使用 `{{field_name}}` 格式定义可搜索字段占位符：

```bash
curl -X POST 'https://api.example.com/search' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer token' \
-d '{
    "keyword": "{{keyword}}",
    "city": "{{city}}",
    "category": "{{category}}",
    "pageSize": 20
}'
```

### 3.2 支持的占位符类型

- `{{keyword}}` - 通用搜索关键词
- `{{city}}` - 城市名称
- `{{category}}` - 分类/类型
- `{{start_date}}` / `{{end_date}}` - 日期范围
- `{{status}}` - 状态
- 其他自定义字段

### 3.3 Curl 解析器

```python
class CurlParser:
    """解析 curl 命令，提取 URL、方法、Headers 和占位符字段"""

    @staticmethod
    def parse(curl_str: str) -> ParsedCurl:
        """
        解析 curl 字符串

        Returns:
            ParsedCurl: 包含以下字段
                - url: str
                - method: str
                - headers: Dict[str, str]
                - body_template: Dict (可能包含占位符)
                - query_params_template: Dict (GET 请求的查询参数)
                - placeholder_fields: List[str] (发现的所有占位符字段)
        """
```

## 4. Agent 状态定义

```python
class QueryAgentState(TypedDict):
    """LangGraph 状态定义"""
    # 输入参数
    query: str                          # 用户原始查询
    parsed_curl: ParsedCurl             # 解析后的 curl
    system_prompt: str                  # 系统提示词

    # 可配置参数
    max_attempts: int                   # 最大尝试次数
    timeout: int                        # HTTP 请求超时时间
    llm_model: str                      # LLM 模型名称
    llm_temperature: float              # LLM 温度参数
    return_raw_response: bool           # 是否返回原始响应
    result_selector: Optional[str]      # 结果选择器

    # 执行状态
    current_parameters: Dict[str, str]  # 当前搜索参数
    current_results: Optional[Dict]     # 当前搜索结果（原始响应）
    search_history: List[SearchAttempt] # 搜索历史
    attempt_count: int                  # 当前尝试次数

    # 结果
    final_result: Optional[Any]         # 最终结果（与原接口结构一致）
    final_raw_response: Optional[Dict]  # 最终原始响应
    final_reasoning: str                # 最终推理
    is_satisfied: bool                  # 是否满意

    # 工作流内部使用
    messages: List[Any]                 # LLM 消息历史
```

## 5. 工作流节点设计

### 5.1 节点流程图

```
┌─────────────────┐
│   extract_params │  (提取初始搜索参数)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     search      │  (执行 HTTP 搜索)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ analyze_results │  (分析搜索结果)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐  ┌─────────────┐
│  END  │  │ optimize_params│ (优化搜索参数)
└───────┘  └──────┬──────┘
                  │
                  └──────► (回到 search)
```

### 5.2 节点详细说明

#### 5.2.1 extract_params (参数提取节点)

**功能**：从用户 query 和 system_prompt 中提取初始搜索参数

**Prompt 设计**：

```
System: 你是一个智能参数提取专家。根据用户的查询语句和系统提示词，
从以下可用字段中选择合适的值来构建搜索参数。

可用字段: {placeholder_fields}

系统提示词（定义了查询目标和判断标准）:
{system_prompt}

用户查询:
{query}

要求：
1. 只使用提供的可用字段
2. 如果某个字段无法确定，可以留空或不包含
3. 考虑同义词、简称、可能的拼写变体
4. 返回格式必须是有效的 JSON

返回格式:
{
    "parameters": {
        "field_name": "extracted_value"
    },
    "reasoning": "简要说明为什么选择这些参数"
}
```

#### 5.2.2 search (搜索节点)

**功能**：使用当前参数执行 HTTP 请求

**实现逻辑**：

1. 使用 `CurlParser` 构建实际请求
2. 替换所有占位符为当前参数值
3. 发送 HTTP 请求
4. 记录请求和响应到 search_history

```python
def search_node(state: QueryAgentState) -> QueryAgentState:
    """执行搜索"""
    parsed_curl = state["parsed_curl"]
    parameters = state["current_parameters"]

    # 构建实际请求
    request_data = replace_placeholders(
        parsed_curl.body_template,
        parameters
    )

    # 发送请求
    response = httpx.request(
        method=parsed_curl.method,
        url=parsed_curl.url,
        headers=parsed_curl.headers,
        json=request_data if parsed_curl.method != "GET" else None,
        params=request_data if parsed_curl.method == "GET" else None,
        timeout=state.get("timeout", 30)
    )

    # 解析响应
    results = response.json()

    # 记录到历史
    attempt = SearchAttempt(
        attempt_number=state["attempt_count"] + 1,
        parameters=parameters,
        result_count=len(results.get("data", [])),
        selected_indices=[],
        reasoning=""
    )

    return {
        **state,
        "current_results": results,
        "attempt_count": state["attempt_count"] + 1,
        "search_history": state["search_history"] + [attempt]
    }
```

#### 5.2.3 analyze_results (结果分析节点)

**功能**：分析搜索结果，判断是否满足用户需求

**Prompt 设计**：

```
System: 你是一个数据匹配专家。根据系统提示词中定义的目标，
分析搜索结果，判断是否有满足条件的数据。

系统提示词:
{system_prompt}

用户原始查询:
{query}

当前搜索参数:
{current_parameters}

搜索结果（共 {result_count} 条）:
{results}

请按以下 JSON 格式返回分析结果:
{
    "is_satisfied": true/false,
    "selected_indices": [0, 1],  // 满足条件的记录索引
    "reasoning": "详细说明为什么这些记录满足/不满足条件",
    "suggestion": "如果不满足，建议如何调整搜索参数"
}
```

#### 5.2.4 optimize_params (参数优化节点)

**功能**：根据分析结果，优化搜索参数进行下一次尝试

**Prompt 设计**：

```
System: 你是一个搜索优化专家。根据之前的搜索结果和分析反馈，
优化搜索参数以获得更好的结果。

系统提示词:
{system_prompt}

用户查询:
{query}

搜索历史:
{search_history}

上次分析反馈:
{last_analysis}

可用字段:
{placeholder_fields}

优化策略：
1. 纠正可能的拼写错误
2. 使用同义词或相关词
3. 扩大或缩小搜索范围
4. 尝试不同的字段组合
5. 使用简称或全称

返回格式:
{
    "parameters": {
        "field_name": "new_value"
    },
    "optimization_reasoning": "说明为什么这样优化",
    "expected_improvement": "预期能改善什么"
}
```

### 5.3 条件边

```python
def should_continue(state: QueryAgentState) -> str:
    """判断是否继续搜索"""
    # 如果已满足，结束
    if state.get("is_satisfied", False):
        return "end"

    # 如果达到最大尝试次数，结束
    if state["attempt_count"] >= state["max_attempts"]:
        return "end"

    # 继续优化
    return "optimize"
```

## 6. 核心类设计

### 6.1 QueryAgent 主类

```python
class QueryAgent:
    """
    通用查询 Agent

    使用示例:
        agent = QueryAgent()

        result = agent.run(
            query="查找北京地区的星巴克门店",
            curl="""
            curl -X POST 'https://api.example.com/stores/search' \
            -H 'Content-Type: application/json' \
            -d '{
                "keyword": "{{keyword}}",
                "city": "{{city}}"
            }'
            """,
            system_prompt="""
            目标是找到用户查询的门店信息。
            匹配标准：
            1. 门店名称应与用户查询的品牌一致
            2. 地理位置应在用户指定的城市
            3. 返回最匹配的一条或多条记录
            """
        )
    """

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self.llm = llm or ChatOpenAI(model="gpt-4o", temperature=0)
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        workflow = StateGraph(QueryAgentState)

        # 添加节点
        workflow.add_node("extract_params", self._extract_params)
        workflow.add_node("search", self._search)
        workflow.add_node("analyze_results", self._analyze_results)
        workflow.add_node("optimize_params", self._optimize_params)

        # 设置入口
        workflow.set_entry_point("extract_params")

        # 添加边
        workflow.add_edge("extract_params", "search")
        workflow.add_edge("search", "analyze_results")

        # 条件边
        workflow.add_conditional_edges(
            "analyze_results",
            self._should_continue,
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
        llm_model: str = "gpt-4o",
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
        # 解析 curl
        parsed_curl = CurlParser.parse(curl)

        # 根据配置初始化 LLM
        if llm_model != self.llm.model_name or llm_temperature != self.llm.temperature:
            self.llm = ChatOpenAI(model=llm_model, temperature=llm_temperature)

        # 初始化状态
        initial_state = QueryAgentState(
            query=query,
            parsed_curl=parsed_curl,
            system_prompt=system_prompt,
            max_attempts=max_attempts,
            timeout=timeout,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            return_raw_response=return_raw_response,
            result_selector=result_selector,
            current_parameters={},
            current_results=None,
            search_history=[],
            attempt_count=0,
            final_result=None,
            final_raw_response=None,
            final_reasoning="",
            is_satisfied=False,
            messages=[]
        )

        # 执行工作流
        result = self.workflow.invoke(initial_state)

        # 构建输出 - 保持与原接口数据结构一致
        output_data = result["final_result"]

        # 如果配置了 result_selector，尝试提取特定字段
        if result_selector and output_data:
            output_data = self._extract_by_selector(output_data, result_selector)

        return QueryAgentOutput(
            success=result["is_satisfied"],
            data=output_data,
            raw_response=result["final_raw_response"] if return_raw_response else None,
            attempts=result["attempt_count"],
            history=result["search_history"],
            reasoning=result["final_reasoning"],
            final_parameters=result.get("current_parameters", {}),
            is_satisfied=result["is_satisfied"]
        )

    def _extract_by_selector(self, data: Any, selector: str) -> Any:
        """
        根据选择器提取数据

        支持格式：
        - JSONPath: $.data.items[0]
        - 点号路径: data.items.0
        """
        try:
            if selector.startswith("$."):
                # JSONPath 格式
                import jsonpath_ng
                jsonpath_expr = jsonpath_ng.parse(selector)
                matches = jsonpath_expr.find(data)
                return [match.value for match in matches] if len(matches) > 1 else (matches[0].value if matches else None)
            else:
                # 点号路径格式
                keys = selector.split(".")
                result = data
                for key in keys:
                    if isinstance(result, dict):
                        result = result.get(key)
                    elif isinstance(result, list) and key.isdigit():
                        result = result[int(key)] if int(key) < len(result) else None
                    else:
                        return None
                    if result is None:
                        return None
                return result
        except Exception:
            return data
```

## 7. 工具函数

### 7.1 占位符替换

```python
def replace_placeholders(template: Any, parameters: Dict[str, str]) -> Any:
    """
    递归替换模板中的占位符

    Args:
        template: 可能包含占位符的数据结构
        parameters: 参数键值对

    Returns:
        替换后的数据结构
    """
    if isinstance(template, dict):
        result = {}
        for k, v in template.items():
            if isinstance(v, str):
                # 替换字符串中的占位符
                result[k] = replace_placeholder_in_string(v, parameters)
            else:
                result[k] = replace_placeholders(v, parameters)
        return result
    elif isinstance(template, list):
        return [replace_placeholders(item, parameters) for item in template]
    else:
        return template

def replace_placeholder_in_string(s: str, parameters: Dict[str, str]) -> str:
    """替换字符串中的 {{field}} 占位符"""
    import re
    pattern = r'\{\{(\w+)\}\}'

    def replacer(match):
        field = match.group(1)
        return parameters.get(field, match.group(0))  # 找不到保留原样

    return re.sub(pattern, replacer, s)
```

### 7.2 Curl 解析器

```python
class CurlParser:
    """Curl 命令解析器"""

    PLACEHOLDER_PATTERN = re.compile(r'\{\{(\w+)\}\}')

    @dataclass
    class ParsedCurl:
        url: str
        method: str
        headers: Dict[str, str]
        body_template: Optional[Dict]
        query_params_template: Optional[Dict]
        placeholder_fields: List[str]

    @classmethod
    def parse(cls, curl_str: str) -> ParsedCurl:
        """解析 curl 命令"""
        # 提取 URL
        url_match = re.search(r"curl\s+(?:-X\s+\w+\s+)?['\"]?([^'\"\s]+)['\"]?", curl_str)
        url = url_match.group(1) if url_match else ""

        # 提取方法
        method_match = re.search(r"-X\s+(\w+)", curl_str)
        method = method_match.group(1).upper() if method_match else "GET"

        # 提取 headers
        headers = {}
        for match in re.finditer(r"-H\s+['\"]([^:]+):\s*([^'\"]+)['\"]", curl_str):
            headers[match.group(1).strip()] = match.group(2).strip()

        # 提取 body
        body_template = None
        body_match = re.search(r"-d\s+['\"](.+?)['\"](?:\s+-H|\s+-X|$)", curl_str, re.DOTALL)
        if body_match:
            try:
                body_str = body_match.group(1).replace("\\n", "\n")
                body_template = json.loads(body_str)
            except json.JSONDecodeError:
                body_template = {"raw": body_match.group(1)}

        # 提取查询参数（从 URL）
        query_params_template = None
        if "?" in url:
            url_part, query_part = url.split("?", 1)
            url = url_part
            query_params_template = {}
            for param in query_part.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    query_params_template[k] = v

        # 提取所有占位符字段
        all_text = curl_str
        placeholder_fields = list(set(cls.PLACEHOLDER_PATTERN.findall(all_text)))

        return cls.ParsedCurl(
            url=url,
            method=method,
            headers=headers,
            body_template=body_template,
            query_params_template=query_params_template,
            placeholder_fields=placeholder_fields
        )
```

## 8. 使用示例

### 8.1 基础示例

```python
from app.services.query_agent import QueryAgent

agent = QueryAgent()

result = agent.run(
    query="帮我找深圳南山区的 Apple Store",
    curl="""
    curl -X POST 'https://api.example.com/stores/search' \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer xxx' \
    -d '{
        "keyword": "{{keyword}}",
        "city": "{{city}}",
        "district": "{{district}}"
    }'
    """,
    system_prompt="""
    查询目标是找到符合用户需求的门店。

    匹配标准：
    1. 门店名称或品牌应与用户查询的关键词匹配
    2. 城市应与用户指定的城市一致
    3. 区域（如果有指定）应与用户指定的区域一致
    4. 优先返回最匹配的一条记录

    如果找不到完全匹配的，可以返回部分匹配的结果。
    """
)

if result.success:
    print(f"找到结果: {result.data}")
else:
    print(f"未找到满意结果，尝试了 {result.attempts} 次")
    print(f"搜索历史: {result.history}")
```

### 8.2 复杂查询示例（使用自定义参数）

```python
# 多字段复杂查询，使用自定义参数
result = agent.run(
    query="查找2024年1月在上海举办的已结束的技术会议",
    curl="""
    curl -X POST 'https://api.example.com/events/search' \
    -H 'Content-Type: application/json' \
    -d '{
        "keyword": "{{keyword}}",
        "city": "{{city}}",
        "start_date": "{{start_date}}",
        "end_date": "{{end_date}}",
        "status": "{{status}}",
        "category": "{{category}}"
    }'
    """,
    system_prompt="""
    查询目标是找到符合用户需求的会议活动。

    匹配标准：
    1. 会议主题/名称应包含关键词
    2. 举办城市应与用户指定城市一致
    3. 举办时间应在指定日期范围内
    4. 会议状态应与用户要求一致
    5. 会议类型（如果有指定）应匹配

    注意：
    - 用户可能使用口语化表达，需要理解"技术会议"对应 category="tech"
    - "已结束"对应 status="completed"
    - 日期格式为 YYYY-MM-DD
    """,
    max_attempts=3,                    # 最多尝试3次
    timeout=60,                        # HTTP 超时60秒
    llm_model="gpt-4o-mini",           # 使用轻量级模型
    llm_temperature=0.2,               # 稍微增加一点创造性
    return_raw_response=True,          # 返回原始响应
    result_selector="data.items"       # 提取 data.items 字段
)

# 输出结果保持与原接口数据结构一致
if result.success:
    # result.data 的结构与原接口返回的 data.items 一致
    print(f"找到 {len(result.data)} 条记录")
    for item in result.data:
        print(f"会议: {item['name']}, 城市: {item['city']}")

    # 同时可以访问原始响应
    if result.raw_response:
        print(f"总记录数: {result.raw_response.get('total', 0)}")
```

### 8.3 返回数据结构示例

假设原接口返回结构如下：
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "total": 100,
        "items": [
            {"id": 1, "name": "星巴克", "city": "深圳", "district": "南山区"}
        ]
    }
}
```

使用 `result_selector="data.items"` 后，Agent 返回的 `result.data` 将是：
```python
[
    {"id": 1, "name": "星巴克", "city": "深圳", "district": "南山区"}
]
```

## 9. 错误处理

### 9.1 异常情况

1. **Curl 解析失败**：抛出 `CurlParseError`
2. **HTTP 请求失败**：记录错误，尝试下一次搜索
3. **LLM 解析失败**：重试或返回部分结果
4. **超时**：根据配置决定是否重试

### 9.2 错误码定义

```python
class QueryAgentError(Exception):
    """Agent 基础异常"""
    pass

class CurlParseError(QueryAgentError):
    """Curl 解析异常"""
    pass

class SearchTimeoutError(QueryAgentError):
    """搜索超时异常"""
    pass

class LLMResponseError(QueryAgentError):
    """LLM 响应解析异常"""
    pass
```

## 10. 扩展性设计

### 10.1 自定义 LLM

```python
from langchain_anthropic import ChatAnthropic

# 使用 Claude
agent = QueryAgent(llm=ChatAnthropic(model="claude-3-opus-20240229"))
```

### 10.2 自定义 Prompt

```python
# 通过继承自定义节点行为
class CustomQueryAgent(QueryAgent):
    def _extract_params(self, state: QueryAgentState) -> QueryAgentState:
        # 自定义参数提取逻辑
        pass
```

## 11. 性能考虑

1. **并发控制**：单次查询串行执行，避免对目标 API 造成压力
2. **缓存机制**：可添加 LLM 响应缓存
3. **超时控制**：每个 HTTP 请求独立超时
4. **重试机制**：HTTP 失败时可配置重试策略

## 12. 文件结构

```
app/services/
├── __init__.py
├── query_agent/
│   ├── __init__.py          # 导出 QueryAgent
│   ├── agent.py             # 主 Agent 类
│   ├── parser.py            # Curl 解析器
│   ├── nodes.py             # 工作流节点实现
│   ├── prompts.py           # Prompt 模板
│   ├── utils.py             # 工具函数
│   └── types.py             # 类型定义
```

## 13. 配置参数汇总

### 13.1 调用方可配置参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `max_attempts` | int | 5 | 最大搜索尝试次数 |
| `timeout` | int | 30 | HTTP 请求超时时间（秒） |
| `llm_model` | str | "gpt-4o" | LLM 模型名称 |
| `llm_temperature` | float | 0.0 | LLM 温度参数（0-2） |
| `return_raw_response` | bool | False | 是否返回原始接口响应 |
| `result_selector` | str | None | 结果选择器（JSONPath 或点号路径） |

### 13.2 使用建议

1. **max_attempts**: 根据接口响应速度和成本考虑，建议 3-5 次
2. **timeout**: 根据接口实际情况调整，慢接口可设置为 60 秒
3. **llm_model**: 复杂查询用 gpt-4o，简单查询可用 gpt-4o-mini 降低成本
4. **llm_temperature**: 保持默认 0 以获得稳定结果，需要创造性时可调至 0.2-0.5
5. **return_raw_response**: 需要访问接口完整响应时设为 True
6. **result_selector**: 当只需要接口返回的特定字段时使用，保持输出结构简洁
