"""
CURL导入服务 - 处理从CURL配置获取数据并生成CSV
"""
import asyncio
import csv
import io
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import aiohttp
from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JSONPathError

from app.log import logger


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
            logger.warning(f"JSONPath 解析错误: {e}")
            return None
        except Exception as e:
            logger.warning(f"提取失败: {e}")
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

        # 改进的 -d 参数解析，支持单引号和双引号包裹的JSON数据
        # 尝试匹配 -d 后面跟随的JSON数据
        data_match = re.search(r'-d\s+([\'"])(\{.*?\})\1', curl_command, re.DOTALL)
        if data_match:
            try:
                json_str = data_match.group(2).replace('\\"', '"')
                result["json"] = json.loads(json_str)
            except json.JSONDecodeError as e:
                result["data"] = data_match.group(2)
        else:
            # 回退：尝试更宽松的匹配
            data_match = re.search(r'-d\s+[\'"]([^\'"]+)[\'"]', curl_command)
            if data_match:
                try:
                    json_str = data_match.group(1).replace('\\"', '"')
                    result["json"] = json.loads(json_str)
                except json.JSONDecodeError:
                    result["data"] = data_match.group(1)

        return result


class CurlImportService:
    """CURL导入服务"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化服务

        Args:
            config: CURL导入配置
        """
        self.config = config
        self.global_vars = config.get("global_vars", {})
        self.level_config = config.get("level_config", {})
        self.data_root_path = config.get("data_root_path", "$.data")
        self.curl_commands = config.get("curl_commands", [])
        self.extractor = JsonPathExtractor()

        # 层级名称列表
        self.level_names = list(self.level_config.keys())

        # 自动判断模式
        self.mode = "single" if len(self.curl_commands) == 1 else "cascade"

        # 构建请求到层级的映射
        self._build_request_level_mapping()

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
            parsed_cmd = CurlParser.parse(cmd)
            parsed.append(parsed_cmd)
        return parsed

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
            # 直接使用 csv_header 作为键，与 convert_to_csv 保持一致
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
            # 提取当前层级的所有字段（extract_level_data 已返回带前缀的键）
            level_data = self.extract_level_data(item, current_level)

            # 构建当前行数据（包含所有祖先数据）
            row = parent_data.copy()
            # level_data 的键已经是 {level_name}_{csv_header} 格式
            row.update(level_data)

            # 获取子节点
            children = self.get_children(item, current_level)

            if children and remaining_levels:
                # 递归处理子节点
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
        context = context or {}

        url = self.replace_variables(request_config['url'], {**self.global_vars, **context})
        headers = self.replace_variables(request_config.get('headers', {}), {**self.global_vars, **context})
        cookies = self.replace_variables(request_config.get('cookies', {}), {**self.global_vars, **context})
        json_data = self.replace_variables(request_config.get('json'), {**self.global_vars, **context})

        logger.info(f"执行请求: {request_config.get('name', 'Unknown')}, URL: {url[:80]}...")

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
                logger.info(f"请求成功，获取 {len(actual_data) if isinstance(actual_data, list) else 1} 条数据")

                return actual_data, response_data

    async def execute_single_request_mode(self, parsed_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """单请求模式：展平树形数据"""
        tree_data, response = await self.execute_request({
            'name': '获取树形数据',
            'method': parsed_request['method'],
            'url': parsed_request['url'],
            'headers': parsed_request.get('headers', {}),
            'cookies': parsed_request.get('cookies', {}),
            'json': parsed_request.get('json')
        })

        if not tree_data or not isinstance(tree_data, list):
            logger.warning("没有返回数据")
            return []

        logger.info(f"获取到 {len(tree_data)} 个顶层节点，配置层级: {self.level_names}")

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
        current_level_name = self.request_level_map.get(request_idx)
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
                if "." in field_path:
                    level_name, field_name = field_path.split(".", 1)
                    for ancestor_level, ancestor_data in ancestors_data:
                        if ancestor_level == level_name:
                            param_value = ancestor_data.get(field_name, "")
                            param_context[param_name] = param_value
                            break
                else:
                    param_value = current_level_data.get(field_path, "")
                    param_context[param_name] = param_value

            context.update(param_context)

            try:
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

                # 构建当前层级的完整数据上下文
                current_row = {}
                # ancestors_data 中的 level_data 键已经是 csv_header 格式（如 level1）
                # 不需要再添加 level_name 前缀
                for level_name, level_data in ancestors_data:
                    for csv_header, value in level_data.items():
                        current_row[csv_header] = value
                # current_level_data 的键也是 csv_header 格式
                for csv_header, value in current_level_data.items():
                    current_row[csv_header] = value

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
                            # 直接使用 csv_header 作为键，与 convert_to_csv 保持一致
                            for csv_header, value in child_data.items():
                                row[csv_header] = value
                            all_results.append(row)
                else:
                    # 没有子节点，添加当前行
                    all_results.append(current_row)

            except Exception as e:
                logger.error(f"请求失败: {e}")
                continue

        return all_results

    async def execute_cascade_mode(self, parsed_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """级联模式：执行多级联请求"""
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
            logger.warning("第一个请求没有返回数据")
            return []

        logger.info(f"获取到 {len(first_data)} 个初始节点")

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

    def convert_to_csv(self, data: List[Dict[str, Any]]) -> Tuple[List[str], List[List[str]]]:
        """
        将数据转换为CSV格式

        Returns:
            (headers, rows) - 表头和数据行
        """
        if not data:
            return [], []

        # 获取所有字段名（直接使用 csv_header，不再添加 level_name 前缀）
        fieldnames = []
        for level_name, level_cfg in self.level_config.items():
            for field in level_cfg.get("fields", []):
                csv_header = field.get("csv_header", "field")
                fieldnames.append(csv_header)

        # 构建CSV行
        rows = []
        for row_data in data:
            row = []
            for field in fieldnames:
                row.append(str(row_data.get(field, "")))
            rows.append(row)

        return fieldnames, rows

    async def fetch_data(self) -> Dict[str, Any]:
        """
        执行CURL请求并获取数据

        Returns:
            {
                "headers": [...],
                "data": [...],
                "row_count": int,
                "mode": "single" | "cascade"
            }
        """
        if not self.curl_commands:
            raise ValueError("没有配置 CURL 命令")

        # 解析CURL命令
        parsed_requests = self.parse_curl_commands()

        # 根据模式执行
        if self.mode == "single":
            all_data = await self.execute_single_request_mode(parsed_requests[0])
        else:
            all_data = await self.execute_cascade_mode(parsed_requests)

        if not all_data:
            return {
                "headers": [],
                "data": [],
                "row_count": 0,
                "mode": self.mode
            }

        # 转换为CSV格式
        headers, rows = self.convert_to_csv(all_data)

        return {
            "headers": headers,
            "data": rows,
            "row_count": len(rows),
            "mode": self.mode
        }

    async def fetch_data_as_csv_string(self) -> str:
        """获取数据并转换为CSV字符串"""
        result = await self.fetch_data()

        if not result["headers"]:
            return ""

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(result["headers"])
        writer.writerows(result["data"])

        return output.getvalue()


# 服务实例
curl_import_service = CurlImportService
