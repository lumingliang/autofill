"""
统一 CURL 导入引擎 - 完全复用脚本核心逻辑

配置格式（与脚本完全一致）:
{
    "description": "配置描述",
    "global_vars": {"BASE_URL": "..."},
    "data_root": "$.data",
    "levels": [
        {
            "name": "level1",
            "source": "request",  # request 或 children
            "request_index": 0,
            "fields": [
                {"header": "name_level1", "jsonpath": "$.option_value"}
            ],
            "children_path": "$.children",
            "params": {}  # 级联请求时的参数映射
        }
    ],
    "curl_commands": ["curl ..."]
}
"""
import csv
import io
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

import aiohttp
from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JSONPathError

from app.log import logger


class JsonPathExtractor:
    """JSONPath 提取器"""

    @staticmethod
    def extract(data: Any, path: str) -> Any:
        if not path:
            return None
        try:
            matches = jsonpath_parse(path).find(data)
            if not matches:
                return None
            return matches[0].value if len(matches) == 1 else [m.value for m in matches]
        except (JSONPathError, Exception) as e:
            logger.warning(f"JSONPath错误: {e}")
            return None


class CurlParser:
    """CURL 命令解析器"""

    @staticmethod
    def parse(cmd: str) -> Dict[str, Any]:
        result = {"method": "GET", "url": "", "headers": {}, "json": None}
        cmd = cmd.replace('\\\n', ' ').replace('\\', '')

        # 方法
        if m := re.search(r'-X\s+(\w+)', cmd):
            result["method"] = m.group(1).upper()

        # URL
        if m := re.search(r'curl\s+(?:-X\s+\w+\s+)?["\']?([^"\'\s]+)["\']?', cmd):
            result["url"] = m.group(1)

        # Headers
        for h in re.findall(r'-H\s+["\']([^"\']+)["\']', cmd):
            if ':' in h:
                k, v = h.split(':', 1)
                result["headers"][k.strip()] = v.strip()

        # JSON data
        if m := re.search(r'-d\s+[\'"](\{.+\})[\'"]', cmd):
            try:
                result["json"] = json.loads(m.group(1).replace('\\"', '"'))
            except json.JSONDecodeError:
                pass

        return result


class CurlImportEngine:
    """
    统一 CURL 导入引擎

    配置格式（与脚本完全一致）:
    {
        "description": "配置描述",
        "global_vars": {"BASE_URL": "..."},
        "data_root": "$.data",
        "levels": [
            {
                "name": "level1",
                "source": "request",
                "request_index": 0,
                "fields": [{"header": "name", "jsonpath": "$.name"}],
                "children_path": "$.children",
                "params": {}
            }
        ],
        "curl_commands": ["curl ..."]
    }
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.global_vars = config.get("global_vars", {})
        self.data_root = config.get("data_root", "$.data")
        self.curl_commands = config.get("curl_commands", [])
        self.levels = config.get("levels", [])
        self.extractor = JsonPathExtractor()

        # 构建请求索引到层级的映射
        self.request_level_map = {}
        for i, lvl in enumerate(self.levels):
            if lvl.get("source") == "request" and "request_index" in lvl:
                self.request_level_map[lvl["request_index"]] = i

    def replace_vars(self, obj: Any, context: Dict[str, Any]) -> Any:
        """递归替换变量"""
        if isinstance(obj, str):
            result = obj
            for k, v in {**self.global_vars, **context}.items():
                result = result.replace(f"{{{k}}}", str(v))
            return result
        elif isinstance(obj, dict):
            return {k: self.replace_vars(v, context) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.replace_vars(i, context) for i in obj]
        return obj

    def extract_fields(self, item: Dict, level: Dict) -> Dict[str, Any]:
        """从数据项提取字段"""
        result = {}
        for field in level.get("fields", []):
            value = self.extractor.extract(item, field.get("jsonpath", "$"))
            result[field["header"]] = value if value is not None else ""
        return result

    def get_children(self, item: Dict, level: Dict) -> List[Dict]:
        """获取子节点"""
        path = level.get("children_path")
        if path:
            children = self.extractor.extract(item, path)
            return children if isinstance(children, list) else []
        return []

    async def execute_request(self, cmd: Dict[str, Any], context: Dict = None, data_root: str = None) -> List[Dict]:
        """执行 HTTP 请求"""
        context = context or {}
        url = self.replace_vars(cmd["url"], context)
        headers = self.replace_vars(cmd.get("headers", {}), context)
        json_data = self.replace_vars(cmd.get("json"), context)

        logger.info(f"执行请求: {cmd.get('method', 'GET')} {url[:60]}...")

        async with aiohttp.ClientSession() as session:
            method = getattr(session, cmd["method"].lower())
            kwargs = {"headers": headers}
            if json_data:
                kwargs["json"] = json_data

            async with method(url, **kwargs) as resp:
                data = await resp.json()
                # 使用传入的 data_root 或全局的 data_root
                root_path = data_root or self.data_root
                result = self.extractor.extract(data, root_path)
                result = result if isinstance(result, list) else []
                logger.info(f"请求成功，返回 {len(result)} 条数据")
                return result

    async def process_level(self,
                           level_idx: int,
                           items: List[Dict],
                           parent_data: Dict[str, Any],
                           parsed_cmds: List[Dict]) -> List[Dict[str, Any]]:
        """递归处理层级 - 核心逻辑"""
        results = []

        if level_idx >= len(self.levels) or not items:
            return results

        level = self.levels[level_idx]
        level_name = level["name"]

        for item in items:
            # 提取当前层级字段
            level_data = self.extract_fields(item, level)

            # 构建当前行
            row = parent_data.copy()
            for header, value in level_data.items():
                row[header] = value

            # 获取子节点
            children = self.get_children(item, level)

            # 判断下一级来源
            next_level = self.levels[level_idx + 1] if level_idx + 1 < len(self.levels) else None

            if not next_level:
                # 最后一层
                results.append(row)
            elif next_level.get("source") == "children" and children:
                # 下一级从 children 展平
                child_results = await self.process_level(
                    level_idx + 1, children, row, parsed_cmds
                )
                results.extend(child_results)
            elif next_level.get("source") == "request":
                # 下一级从请求获取（级联）
                req_idx = next_level.get("request_index")
                if req_idx is not None and req_idx < len(parsed_cmds):
                    # 构建参数上下文
                    ctx = {}
                    params = next_level.get("params", {})
                    for param_name, field_ref in params.items():
                        # field_ref 格式: "header_name" - 直接使用配置中定义的 header 名称
                        ctx[param_name] = row.get(field_ref, "")

                    # 执行请求获取下一级数据（使用层级特定的 data_root）
                    try:
                        level_data_root = next_level.get("data_root")
                        next_items = await self.execute_request(parsed_cmds[req_idx], ctx, level_data_root)
                        if next_items:
                            child_results = await self.process_level(
                                level_idx + 1, next_items, row, parsed_cmds
                            )
                            results.extend(child_results)
                        else:
                            results.append(row)
                    except Exception as e:
                        logger.error(f"请求失败: {e}")
                        results.append(row)
            else:
                # 无子节点，添加当前行
                results.append(row)

        return results

    async def run(self) -> List[Dict[str, Any]]:
        """运行导入流程"""
        logger.info("=" * 60)
        logger.info(f"【{self.config.get('description', 'CURL导入')}】")
        logger.info(f"层级数: {len(self.levels)}, 请求数: {len(self.curl_commands)}")
        logger.info("=" * 60)

        start_time = datetime.now()

        # 解析 CURL 命令
        logger.info("[1/3] 解析 CURL 命令...")
        parsed_cmds = [CurlParser.parse(cmd) for cmd in self.curl_commands]
        for i, cmd in enumerate(parsed_cmds):
            logger.info(f"  [{i}] {cmd['method']} {cmd['url'][:50]}...")

        # 找到第一个 request 来源的层级
        first_request_level = None
        for i, lvl in enumerate(self.levels):
            if lvl.get("source") == "request":
                first_request_level = i
                break

        if first_request_level is None:
            raise ValueError("配置错误：没有找到 request 来源的层级")

        # 执行第一个请求
        logger.info(f"[2/3] 执行初始请求 (层级: {self.levels[first_request_level]['name']})...")
        req_idx = self.levels[first_request_level].get("request_index", 0)
        initial_data = await self.execute_request(parsed_cmds[req_idx])

        if not initial_data:
            raise ValueError("初始请求无数据")

        # 递归处理所有层级
        logger.info("[3/3] 处理层级数据...")
        all_data = await self.process_level(
            first_request_level, initial_data, {}, parsed_cmds
        )

        # 统计
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"完成！共 {len(all_data)} 行，耗时 {duration:.2f}s")

        return all_data

    def _get_headers(self) -> List[str]:
        """获取表头列表（从配置中提取）"""
        headers = []
        for lvl in self.levels:
            for field in lvl.get("fields", []):
                headers.append(field['header'])
        return headers

    def convert_to_csv(self, data: List[Dict[str, Any]]) -> str:
        """转换为 CSV 字符串"""
        if not data:
            return ""

        headers = self._get_headers()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)

        for row in data:
            writer.writerow([str(row.get(h, "")) for h in headers])

        return output.getvalue()

    async def fetch_data_as_csv(self) -> Dict[str, Any]:
        """
        获取数据并转换为 CSV 格式

        Returns:
            {
                "csv_content": "CSV字符串",
                "row_count": 行数,
                "headers": [表头列表]
            }
        """
        # 执行导入流程
        all_data = await self.run()

        # 转换为 CSV
        csv_content = self.convert_to_csv(all_data)
        headers = self._get_headers()

        return {
            "csv_content": csv_content,
            "row_count": len(all_data),
            "headers": headers
        }

    async def fetch_data_as_rows(self) -> Dict[str, Any]:
        """
        获取数据并返回结构化数据（避免 CSV 编解码开销）

        Returns:
            {
                "headers": [表头列表],
                "rows": [Dict[str, Any], ...],  # 每行是一个字典
                "row_count": 行数
            }
        """
        # 执行导入流程
        all_data = await self.run()
        headers = self._get_headers()

        return {
            "headers": headers,
            "rows": all_data,
            "row_count": len(all_data)
        }
