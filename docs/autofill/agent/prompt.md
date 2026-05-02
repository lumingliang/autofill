# 高度灵活的门店搜索 Agent（基于通用 HTTP 接口）

这个方案完全基于你提供的单个 curl 请求，Agent 会自主完成关键词提取、接口调用、结果分析、关键词优化的全流程，直到找到满意的门店。

```python
import os
import re
import json
import httpx
from typing import TypedDict, Annotated, List, Dict, Optional, Any
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

# ============ 配置区域 ============
# 在这里配置你从前端复制的 curl 请求
CURL_TEMPLATE = """
curl -X POST 'https://your-api-endpoint.com/api/stores/search' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer YOUR_TOKEN' \
-d '{
    "keyword": "{{keyword}}",
    "pageSize": 20
}'
"""

# 解析 curl 提取配置（自动解析上面的 curl）
def parse_curl(curl_str):
    url = re.search(r"curl\s+['\"]?([^'\"]+)['\"]?", curl_str).group(1)
    method = re.search(r"-X\s+(\w+)", curl_str)
    method = method.group(1) if method else "GET"
    headers = dict(re.findall(r"-H\s+'([^:]+):\s*([^']+)'", curl_str))
    data_match = re.search(r"-d\s+'([^']+)'", curl_str)
    data_template = json.loads(data_match.group(1)) if data_match else {}
    return {
        "url": url,
        "method": method,
        "headers": headers,
        "data_template": data_template
    }

API_CONFIG = parse_curl(CURL_TEMPLATE)

# ============ Agent 状态定义 ============
class AgentState(TypedDict):
    chat_history: str                # 用户输入的聊天记录
    current_keywords: List[str]      # 当前搜索关键词
    search_history: List[Dict]       # 搜索历史记录
    attempt_count: int                # 尝试次数
    final_result: Optional[Dict]      # 最终选中的门店
    messages: List[Any]

# ============ 核心工具：HTTP 搜索 ============
@tool
def search_store_api(keyword: str) -> Dict:
    """
    调用门店搜索接口（根据你提供的 curl 自动适配）
    """
    # 替换数据模板中的关键词
    data = {**API_CONFIG["data_template"]}
    
    # 智能查找并替换关键词字段
    def replace_keyword(obj, kw):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and "{{keyword}}" in v:
                    obj[k] = v.replace("{{keyword}}", kw)
                elif isinstance(v, (dict, list)):
                    replace_keyword(v, kw)
        elif isinstance(obj, list):
            for item in obj:
                replace_keyword(item, kw)
    
    replace_keyword(data, keyword)
    
    # 发送请求
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method=API_CONFIG["method"],
                url=API_CONFIG["url"],
                headers=API_CONFIG["headers"],
                json=data if API_CONFIG["method"] != "GET" else None,
                params=data if API_CONFIG["method"] == "GET" else None
            )
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json()
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============ Agent 核心逻辑 ============
class FlexibleStoreAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.tools = [search_store_api]
        
        # 构建工作流
        workflow = StateGraph(AgentState)
        
        workflow.add_node("extract_keywords", self._extract_keywords)
        workflow.add_node("search", self._search)
        workflow.add_node("analyze_results", self._analyze_results)
        workflow.add_node("optimize_keywords", self._optimize_keywords)
        
        workflow.set_entry_point("extract_keywords")
        
        workflow.add_edge("extract_keywords", "search")
        workflow.add_edge("search", "analyze_results")
        
        workflow.add_conditional_edges(
            "analyze_results",
            self._should_continue,
            {
                "done": END,
                "optimize": "optimize_keywords"
            }
        )
        
        workflow.add_edge("optimize_keywords", "search")
        
        self.app = workflow.compile()
    
    def _extract_keywords(self, state: AgentState) -> AgentState:
        """从聊天记录智能提取初始关键词"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""你是一个关键词提取专家。请从用户的聊天记录中提取用于搜索门店的关键词。

考虑以下类型的关键词：
1. 门店品牌/名称（可能有错别字、简称、昵称）
2. 地理位置（商圈、地标、道路）
3. 门店类型/品类

返回格式：JSON 数组，按优先级排序
示例：["星巴克万象城店", "星巴克", "万象城咖啡店"]"""),
            HumanMessage(content=f"聊天记录：\n{state['chat_history']}")
        ])
        
        response = self.llm.invoke(prompt.format_messages())
        keywords = json.loads(response.content)
        
        return {
            **state,
            "current_keywords": keywords,
            "search_history": [],
            "attempt_count": 0
        }
    
    def _search(self, state: AgentState) -> AgentState:
        """执行搜索（每次取第一个关键词）"""
        current_kw = state["current_keywords"][0]
        result = search_store_api.invoke({"keyword": current_kw})
        
        # 记录搜索历史
        search_history = state["search_history"] + [{
            "keyword": current_kw,
            "result": result
        }]
        
        return {
            **state,
            "search_history": search_history,
            "attempt_count": state["attempt_count"] + 1
        }
    
    def _analyze_results(self, state: AgentState) -> AgentState:
        """智能分析搜索结果"""
        last_search = state["search_history"][-1]
        keyword = last_search["keyword"]
        api_result = last_search["result"]
        
        # 将结果和聊天记录一起给 LLM 分析
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""你是一个门店匹配专家。请分析搜索结果，找出最符合用户需求的门店。

用户需求隐含在聊天记录中，请仔细理解。

请按以下 JSON 格式返回：
{
    "decision": "found|not_found",
    "selected_store": {...},  // 如果 found，填入门店数据
    "reason": "简要说明原因",
    "suggestion": "如果没找到，建议如何修改关键词"
}"""),
            HumanMessage(content=f"""聊天记录：
{state['chat_history']}

搜索关键词：{keyword}

API 返回结果：
{json.dumps(api_result, ensure_ascii=False, indent=2)}

请分析结果：""")
        ])
        
        response = self.llm.invoke(prompt.format_messages())
        analysis = json.loads(response.content)
        
        return {
            **state,
            "final_result": analysis.get("selected_store"),
            "_analysis": analysis  # 临时存储分析结果
        }
    
    def _should_continue(self, state: AgentState) -> str:
        """判断是否继续搜索"""
        analysis = state["_analysis"]
        
        if analysis["decision"] == "found":
            return "done"
        
        # 最多尝试 5 次
        if state["attempt_count"] >= 5:
            return "done"
        
        return "optimize"
    
    def _optimize_keywords(self, state: AgentState) -> AgentState:
        """优化关键词"""
        analysis = state["_analysis"]
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""你是一个搜索优化专家。根据之前的搜索结果和分析，生成新的搜索关键词列表。

考虑：
1. 纠正错别字
2. 使用同义词/简称/全称
3. 扩大或缩小范围
4. 拆分组合关键词

返回 JSON 数组格式。"""),
            HumanMessage(content=f"""聊天记录：
{state['chat_history']}

之前的关键词：{state['current_keywords']}
搜索分析：{json.dumps(analysis, ensure_ascii=False)}

请生成新的关键词列表（至少 3 个）：""")
        ])
        
        response = self.llm.invoke(prompt.format_messages())
        new_keywords = json.loads(response.content)
        
        return {
            **state,
            "current_keywords": new_keywords
        }
    
    def run(self, chat_history: str) -> Dict:
        """运行 Agent"""
        result = self.app.invoke({
            "chat_history": chat_history,
            "messages": []
        })
        
        return {
            "success": result["final_result"] is not None,
            "store": result["final_result"],
            "attempts": result["attempt_count"],
            "history": result["search_history"]
        }

# ============ 使用示例 ============
if __name__ == "__main__":
    # 1. 先在上面配置好你的 curl
    # 2. 运行 Agent
    agent = FlexibleStoreAgent()
    
    chat_history = """
    用户：帮我找一下那个华强北的肯德基地址？
    用户：不对，好像是麦当劳？
    用户：唉，反正就是卖汉堡的，在华强北地铁站附近的
    """
    
    result = agent.run(chat_history)
    
    print("=" * 50)
    if result["success"]:
        print("✅ 找到匹配门店！")
        print(f"门店信息：{json.dumps(result['store'], ensure_ascii=False, indent=2)}")
    else:
        print("❌ 未找到匹配门店")
    print(f"\n搜索次数：{result['attempts']}")
    print("=" * 50)
```

## 核心特点

### 1. 零代码配置 curl
只需把前端的 curl 粘贴到 `CURL_TEMPLATE`，Agent 会自动解析并调用。

### 2. 完全自主的智能流程
- **关键词提取**：自动从聊天记录识别（包括错别字、昵称）
- **结果分析**：自己理解 API 返回的任意 JSON 结构
- **智能判断**：决定是否找到合适的门店
- **关键词优化**：自动修正、调整搜索词

### 3. 灵活适配任意 API 结构
不需要你定义 API 的响应 schema，LLM 会自动理解返回的 JSON 数据结构。

### 4. 完整的可观测性
记录每一次搜索的关键词和结果，方便调试。

## 快速开始

1. 把代码里的 `CURL_TEMPLATE` 换成你实际的 curl
2. 把 `{{keyword}}` 放在 curl 的参数位置（如果原来有具体值，替换掉）
3. 运行代码即可
