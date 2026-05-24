#!/usr/bin/env python3
"""
通用 CURL 导入引擎 - 统一配置版
支持提取任意字段并映射到自定义表头
支持任意层级的级联请求（通过 curl_commands 数量自动判断）
"""

import asyncio
import json
import csv
import yaml
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JSONPathError


# ==================== 全局配置中心 ====================
# 统一配置格式：
# - curl_commands: CURL 命令列表（1个为单请求，多个为级联）
# - request_params: 每个请求的参数映射（与 curl_commands 索引对应）
# - level_config: 层级配置，每个层级支持展平

GLOBAL_CONFIG = {
    # ========================================
    # 场景1: 事件类型 - 单 CURL 树形结构
    # ========================================
#     "event_type_single": {
#         "description": "事件类型单请求树形结构导入",
#         "output_file": "event_type_single_output.csv",
#         "yaml_file": "event_type_single_config.yaml",
#         "global_vars": {
#             "API_KEY": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
#             "BASE_URL": "http://localhost:9999",
#             "CLASS_NAME": "事件类型",
#             "TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJleHAiOjE3ODAxMDExMDAsImN1cnJlbnRfdGVuYW50X2lkIjozLCJ0ZW5hbnRfZG9tYWluIjoiIn0.vX0vLFzm93vpkI0_x2dqOYucajcAgoI67T1SJaOpVvU"
#         },
#         "data_root_path": "$.data",
        
#         # 请求参数配置 - 每个元素对应一个请求的参数映射
#         # 单请求时只有1个元素，级联时有多个元素
#         "request_params": [
#             {}  # 第1个请求不需要参数
#         ],
        
#         # 层级配置 - 每个层级定义展平规则
#         "level_config": {
#             "level1": {
#                 # 第1层数据：来自第1个请求 (curl_commands[0])
#                 "source": {"type": "request", "index": 0},
#                 "fields": [
#                     {"csv_header": "level1", "jsonpath": "$.option_value"},
#                     {"csv_header": "level1_summary", "jsonpath": "$.summary"},
#                     {"csv_header": "level1_id", "jsonpath": "$.id"},
#                     {"csv_header": "level1_code", "jsonpath": "$.code"}
#                 ],
#                 "children_jsonpath": "$.children",  # 子节点路径
#                 "params": {}  # 第1个请求无参数
#             },
#             "level2": {
#                 # 第2层数据：来自 level1 的 children_jsonpath 展平
#                 "source": {"type": "children", "from_level": "level1"},
#                 "fields": [
#                     {"csv_header": "level2", "jsonpath": "$.option_value"},
#                     {"csv_header": "level2_summary", "jsonpath": "$.summary"},
#                     {"csv_header": "level2_id", "jsonpath": "$.id"}
#                 ],
#                 "children_jsonpath": "$.children",
#                 "params": {}
#             },
#             "level3": {
#                 # 第3层数据：来自 level2 的 children_jsonpath 展平
#                 "source": {"type": "children", "from_level": "level2"},
#                 "fields": [
#                     {"csv_header": "level3", "jsonpath": "$.option_value"},
#                     {"csv_header": "level3_summary", "jsonpath": "$.summary"}
#                 ],
#                 "children_jsonpath": None,  # 最后一层无子节点
#                 "params": {}
#             }
#         },
        
#         # CURL 命令列表（1个为单请求，多个为级联）
#         "curl_commands": [
#             """curl 'http://localhost:3200/api/v1/autofill/dropdown/tree?app_name=test_app&class_name=%E4%BA%8B%E4%BB%B6%E7%B1%BB%E5%9E%8B' \
#    -H 'Accept: application/json, text/plain, */*' \
#    -H 'token: {TOKEN}'"""
#         ]
#     },

    # ========================================
    # 场景2: 事件类型 - 级联 CURL (2层)
    # ========================================
    "event_type_cascade": {
        "description": "事件类型级联请求导入(2层)",
        "output_file": "event_type_cascade_output.csv",
        "yaml_file": "event_type_cascade_config.yaml",
        "global_vars": {
            "API_KEY": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
            "BASE_URL": "http://localhost:9999",
            "CLASS_NAME": "事件类型"
        },
        "data_root_path": "$.data",
        
        # 层级配置 - 明确定义每个层级的数据结构和来源
        "level_config": {
            "level1": {
                # 第1层数据：来自第1个请求 (curl_commands[0])
                "source": {"type": "request", "index": 0},
                "fields": [
                    {"csv_header": "level1", "jsonpath": "$.option_value"},
                    {"csv_header": "level1_summary", "jsonpath": "$.summary"},
                    {"csv_header": "level1_id", "jsonpath": "$.id"}
                ],
                "children_jsonpath": "$.children",
                "params": {}  # 第1个请求无参数
            },
            "level2": {
                # 第2层数据：来自第2个请求 (curl_commands[1])
                "source": {"type": "request", "index": 1},
                "fields": [
                    {"csv_header": "level2", "jsonpath": "$.option_value"},
                    {"csv_header": "level2_summary", "jsonpath": "$.summary"}
                ],
                "children_jsonpath": "$.children",
                # 第2个请求的参数映射
                "params": {
                    "parent_value": "level1.level1"  # 使用 level1 的 level1 字段
                }
            },
            "level3": {
                # 第3层数据：来自 level2 的 children_jsonpath 展平
                "source": {"type": "children", "from_level": "level2"},
                "fields": [
                    {"csv_header": "level3", "jsonpath": "$.option_value"},
                    {"csv_header": "level3_summary", "jsonpath": "$.summary"}
                ],
                "children_jsonpath": None,
                "params": {}
            }
        },
        
        # 2个 CURL 命令
        "curl_commands": [
            """curl -X POST "http://localhost:9999/api/autofill/dropdown/first_level" \\
  -H "Authorization: Bearer {API_KEY}" \\
  -d '{"class_name": "事件类型"}'""",
            """curl -X POST "http://localhost:9999/api/autofill/dropdown/submenus_tree" \\
  -H "Authorization: Bearer {API_KEY}" \\
  -d '{"first_level_value": "{parent_value}", "class_name": "事件类型"}'"""
        ]
    },

    # ========================================
    # 场景3: 产品分类 - 级联 CURL (4层示例)
    # ========================================
#     "product_category_4level": {
#         "description": "产品分类4层级联请求导入示例",
#         "output_file": "product_category_4level_output.csv",
#         "yaml_file": "product_category_4level_config.yaml",
#         "global_vars": {
#             "API_KEY": "your_api_key",
#             "BASE_URL": "http://localhost:8080"
#         },
#         "data_root_path": "$.data",
        
#         # 4层级的请求参数配置
#         "request_params": [
#             {},  # 第1个请求: 获取一级分类，无参数
#             {"parent_id": "level1.cat1_id"},  # 第2个请求: 使用一级分类ID
#             {"parent_id": "level2.cat2_id"},  # 第3个请求: 使用二级分类ID
#             {"parent_id": "level3.cat3_id"}   # 第4个请求: 使用三级分类ID
#         ],
        
#         "level_config": {
#             "level1": {
#                 "fields": [
#                     {"csv_header": "cat1_id", "jsonpath": "$.id"},
#                     {"csv_header": "cat1_name", "jsonpath": "$.name"},
#                     {"csv_header": "cat1_code", "jsonpath": "$.code"}
#                 ],
#                 "children_jsonpath": "$.children"
#             },
#             "level2": {
#                 "fields": [
#                     {"csv_header": "cat2_id", "jsonpath": "$.id"},
#                     {"csv_header": "cat2_name", "jsonpath": "$.name"},
#                     {"csv_header": "cat2_code", "jsonpath": "$.code"}
#                 ],
#                 "children_jsonpath": "$.children"
#             },
#             "level3": {
#                 "fields": [
#                     {"csv_header": "cat3_id", "jsonpath": "$.id"},
#                     {"csv_header": "cat3_name", "jsonpath": "$.name"}
#                 ],
#                 "children_jsonpath": "$.children"
#             },
#             "level4": {
#                 "fields": [
#                     {"csv_header": "cat4_id", "jsonpath": "$.id"},
#                     {"csv_header": "cat4_name", "jsonpath": "$.name"}
#                 ],
#                 "children_jsonpath": None
#             }
#         },
        
#         # 4个 CURL 命令，对应4层
#         "curl_commands": [
#             """curl -X GET "http://localhost:8080/api/categories/level1" \\
#   -H "Authorization: Bearer {API_KEY}" """,
#             """curl -X GET "http://localhost:8080/api/categories/level2?parent_id={parent_id}" \\
#   -H "Authorization: Bearer {API_KEY}" """,
#             """curl -X GET "http://localhost:8080/api/categories/level3?parent_id={parent_id}" \\
#   -H "Authorization: Bearer {API_KEY}" """,
#             """curl -X GET "http://localhost:8080/api/categories/level4?parent_id={parent_id}" \\
#   -H "Authorization: Bearer {API_KEY}" """
#         ]
#     }
}

# ========================================
# 当前使用的场景配置 KEY
# ========================================
SCENARIO_KEY = "event_type_single"


class JsonPathExtractor:
    """使用 jsonpath-ng 库的 JSONPath 提取器"""
    
    @staticmethod
    def extract(data: Any, jsonpath: str) -> Any:
        """使用 jsonpath-ng 库从数据中提取 JSONPath 指定的值"""
        if not jsonpath or not isinstance(jsonpath, str):
            return None
        
        try:
            jsonpath_expr = jsonpath_parse(jsonpath)
            matches = jsonpath_expr.find(data)
            
            if not matches:
                return None
            
            if len(matches) == 1:
                return matches[0].value
            
            return [match.value for match in matches]
            
        except JSONPathError as e:
            print(f"  ⚠️ JSONPath 解析错误: {e}")
            return None
        except Exception as e:
            print(f"  ⚠️ 提取失败: {e}")
            return None


class CurlParser:
    """CURL 命令解析器"""
    
    @staticmethod
    def parse(curl_command: str) -> Dict[str, Any]:
        """解析 CURL 命令为结构化数据"""
        result = {
            "method": "GET",
            "url": "",
            "headers": {},
            "cookies": {},
            "data": None,
            "json": None
        }
        
        curl_command = curl_command.replace('\\\n', ' ').replace('\\', '')
        
        method_match = re.search(r'-X\s+(\w+)', curl_command)
        if method_match:
            result["method"] = method_match.group(1).upper()
        
        url_match = re.search(r'curl\s+(?:-X\s+\w+\s+)?["\']?([^"\'\s]+)["\']?', curl_command)
        if url_match:
            result["url"] = url_match.group(1)
        
        header_matches = re.findall(r'-H\s+["\']([^"\']+)["\']', curl_command)
        for header in header_matches:
            if ':' in header:
                key, value = header.split(':', 1)
                result["headers"][key.strip()] = value.strip()
        
        cookie_matches = re.findall(r'-b\s+["\']([^"\']+)["\']', curl_command)
        for cookie_str in cookie_matches:
            for cookie in cookie_str.split(';'):
                if '=' in cookie:
                    key, value = cookie.split('=', 1)
                    result["cookies"][key.strip()] = value.strip()
        
        data_match = re.search(r'-d\s+[\'"](\{.+\})[\'"]', curl_command)
        if data_match:
            try:
                json_str = data_match.group(1).replace('\\"', '"')
                result["json"] = json.loads(json_str)
            except json.JSONDecodeError as e:
                result["data"] = data_match.group(1)
        
        return result


class CurlImportEngine:
    """通用 CURL 导入引擎 - 统一配置版"""

    def __init__(self, scenario_key: str = None):
        """
        初始化引擎
        
        Args:
            scenario_key: 场景配置 key
        """
        self.scenario_key = scenario_key or SCENARIO_KEY
        self.config = GLOBAL_CONFIG.get(self.scenario_key)
        
        if not self.config:
            raise ValueError(f"未知的场景配置: {self.scenario_key}")
        
        self.global_vars = self.config["global_vars"]
        self.level_config = self.config["level_config"]
        self.data_root_path = self.config.get("data_root_path", "$.data")
        self.output_file = self.config.get("output_file", f"{self.scenario_key}_output.csv")
        self.yaml_file = self.config.get("yaml_file", f"{self.scenario_key}_config.yaml")
        self.extractor = JsonPathExtractor()
        
        # 构建 CSV 表头映射
        self.csv_headers = self._build_csv_headers()
        
        # 层级名称列表
        self.level_names = list(self.level_config.keys())
        
        # 自动判断模式（根据 curl_commands 数量）
        self.curl_commands = self.config.get("curl_commands", [])
        self.mode = "single" if len(self.curl_commands) == 1 else "cascade"
        
        # 构建请求到层级的映射
        self._build_request_level_mapping()

    def _build_csv_headers(self) -> Dict[str, str]:
        """构建 CSV 表头映射"""
        headers = {}
        for level_name, level_cfg in self.level_config.items():
            for field in level_cfg.get("fields", []):
                csv_header = field.get("csv_header", f"{level_name}_field")
                key = f"{level_name}_{csv_header}"
                headers[key] = csv_header
        return headers

    def _build_request_level_mapping(self):
        """构建请求索引到层级的映射"""
        self.request_level_map = {}   # request_idx -> level_name
        self.level_params = {}        # level_name -> params
        self.level_source = {}        # level_name -> source config

        for level_name, level_cfg in self.level_config.items():
            source = level_cfg.get("source", {})
            self.level_source[level_name] = source
            self.level_params[level_name] = level_cfg.get("params", {})

            # 如果数据源是 request，建立映射
            if source.get("type") == "request":
                request_idx = source.get("index")
                if request_idx is not None:
                    self.request_level_map[request_idx] = level_name

    def parse_curl_commands(self) -> List[Dict[str, Any]]:
        """解析 CURL 命令"""
        parsed = []
        for i, cmd in enumerate(self.curl_commands):
            print(f"\n解析 CURL 命令 {i+1}...")
            parsed_cmd = CurlParser.parse(cmd)
            parsed.append(parsed_cmd)
            
            print(f"  方法: {parsed_cmd['method']}")
            print(f"  URL: {parsed_cmd['url'][:80]}...")
            if parsed_cmd.get('json'):
                print(f"  JSON: {parsed_cmd['json']}")
        
        return parsed

    def generate_yaml_config(self, parsed_requests: List[Dict[str, Any]]) -> str:
        """生成 YAML 配置"""
        requests_config = []
        
        for i, req in enumerate(parsed_requests):
            # 获取该请求对应的层级名称
            level_name = self.request_level_map.get(i)
            # 获取该层级的参数
            params = self.level_params.get(level_name, {}) if level_name else {}
            
            req_config = {
                "name": f"请求{i+1}",
                "method": req['method'],
                "url": req['url'],
                "headers": req['headers'],
                "cookies": req.get('cookies', {}),
                "params": params,
                "level": level_name,
                "level_config": self.level_config
            }
            
            if req.get('json'):
                req_config['json'] = req['json']
            
            requests_config.append(req_config)
        
        config = {
            "scenario": self.scenario_key,
            "description": self.config["description"],
            "mode": self.mode,
            "output": {
                "path": self.output_file,
                "encoding": "utf-8-sig",
                "deduplicate": True
            },
            "request": {
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1
            },
            "data": {
                "root_path": self.data_root_path
            },
            "csv_headers": self.csv_headers,
            "level_config": self.level_config,
            "requests": requests_config
        }
        
        return yaml.dump(config, allow_unicode=True, default_flow_style=False, indent=2, sort_keys=False)

    def replace_variables(self, obj: Any, context: Dict[str, Any]) -> Any:
        """递归替换变量占位符"""
        if isinstance(obj, str):
            result = obj
            for key, value in context.items():
                placeholder = f"{{{key}}}"
                if placeholder in result:
                    result = result.replace(placeholder, str(value))
            return result
        elif isinstance(obj, dict):
            # 递归处理字典的每个值
            result = {}
            for key, value in obj.items():
                result[key] = self.replace_variables(value, context)
            return result
        elif isinstance(obj, list):
            # 递归处理列表的每个元素
            return [self.replace_variables(item, context) for item in obj]
        return obj

    def extract_level_data(self, item: Dict, level_name: str) -> Dict[str, Any]:
        """使用 JSONPath 从数据项中提取该层级的所有字段"""
        level_cfg = self.level_config.get(level_name, {})
        fields = level_cfg.get("fields", [])
        
        result = {}
        for field in fields:
            csv_header = field.get("csv_header", "field")
            jsonpath = field.get("jsonpath", "$")
            value = self.extractor.extract(item, jsonpath)
            result[csv_header] = value if value is not None else ""
        
        return result

    def get_children(self, item: Dict, level_name: str) -> List[Dict]:
        """使用 JSONPath 获取子节点列表"""
        level_cfg = self.level_config.get(level_name, {})
        children_jsonpath = level_cfg.get("children_jsonpath")
        
        if children_jsonpath:
            children = self.extractor.extract(item, children_jsonpath)
            if isinstance(children, list):
                return children
        return []

    def flatten_data_recursive(self, 
                               items: List[Dict], 
                               level_names: List[str],
                               parent_data: Dict = None,
                               ancestors_data: List[Tuple[str, Dict]] = None) -> List[Dict]:
        """递归展平任意层级的数据"""
        results = []
        parent_data = parent_data or {}
        ancestors_data = ancestors_data or []
        
        if not level_names or not items:
            return results
        
        current_level = level_names[0]
        remaining_levels = level_names[1:]
        
        for item in items:
            # 提取当前层级的所有字段
            level_data = self.extract_level_data(item, current_level)
            
            # 构建当前行数据（包含所有祖先数据）
            row = parent_data.copy()
            for csv_header, value in level_data.items():
                row[f"{current_level}_{csv_header}"] = value
            
            # 获取子节点
            children = self.get_children(item, current_level)
            
            if children and remaining_levels:
                # 递归处理子节点，传递当前层级数据作为祖先
                new_ancestors = ancestors_data + [(current_level, level_data)]
                child_results = self.flatten_data_recursive(
                    children, 
                    remaining_levels, 
                    row,
                    new_ancestors
                )
                results.extend(child_results)
            else:
                # 没有子节点，直接添加当前行
                results.append(row)
        
        return results

    async def execute_request(self, request_config: Dict[str, Any], context: Dict[str, Any] = None) -> Tuple[List[Dict], Dict]:
        """执行 HTTP 请求"""
        import aiohttp
        
        context = context or {}
        
        url = self.replace_variables(request_config['url'], {**self.global_vars, **context})
        headers = self.replace_variables(request_config.get('headers', {}), {**self.global_vars, **context})
        cookies = self.replace_variables(request_config.get('cookies', {}), {**self.global_vars, **context})
        json_data = self.replace_variables(request_config.get('json'), {**self.global_vars, **context})
        
        print(f"\n执行请求: {request_config.get('name', 'Unknown')}")
        print(f"  URL: {url[:80]}...")
        
        async with aiohttp.ClientSession() as session:
            method = getattr(session, request_config['method'].lower())
            kwargs = {'headers': headers}
            
            if cookies:
                kwargs['cookies'] = cookies
            if json_data:
                kwargs['json'] = json_data
            
            async with method(url, **kwargs) as resp:
                response_data = await resp.json()
                
                if response_data.get('code') != 200 and 'data' not in response_data:
                    raise Exception(f"API 错误: {response_data.get('msg', 'Unknown error')}")
                
                actual_data = response_data.get('data', [])
                print(f"  ✅ 成功，获取 {len(actual_data) if isinstance(actual_data, list) else 1} 条数据")
                
                return actual_data, response_data

    async def execute_single_request_mode(self, parsed_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """单请求模式：展平树形数据"""
        print("\n" + "=" * 60)
        print("【单请求模式】展平树形数据")
        print("=" * 60)
        
        tree_data, response = await self.execute_request({
            'name': '获取树形数据',
            'method': parsed_request['method'],
            'url': parsed_request['url'],
            'headers': parsed_request.get('headers', {}),
            'cookies': parsed_request.get('cookies', {}),
            'json': parsed_request.get('json')
        })
        
        if not tree_data or not isinstance(tree_data, list):
            print("❌ 没有返回数据")
            return []
        
        print(f"\n获取到 {len(tree_data)} 个顶层节点")
        print(f"配置层级: {self.level_names}")
        
        flattened = self.flatten_data_recursive(tree_data, self.level_names)
        
        return flattened

    async def execute_cascade_recursive(self,
                                       parsed_requests: List[Dict[str, Any]],
                                       request_idx: int,
                                       ancestors_data: List[Tuple[str, Dict]],
                                       parent_items: List[Dict]) -> List[Dict]:
        """递归执行级联请求"""
        all_results = []

        if request_idx >= len(parsed_requests):
            return all_results

        current_req = parsed_requests[request_idx]

        # 通过 request_level_map 获取当前请求对应的层级
        current_level_name = self.request_level_map.get(request_idx)

        print(f"\n{'='*60}")
        print(f"【级联请求 {request_idx + 1}/{len(parsed_requests)}】")
        if current_level_name:
            print(f"  对应层级: {current_level_name}")
        print(f"{'='*60}")

        # 获取当前层级的参数映射
        param_mapping = self.level_params.get(current_level_name, {}) if current_level_name else {}
        
        for parent_item in parent_items:
            # 提取当前层级的数据
            if current_level_name:
                current_level_data = self.extract_level_data(parent_item, current_level_name)
            else:
                current_level_data = {}
            
            # 构建参数上下文
            context = {}
            
            # 1. 添加祖先层级的数据（带层级前缀）
            for level_name, level_data in ancestors_data:
                for csv_header, value in level_data.items():
                    context[f"{level_name}_{csv_header}"] = value
            
            # 2. 添加当前层级的数据（不带前缀，用于级联参数）
            for csv_header, value in current_level_data.items():
                context[csv_header] = value
            
            # 3. 根据 request_params 映射参数
            param_context = {}
            for param_name, field_path in param_mapping.items():
                # 解析字段路径 (格式: "level1.level1" 或 "level1.level1_id")
                if "." in field_path:
                    level_name, field_name = field_path.split(".", 1)
                    # 从祖先数据中查找
                    for ancestor_level, ancestor_data in ancestors_data:
                        if ancestor_level == level_name:
                            param_value = ancestor_data.get(field_name, "")
                            param_context[param_name] = param_value
                            break
                else:
                    # 直接从当前层级获取
                    param_value = current_level_data.get(field_path, "")
                    param_context[param_name] = param_value
            
            # 合并参数上下文
            context.update(param_context)
            
            # 显示处理的参数
            if param_context:
                param_display = ", ".join([f"{k}={v}" for k, v in param_context.items()])
                print(f"\n🔄 处理 {current_level_name}: {param_display}")
            
            try:
                # 执行当前请求
                response_data, _ = await self.execute_request({
                    'name': f'获取{current_level_name or "数据"}',
                    'method': current_req['method'],
                    'url': current_req['url'],
                    'headers': current_req.get('headers', {}),
                    'cookies': current_req.get('cookies', {}),
                    'json': current_req.get('json')
                }, context)
                
                # 获取子节点
                if isinstance(response_data, dict):
                    children = response_data.get('children', [])
                    if not children:
                        children = response_data.get('data', [])
                else:
                    children = response_data if isinstance(response_data, list) else []
                
                print(f"  获取到 {len(children)} 个子节点")
                
                # 构建当前层级的完整数据上下文
                current_row = {}
                for level_name, level_data in ancestors_data:
                    for csv_header, value in level_data.items():
                        current_row[f"{level_name}_{csv_header}"] = value
                for csv_header, value in current_level_data.items():
                    current_row[f"{current_level_name}_{csv_header}"] = value
                
                # 如果有更多请求，递归处理
                if request_idx + 1 < len(parsed_requests) and children:
                    new_ancestors = ancestors_data + [(current_level_name, current_level_data)]
                    child_results = await self.execute_cascade_recursive(
                        parsed_requests,
                        request_idx + 1,
                        new_ancestors,
                        children
                    )
                    all_results.extend(child_results)
                elif children:
                    # 最后一个请求，展平数据
                    remaining_levels = self.level_names[request_idx + 1:]
                    if remaining_levels:
                        child_results = self.flatten_data_recursive(
                            children,
                            remaining_levels,
                            current_row,
                            ancestors_data + [(current_level_name, current_level_data)]
                        )
                        all_results.extend(child_results)
                    else:
                        # 直接添加子节点数据
                        for child in children:
                            child_data = self.extract_level_data(child, self.level_names[-1])
                            row = current_row.copy()
                            for csv_header, value in child_data.items():
                                row[f"{self.level_names[-1]}_{csv_header}"] = value
                            all_results.append(row)
                else:
                    # 没有子节点，添加当前行
                    all_results.append(current_row)
                    
            except Exception as e:
                print(f"  ❌ 请求失败: {e}")
                continue
        
        return all_results

    async def execute_cascade_mode(self, parsed_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """级联模式：执行多级联请求"""
        print("\n" + "=" * 60)
        print("【级联模式】执行级联请求")
        print(f"  总请求数: {len(parsed_requests)}")
        print(f"  总层级数: {len(self.level_names)}")
        print("=" * 60)
        
        # 执行第一个请求获取初始数据
        first_req = parsed_requests[0]
        first_data, _ = await self.execute_request({
            'name': '获取初始数据',
            'method': first_req['method'],
            'url': first_req['url'],
            'headers': first_req.get('headers', {}),
            'cookies': first_req.get('cookies', {}),
            'json': first_req.get('json')
        })
        
        if not first_data or not isinstance(first_data, list):
            print("❌ 第一个请求没有返回数据")
            return []
        
        print(f"\n获取到 {len(first_data)} 个初始节点")
        
        # 如果只有一个请求，直接展平
        if len(parsed_requests) == 1:
            return self.flatten_data_recursive(first_data, self.level_names)
        
        # 递归执行级联请求
        first_level_name = self.level_names[0]
        
        results = await self.execute_cascade_recursive(
            parsed_requests,
            1,  # 从第二个请求开始
            [(first_level_name, self.extract_level_data(item, first_level_name)) for item in first_data],
            first_data
        )
        
        return results

    def write_to_csv(self, data: List[Dict[str, Any]], filename: str = "output.csv"):
        """写入 CSV，支持自定义表头映射"""
        if not data:
            print("⚠️ 没有数据可写入")
            return
        
        # 获取所有字段名（直接使用 csv_header）
        fieldnames = []
        for level_name, level_cfg in self.level_config.items():
            for field in level_cfg.get("fields", []):
                csv_header = field.get("csv_header", "field")
                fieldnames.append(f"{level_name}_{csv_header}")
        
        # 应用表头映射
        mapped_fieldnames = []
        header_mapping = {}
        
        for raw_name in fieldnames:
            if raw_name in self.csv_headers:
                mapped_name = self.csv_headers[raw_name]
                mapped_fieldnames.append(mapped_name)
                header_mapping[raw_name] = mapped_name
            else:
                mapped_fieldnames.append(raw_name)
                header_mapping[raw_name] = raw_name
        
        # 转换数据
        mapped_data = []
        for row in data:
            mapped_row = {}
            for raw_name, mapped_name in header_mapping.items():
                mapped_row[mapped_name] = row.get(raw_name, "")
            mapped_data.append(mapped_row)
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=mapped_fieldnames)
            writer.writeheader()
            writer.writerows(mapped_data)
        
        print(f"\n✅ 数据已写入: {filename} ({len(data)} 行)")
        print(f"   CSV 表头: {', '.join(mapped_fieldnames)}")

    def calculate_md5(self, data: List[Dict[str, Any]]) -> str:
        """计算 MD5"""
        import hashlib
        
        fieldnames = []
        for level_name, level_cfg in self.level_config.items():
            for field in level_cfg.get("fields", []):
                csv_header = field.get("csv_header", "field")
                fieldnames.append(f"{level_name}_{csv_header}")
        
        content_json = {
            "headers": fieldnames,
            "data": [[row.get(k, "") for k in fieldnames] for row in data]
        }
        
        return hashlib.md5(
            json.dumps(content_json, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

    async def run(self):
        """运行完整流程"""
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 12 + "通用 CURL 导入引擎" + " " * 12 + "║")
        print("╚" + "=" * 58 + "╝")
        
        print(f"\n📋 当前场景: {self.scenario_key}")
        print(f"   描述: {self.config['description']}")
        print(f"   模式: {self.mode} ({len(self.curl_commands)} 个请求)")
        print(f"   层级数: {len(self.level_names)}")
        
        start_time = datetime.now()
        
        if not self.curl_commands:
            print("❌ 没有配置 CURL 命令")
            return None
        
        # 1. 解析
        print("\n" + "=" * 60)
        print("【步骤1】解析 CURL 命令")
        print("=" * 60)
        parsed_requests = self.parse_curl_commands()
        
        # 2. 生成 YAML
        print("\n" + "=" * 60)
        print("【步骤2】生成 YAML 配置")
        print("=" * 60)
        yaml_config = self.generate_yaml_config(parsed_requests)
        print(yaml_config)
        
        with open(self.yaml_file, "w", encoding="utf-8") as f:
            f.write(yaml_config)
        print(f"✅ YAML 配置已保存: {self.yaml_file}")
        
        # 3. 执行（根据模式自动选择）
        if self.mode == "single":
            all_data = await self.execute_single_request_mode(parsed_requests[0])
        else:
            all_data = await self.execute_cascade_mode(parsed_requests)
        
        if not all_data:
            print("\n❌ 没有获取到数据")
            return None
        
        # 4. 写入 CSV
        self.write_to_csv(all_data, self.output_file)
        
        # 5. 计算 MD5
        md5_hash = self.calculate_md5(all_data)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 6. 摘要
        print("\n" + "=" * 60)
        print("执行摘要")
        print("=" * 60)
        print(f"场景: {self.scenario_key}")
        print(f"模式: {self.mode}")
        print(f"数据 MD5: {md5_hash}")
        print(f"总行数: {len(all_data)}")
        print(f"执行时间: {duration:.2f} 秒")
        
        return {
            "yaml_config": yaml_config,
            "csv_data": all_data,
            "md5": md5_hash,
            "row_count": len(all_data)
        }


async def main():
    """主函数"""
    import sys
    
    scenario_key = sys.argv[1] if len(sys.argv) > 1 else SCENARIO_KEY
    
    try:
        engine = CurlImportEngine(scenario_key)
        result = await engine.run()
        
        if result:
            print("\n✅ 导入测试成功完成！")
    except ValueError as e:
        print(f"❌ 错误: {e}")
        print(f"\n可用的场景配置:")
        for key, config in GLOBAL_CONFIG.items():
            curl_count = len(config.get('curl_commands', []))
            mode = "单请求" if curl_count == 1 else f"级联({curl_count}层)"
            print(f"  - {key}: {config['description']} ({mode})")


if __name__ == "__main__":
    asyncio.run(main())
