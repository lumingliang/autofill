# 通用数据查询Agent实施文档（简化版）

## 1. 概述

### 1.2 核心能力
- **动态API工具生成**：根据OpenAPI规范自动创建可调用工具
- **Agent自主决策**：Agent自主决策是否调用工具、是否满足用户需求、是否退出
- **多轮交互支持**：查询结果返回给Agent，由Agent决定继续查询或返回结果
- **结果返回调用方**：原始API响应数据返回给调用方

### 1.3 输入输出
- **输入**：
  - `query`: 用户查询语句（从聊天记录提取）
  - `doc`: OpenAPI规范文档（JSON/YAML格式）
- **输出**：
  - `agent_decision`: Agent决策结果（继续/退出）
  - `api_response`: 原始API响应数据（JSON）
  - `formatted_result`: 格式化后的查询结果（可选）

---

## 2. 系统架构（简化版）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           用户查询层                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────┐  │
│  │  聊天记录    │    │  Query提取  │───▶│  "查询北京比亚迪门店"          │  │
│  └─────────────┘    └─────────────┘    └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         OpenAPI解析器层                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  OpenAPI Spec Parser                                             │   │
│  │  ├── 解析Paths (API端点)                                          │   │
│  │  ├── 解析Schemas (请求/响应结构)                                   │   │
│  │  ├── 解析Parameters (参数定义)                                    │   │
│  │  └── 解析Security (认证方式)                                      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Tool Generator                                                  │   │
│  │  └── 为每个API端点生成LangChain Tool                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Agent执行器层（核心）                             │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Agent Loop                                                      │   │
│  │                                                                  │   │
│  │  第1轮：                                                         │   │
│  │    User Input: "查询北京比亚迪门店"                               │   │
│  │    Agent Thought: 需要调用search_dealers工具，参数city="北京"     │   │
│  │    Agent Action: 调用API                                          │   │
│  │    API Response: {原始JSON数据}                                   │   │
│  │                                                                  │   │
│  │  第2轮（反馈给Agent）：                                           │   │
│  │    User Input: "API返回了{原始JSON数据}，是否满足用户需求？"       │   │
│  │    Agent Thought: 分析结果...                                     │   │
│  │    ├─ 满足 → Final Answer                                         │   │
│  │    └─ 不满足 → 继续调用工具（如分页、过滤等）                      │   │
│  │                                                                  │   │
│  │  退出条件：                                                       │   │
│  │    1. 结果满足用户需求                                            │   │
│  │    2. 达到最大迭代次数                                            │   │
│  │    3. 无法获取更多有效数据                                        │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  返回调用方                                                       │   │
│  │  {                                                               │   │
│  │    "agent_decision": "complete",  // complete / continue         │   │
│  │    "api_response": {原始API响应JSON},                            │   │
│  │    "formatted_result": "格式化后的结果",                         │   │
│  │    "reasoning": "Agent的决策理由"                                │   │
│  │  }                                                               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心模块实现

### 3.1 OpenAPI解析与Tool生成

```python
from typing import Dict, List, Any, Optional
import requests
import yaml
import json
from langchain.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, create_model


class OpenAPIParser:
    """OpenAPI规范解析器"""
    
    def __init__(self, spec_source: str):
        self.spec = self._load_spec(spec_source)
        self.base_url = self._get_base_url()
        
    def _load_spec(self, source: str) -> Dict:
        if source.startswith(('http://', 'https://')):
            response = requests.get(source)
            response.raise_for_status()
            content = response.text
        else:
            with open(source, 'r', encoding='utf-8') as f:
                content = f.read()
        
        if content.strip().startswith('{'):
            return json.loads(content)
        return yaml.safe_load(content)
    
    def _get_base_url(self) -> str:
        servers = self.spec.get('servers', [])
        if servers:
            return servers[0].get('url', '')
        return ''
    
    def get_endpoints(self) -> List[Dict]:
        """提取所有API端点"""
        endpoints = []
        paths = self.spec.get('paths', {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    endpoints.append({
                        'path': path,
                        'method': method.upper(),
                        'operation_id': details.get('operationId', ''),
                        'summary': details.get('summary', ''),
                        'description': details.get('description', ''),
                        'parameters': details.get('parameters', []),
                        'request_body': details.get('requestBody', {}),
                    })
        return endpoints
```

### 3.2 API Tool实现

```python
class APITool:
    """API调用工具"""
    
    def __init__(self, parser: OpenAPIParser, api_key: Optional[str] = None):
        self.parser = parser
        self.api_key = api_key
        self.base_url = parser.base_url
        
    def create_tools(self) -> List[BaseTool]:
        """创建所有API工具"""
        endpoints = self.parser.get_endpoints()
        tools = []
        
        for endpoint in endpoints:
            tool = self._create_tool(endpoint)
            if tool:
                tools.append(tool)
        
        return tools
    
    def _create_tool(self, endpoint: Dict) -> Optional[BaseTool]:
        """为单个端点创建Tool"""
        operation_id = endpoint['operation_id'] or f"{endpoint['method']}_{endpoint['path']}"
        
        # 构建参数Schema
        args_schema = self._build_args_schema(endpoint)
        
        def api_caller(**kwargs) -> str:
            """执行API调用"""
            url = f"{self.base_url}{endpoint['path']}"
            method = endpoint['method'].lower()
            
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            
            try:
                if method == 'get':
                    response = requests.request(method, url, headers=headers, params=kwargs)
                else:
                    response = requests.request(method, url, headers=headers, json=kwargs)
                
                response.raise_for_status()
                return response.text  # 返回原始JSON字符串
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        return StructuredTool.from_function(
            func=api_caller,
            name=operation_id,
            description=self._build_description(endpoint),
            args_schema=args_schema,
            return_direct=False
        )
    
    def _build_args_schema(self, endpoint: Dict) -> type[BaseModel]:
        """构建参数Schema"""
        fields = {}
        type_mapping = {'string': str, 'integer': int, 'number': float, 'boolean': bool, 'array': list}
        
        # Path/Query参数
        for param in endpoint.get('parameters', []):
            name = param['name']
            ptype = param.get('schema', {}).get('type', 'string')
            desc = param.get('description', '')
            required = param.get('required', False)
            
            py_type = type_mapping.get(ptype, str)
            if required:
                fields[name] = (py_type, Field(description=desc))
            else:
                fields[name] = (Optional[py_type], Field(default=None, description=desc))
        
        # Body参数
        request_body = endpoint.get('request_body', {})
        if request_body:
            content = request_body.get('content', {})
            schema = content.get('application/json', {}).get('schema', {})
            if schema.get('type') == 'object':
                for name, prop in schema.get('properties', {}).items():
                    if name not in fields:
                        ptype = prop.get('type', 'string')
                        desc = prop.get('description', '')
                        required = name in schema.get('required', [])
                        py_type = type_mapping.get(ptype, str)
                        
                        if required:
                            fields[name] = (py_type, Field(description=desc))
                        else:
                            fields[name] = (Optional[py_type], Field(default=None, description=desc))
        
        return create_model(f"{endpoint['operation_id']}Args", **fields)
    
    def _build_description(self, endpoint: Dict) -> str:
        """构建工具描述"""
        lines = [
            f"API: {endpoint['summary']}",
            f"描述: {endpoint['description']}",
            f"方法: {endpoint['method']} {endpoint['path']}",
        ]
        
        if endpoint['parameters']:
            lines.append("参数:")
            for p in endpoint['parameters']:
                req = "必填" if p.get('required') else "可选"
                lines.append(f"  - {p['name']}({req}): {p.get('description', '')}")
        
        return "\n".join(lines)
```

### 3.3 核心Agent实现（简化版）

```python
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser


class QueryResult(BaseModel):
    """查询结果结构"""
    agent_decision: str = Field(description="决策结果: complete/continue/need_more_info")
    api_response: Optional[Dict] = Field(description="原始API响应数据")
    formatted_result: Optional[str] = Field(description="格式化后的结果")
    reasoning: str = Field(description="决策理由")


class DataQueryAgent:
    """通用数据查询Agent - 简化版"""
    
    def __init__(
        self,
        llm: ChatOpenAI,
        openapi_spec: str,
        api_key: Optional[str] = None,
        max_iterations: int = 5
    ):
        self.llm = llm
        self.max_iterations = max_iterations
        
        # 解析OpenAPI并创建工具
        self.parser = OpenAPIParser(openapi_spec)
        self.tools = APITool(self.parser, api_key).create_tools()
        
        # 创建Agent
        self.agent = self._create_agent()
    
    def _create_agent(self):
        """创建Agent"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能数据查询助手。你的任务是根据用户需求调用工具查询数据，并判断结果是否满足需求。

## 可用工具
{tools}

## 工作流程

1. **分析用户需求**：理解用户想要什么数据
2. **调用工具**：选择合适的工具，提取参数并调用
3. **接收结果**：获取API返回的原始数据
4. **决策判断**：
   - 如果结果满足用户需求 → 返回 complete
   - 如果结果不满足（需要更多数据、需要过滤等）→ 返回 continue
   - 如果缺少必要信息无法查询 → 返回 need_more_info

## 输出格式

你必须按以下JSON格式返回：

```json
{
  "agent_decision": "complete/continue/need_more_info",
  "formatted_result": "格式化后的查询结果（仅complete时填写）",
  "reasoning": "你的决策理由"
}
```

## 注意事项
- 参数值从用户query中提取，不要编造
- API响应是原始JSON，你需要解析并判断
- 如果用户query包含"前N条"、"显示X个"等限制，请遵守
- 如果查询无结果，说明情况并返回complete
"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        return create_openai_functions_agent(self.llm, self.tools, prompt)
    
    def query(self, user_query: str, chat_history: Optional[List[Dict]] = None) -> Dict:
        """
        执行查询
        
        Args:
            user_query: 用户查询语句
            chat_history: 聊天记录
            
        Returns:
            {
                "agent_decision": "complete/continue/need_more_info",
                "api_response": {...},  # 原始API响应
                "formatted_result": "...",
                "reasoning": "...",
                "iterations": [...]  # 每轮迭代记录
            }
        """
        agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            max_iterations=self.max_iterations,
            verbose=True,
            return_intermediate_steps=True
        )
        
        iterations = []
        current_query = user_query
        final_api_response = None
        
        for i in range(self.max_iterations):
            # 执行Agent
            result = agent_executor.invoke({
                "input": current_query,
                "chat_history": self._format_chat_history(chat_history or [])
            })
            
            # 提取API响应（从intermediate_steps）
            api_response = self._extract_api_response(result.get('intermediate_steps', []))
            if api_response:
                final_api_response = api_response
            
            # 解析Agent决策
            output = result.get('output', '')
            decision = self._parse_decision(output)
            
            iteration_record = {
                "round": i + 1,
                "query": current_query,
                "api_response": api_response,
                "agent_output": output,
                "decision": decision
            }
            iterations.append(iteration_record)
            
            # 判断是否需要继续
            if decision.get('agent_decision') == 'complete':
                return {
                    "agent_decision": 'complete',
                    "api_response": final_api_response,
                    "formatted_result": decision.get('formatted_result', ''),
                    "reasoning": decision.get('reasoning', ''),
                    "iterations": iterations
                }
            
            elif decision.get('agent_decision') == 'need_more_info':
                return {
                    "agent_decision": 'need_more_info',
                    "api_response": final_api_response,
                    "formatted_result": None,
                    "reasoning": decision.get('reasoning', ''),
                    "iterations": iterations
                }
            
            # 继续下一轮：将API结果反馈给Agent
            current_query = f"""API返回结果：{json.dumps(api_response, ensure_ascii=False)}

请判断：
1. 这个结果是否满足原始用户需求"{user_query}"？
2. 如果不满足，还需要做什么？
3. 如果满足，请格式化结果并返回complete。

请按指定JSON格式返回决策。"""
        
        # 达到最大迭代次数
        return {
            "agent_decision": 'complete',
            "api_response": final_api_response,
            "formatted_result": "已达到最大迭代次数",
            "reasoning": f"达到最大迭代次数({self.max_iterations})",
            "iterations": iterations
        }
    
    def _extract_api_response(self, intermediate_steps: List) -> Optional[Dict]:
        """从执行步骤中提取API响应"""
        for step in intermediate_steps:
            if len(step) >= 2:
                action, observation = step[0], step[1]
                # observation是API返回的JSON字符串
                try:
                    return json.loads(observation)
                except:
                    return {"raw_response": observation}
        return None
    
    def _parse_decision(self, output: str) -> Dict:
        """解析Agent决策"""
        try:
            # 尝试从输出中提取JSON
            if '```json' in output:
                json_str = output.split('```json')[1].split('```')[0]
            elif '```' in output:
                json_str = output.split('```')[1].split('```')[0]
            else:
                json_str = output
            
            return json.loads(json_str.strip())
        except:
            # 如果解析失败，根据关键词判断
            if 'complete' in output.lower():
                return {"agent_decision": "complete", "reasoning": output}
            elif 'continue' in output.lower():
                return {"agent_decision": "continue", "reasoning": output}
            else:
                return {"agent_decision": "complete", "reasoning": output}
    
    def _format_chat_history(self, history: List[Dict]) -> List:
        """格式化聊天记录"""
        messages = []
        for msg in history:
            if msg.get('role') == 'user':
                messages.append(HumanMessage(content=msg.get('content', '')))
            elif msg.get('role') == 'assistant':
                messages.append(AIMessage(content=msg.get('content', '')))
        return messages
```

### 3.4 完整使用示例

```python
# main.py
from langchain_openai import ChatOpenAI
from data_query_agent import DataQueryAgent
import json


def main():
    # 初始化LLM
    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0,
        api_key="your-openai-api-key"
    )
    
    # 初始化Agent
    agent = DataQueryAgent(
        llm=llm,
        openapi_spec="/path/to/byd-dealers-api.yaml",
        api_key="your-byd-api-key",
        max_iterations=3
    )
    
    # 执行查询
    result = agent.query(
        user_query="查询北京的比亚迪门店，显示前5条",
        chat_history=[]
    )
    
    # 输出结果
    print("=" * 50)
    print(f"Agent决策: {result['agent_decision']}")
    print(f"决策理由: {result['reasoning']}")
    print("=" * 50)
    print("原始API响应:")
    print(json.dumps(result['api_response'], ensure_ascii=False, indent=2))
    print("=" * 50)
    print("格式化结果:")
    print(result['formatted_result'])
    print("=" * 50)
    print(f"迭代次数: {len(result['iterations'])}")
    for it in result['iterations']:
        print(f"  第{it['round']}轮: {it['decision'].get('agent_decision')}")


if __name__ == "__main__":
    main()
```

### 3.5 返回结果示例

```json
{
  "agent_decision": "complete",
  "api_response": {
    "success": true,
    "data": [
      {
        "id": 1,
        "name": "北京盛世路骐汽车销售有限公司",
        "city": "北京市",
        "address": "北京市朝阳区XX路XX号",
        "phone": "010-12345678",
        "service_types": ["销售", "售后"]
      },
      {
        "id": 2,
        "name": "北京环耀盛合汽车销售有限公司",
        "city": "北京市",
        "address": "北京市海淀区XX路XX号",
        "phone": "010-87654321",
        "service_types": ["销售"]
      }
    ],
    "total": 15,
    "query": "北京"
  },
  "formatted_result": "查询结果（共15条，显示前5条）：\n\n1. 北京盛世路骐汽车销售有限公司\n   地址: 北京市朝阳区XX路XX号\n   电话: 010-12345678\n   服务: 销售, 售后\n\n2. 北京环耀盛合汽车销售有限公司\n   地址: 北京市海淀区XX路XX号\n   电话: 010-87654321\n   服务: 销售",
  "reasoning": "成功查询到北京地区的比亚迪门店，结果满足用户需求，已格式化输出前5条数据。",
  "iterations": [
    {
      "round": 1,
      "query": "查询北京的比亚迪门店，显示前5条",
      "api_response": {...},
      "agent_output": "...",
      "decision": {"agent_decision": "complete", ...}
    }
  ]
}
```

---

## 4. 多轮对话流程示例

### 场景1：单次查询满足需求

```
用户: 查询北京的比亚迪门店

Agent第1轮:
  Thought: 用户想查询北京的比亚迪门店，需要调用search_dealers工具
  Action: search_dealers(city="北京", limit=10)
  Observation: {API返回15条数据}
  
Agent决策: complete
  Reasoning: 成功获取到北京地区15家门店数据，满足用户需求

返回调用方:
  agent_decision: complete
  api_response: {原始JSON}
  formatted_result: "查询结果（共15条）..."
```

### 场景2：需要分页获取更多数据

```
用户: 查询上海的所有比亚迪门店

Agent第1轮:
  Thought: 用户想查询上海的所有门店
  Action: search_dealers(city="上海", limit=50)
  Observation: {返回50条，total=120}
  
Agent决策: continue
  Reasoning: 只获取到50条，但总共有120条，需要继续查询

Agent第2轮:
  Thought: 需要获取更多数据
  Action: search_dealers(city="上海", limit=50, offset=50)
  Observation: {返回50条}
  
Agent决策: continue
  Reasoning: 还需要获取更多数据

Agent第3轮:
  Thought: 继续获取剩余数据
  Action: search_dealers(city="上海", limit=50, offset=100)
  Observation: {返回20条}
  
Agent决策: complete
  Reasoning: 已获取全部120条数据

返回调用方:
  agent_decision: complete
  api_response: {合并后的完整数据}
  formatted_result: "查询结果（共120条）..."
```

### 场景3：需要更多信息

```
用户: 查询门店

Agent第1轮:
  Thought: 用户想查询门店，但没有指定城市或其他条件
  Action: 无需调用工具
  
Agent决策: need_more_info
  Reasoning: 缺少查询条件，需要知道用户想查询哪个城市的门店

返回调用方:
  agent_decision: need_more_info
  api_response: null
  formatted_result: null
  reasoning: "请告诉我您想查询哪个城市的门店？"
```

---

## 5. 项目结构

```
data-query-agent/
├── src/
│   ├── __init__.py
│   ├── agent.py              # 主Agent实现（简化版）
│   ├── openapi_parser.py     # OpenAPI解析器
│   ├── api_tool.py           # API工具生成
│   └── utils.py              # 工具函数
├── config/
│   └── settings.py
├── examples/
│   └── byd_example.py
├── requirements.txt
└── README.md
```

---

## 6. 依赖安装

```bash
# requirements.txt
langchain>=0.1.0
langchain-openai>=0.0.5
openai>=1.0.0
pydantic>=2.0.0
pyyaml>=6.0
requests>=2.31.0
```

---

## 7. 与上一版的主要区别

| 特性 | 上一版 | 简化版 |
|------|--------|--------|
| 意图提取 | 独立模块 | 集成到Agent |
| 参数映射 | 独立模块 | Agent自主提取 |
| 决策流程 | 意图→Agent | Agent直接决策 |
| 结果反馈 | 单轮 | 多轮反馈给Agent |
| 返回数据 | 仅格式化结果 | 原始API响应+格式化结果 |
| 架构复杂度 | 高 | 低 |
