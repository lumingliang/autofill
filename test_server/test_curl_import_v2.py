#!/usr/bin/env python3
"""
统一 CURL 导入引擎 - V2 改进版
修复了V1中发现的问题
"""

import asyncio
import json
import csv
import re
import logging
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JSONPathError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 测试配置 ====================

CONFIG_SINGLE = {
    "description": "单请求树形结构展平 - 测试接口",
    "output_file": "test_server/single_output_v2.csv",
    "global_vars": {
        "BASE_URL": "http://localhost:6666"
    },
    "data_root": "$.data",
    "request_timeout": 30,
    "max_retries": 3,
    "retry_delay": 1.0,

    "levels": [
        {
            "name": "level1",
            "source": "request",
            "request_index": 0,
            "fields": [
                {"header": "name", "jsonpath": "$.option_value"},
                {"header": "summary", "jsonpath": "$.summary"},
                {"header": "id", "jsonpath": "$.id"},
                {"header": "code", "jsonpath": "$.code"}
            ],
            "children_path": "$.children"
        },
        {
            "name": "level2",
            "source": "children",
            "fields": [
                {"header": "name", "jsonpath": "$.option_value"},
                {"header": "summary", "jsonpath": "$.summary"},
                {"header": "id", "jsonpath": "$.id"}
            ],
            "children_path": "$.children"
        },
        {
            "name": "level3",
            "source": "children",
            "fields": [
                {"header": "name", "jsonpath": "$.option_value"},
                {"header": "summary", "jsonpath": "$.summary"}
            ],
            "children_path": None
        }
    ],

    "curl_commands": [
        """curl -X POST "{BASE_URL}/api/test/tree" \\
  -H "Content-Type: application/json" \\
  -d '{"class_name": "事件类型"}'"""
    ]
}


CONFIG_CASCADE = {
    "description": "级联请求展平 - 测试接口",
    "output_file": "test_server/cascade_output_v2.csv",
    "global_vars": {
        "BASE_URL": "http://localhost:6666"
    },
    "data_root": "$.data",
    "request_timeout": 30,
    "max_retries": 3,
    "retry_delay": 1.0,

    "levels": [
        {
            "name": "level1",
            "source": "request",
            "request_index": 0,
            "fields": [
                {"header": "name", "jsonpath": "$.option_value"},
                {"header": "summary", "jsonpath": "$.summary"},
                {"header": "id", "jsonpath": "$.id"}
            ],
            "children_path": "$.children"
        },
        {
            "name": "level2",
            "source": "request",
            "request_index": 1,
            "data_root": "$.data.children",
            "fields": [
                {"header": "name", "jsonpath": "$.option_value"},
                {"header": "summary", "jsonpath": "$.summary"}
            ],
            "children_path": "$.children",
            "params": {
                "first_level_value": "level1.name"
            }
        },
        {
            "name": "level3",
            "source": "children",
            "fields": [
                {"header": "name", "jsonpath": "$.option_value"},
                {"header": "summary", "jsonpath": "$.summary"}
            ],
            "children_path": None
        }
    ],

    "curl_commands": [
        """curl -X POST "{BASE_URL}/api/test/first_level" \\
  -H "Content-Type: application/json" \\
  -d '{"class_name": "事件类型"}'""",
        """curl -X POST "{BASE_URL}/api/test/submenus" \\
  -H "Content-Type: application/json" \\
  -d '{"first_level_value": "{first_level_value}", "class_name": "事件类型"}'"""
    ]
}


# ==================== 自定义异常 ====================

class CurlImportError(Exception):
    """CURL导入基础异常"""
    pass

class ConfigValidationError(CurlImportError):
    """配置验证错误"""
    pass

class RequestError(CurlImportError):
    """请求执行错误"""
    pass

class DataExtractionError(CurlImportError):
    """数据提取错误"""
    pass


# ==================== 核心类 ====================

class JsonPathExtractor:
    """JSONPath 提取器 - V2改进版"""

    @staticmethod
    def extract(data: Any, path: str, always_list: bool = False) -> Any:
        """
        使用 JSONPath 从数据中提取值
        
        Args:
            data: 要提取的数据
            path: JSONPath 表达式
            always_list: 是否始终返回列表（用于children_path等场景）
        """
        if not path:
            return [] if always_list else None
        
        try:
            matches = jsonpath_parse(path).find(data)
            if not matches:
                return [] if always_list else None
            
            values = [m.value for m in matches]
            
            # 如果要求始终返回列表
            if always_list:
                # 如果只有一个值且是列表，返回该列表（如$.data返回数组）
                if len(values) == 1 and isinstance(values[0], list):
                    return values[0]
                return values
            
            # 单值返回原始值，多值返回列表
            return values[0] if len(values) == 1 else values
            
        except JSONPathError as e:
            logger.warning(f"JSONPath解析错误 '{path}': {e}")
            return [] if always_list else None
        except Exception as e:
            logger.error(f"提取失败 '{path}': {e}")
            return [] if always_list else None


class CurlParser:
    """CURL 命令解析器 - V2改进版"""

    @staticmethod
    def parse(cmd: str) -> Dict[str, Any]:
        """
        解析 CURL 命令为结构化数据
        支持：-X, -H, -d, --data, --data-raw 等参数
        """
        result = {
            "method": "GET",
            "url": "",
            "headers": {},
            "json": None,
            "data": None  # 新增：支持form-data
        }
        
        # 标准化：处理换行和转义
        cmd = cmd.replace('\\\n', ' ').replace('\\', '')
        
        # 解析方法
        if m := re.search(r'-X\s+(\w+)', cmd):
            result["method"] = m.group(1).upper()
        
        # 解析URL - 改进：支持多种引号和无引号
        # 尝试匹配带引号的URL
        url_patterns = [
            r'curl\s+(?:-X\s+\w+\s+)?["\']([^"\']+)["\']',  # 带引号
            r'curl\s+(?:-X\s+\w+\s+)?([^\s-]+)',  # 无引号
        ]
        for pattern in url_patterns:
            if m := re.search(pattern, cmd):
                result["url"] = m.group(1).strip()
                break
        
        # 解析Headers
        for h in re.findall(r'-H\s+["\']([^"\']+)["\']', cmd):
            if ':' in h:
                k, v = h.split(':', 1)
                result["headers"][k.strip()] = v.strip()
        
        # 解析JSON数据 (-d 或 --data)
        data_patterns = [
            r'--data-raw\s+["\'](\{.+?\})["\']',
            r'--data\s+["\'](\{.+?\})["\']',
            r'-d\s+["\'](\{.+?\})["\']',
        ]
        for pattern in data_patterns:
            if m := re.search(pattern, cmd, re.DOTALL):
                try:
                    json_str = m.group(1).replace('\\"', '"')
                    result["json"] = json.loads(json_str)
                    break
                except json.JSONDecodeError:
                    pass
        
        # 解析form-data (非JSON格式)
        if not result["json"]:
            for m in re.finditer(r'-d\s+["\']([^"\']+)["\']', cmd):
                data_str = m.group(1)
                if '=' in data_str and '{' not in data_str:
                    # 解析 key=value&key2=value2 格式
                    form_data = {}
                    for pair in data_str.split('&'):
                        if '=' in pair:
                            k, v = pair.split('=', 1)
                            form_data[k] = v
                    if form_data:
                        result["data"] = form_data
        
        return result


class ConfigValidator:
    """配置验证器 - V2新增"""

    @staticmethod
    def validate(config: Dict[str, Any]) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        
        # 检查必需字段
        required_fields = ["levels", "curl_commands"]
        for field in required_fields:
            if field not in config:
                errors.append(f"缺少必需配置: {field}")
        
        if errors:
            return errors
        
        levels = config.get("levels", [])
        curl_commands = config.get("curl_commands", [])
        
        # 验证层级配置
        for i, level in enumerate(levels):
            level_name = level.get("name", f"level_{i}")
            
            # 检查source
            source = level.get("source")
            if source not in ["request", "children"]:
                errors.append(f"层级 '{level_name}': source必须是'request'或'children'")
            
            # request类型检查request_index
            if source == "request":
                req_idx = level.get("request_index")
                if req_idx is None:
                    errors.append(f"层级 '{level_name}': request类型需要request_index")
                elif req_idx < 0 or req_idx >= len(curl_commands):
                    errors.append(f"层级 '{level_name}': request_index {req_idx} 超出范围 (0-{len(curl_commands)-1})")
            
            # 检查fields
            fields = level.get("fields", [])
            if not fields:
                errors.append(f"层级 '{level_name}': fields不能为空")
            for j, field in enumerate(fields):
                if "header" not in field:
                    errors.append(f"层级 '{level_name}' 字段{j}: 缺少header")
                if "jsonpath" not in field:
                    errors.append(f"层级 '{level_name}' 字段{j}: 缺少jsonpath")
        
        # 检查至少有一个request类型的层级
        has_request = any(l.get("source") == "request" for l in levels)
        if not has_request:
            errors.append("至少需要有一个source为'request'的层级")
        
        return errors


class CurlImportEngine:
    """统一 CURL 导入引擎 - V2改进版"""

    def __init__(self, config: Dict[str, Any]):
        # 先验证配置
        errors = ConfigValidator.validate(config)
        if errors:
            raise ConfigValidationError("配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors))
        
        self.config = config
        self.global_vars = config.get("global_vars", {})
        self.levels = config.get("levels", [])
        self.data_root = config.get("data_root", "$.data")
        self.output_file = config.get("output_file", "output.csv")
        self.curl_commands = config.get("curl_commands", [])
        self.extractor = JsonPathExtractor()
        
        # V2新增：请求配置
        self.request_timeout = config.get("request_timeout", 30)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 1.0)
        
        # 统计信息
        self.stats = {
            "requests_made": 0,
            "requests_failed": 0,
            "retries": 0,
            "rows_generated": 0
        }

    def replace_vars(self, obj: Any, context: Dict[str, Any]) -> Any:
        """递归替换变量 - V2改进：添加循环引用保护"""
        return self._replace_vars_recursive(obj, context, set())
    
    def _replace_vars_recursive(self, obj: Any, context: Dict[str, Any], visited: set) -> Any:
        """递归替换变量的内部实现"""
        if isinstance(obj, str):
            result = obj
            for k, v in {**self.global_vars, **context}.items():
                placeholder = f"{{{k}}}"
                if placeholder in result:
                    # 防止循环引用：检查是否已经替换过这个变量
                    if k in visited:
                        logger.warning(f"检测到循环引用: {k}")
                        continue
                    visited.add(k)
                    result = result.replace(placeholder, str(v))
            return result
        elif isinstance(obj, dict):
            return {k: self._replace_vars_recursive(v, context, visited.copy()) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_vars_recursive(i, context, visited.copy()) for i in obj]
        return obj

    def extract_fields(self, item: Dict, level: Dict) -> Dict[str, Any]:
        """从数据项提取字段"""
        result = {}
        for field in level.get("fields", []):
            value = self.extractor.extract(item, field.get("jsonpath", "$"))
            result[field["header"]] = value if value is not None else ""
        return result

    def get_children(self, item: Dict, level: Dict) -> List[Dict]:
        """获取子节点 - V2改进：使用always_list确保返回列表"""
        path = level.get("children_path")
        if path:
            children = self.extractor.extract(item, path, always_list=True)
            return children if isinstance(children, list) else []
        return []

    async def execute_request_with_retry(self, cmd: Dict[str, Any], context: Dict = None, data_root: str = None) -> List[Dict]:
        """执行 HTTP 请求 - V2新增：带重试机制"""
        import aiohttp
        
        context = context or {}
        url = self.replace_vars(cmd["url"], context)
        headers = self.replace_vars(cmd.get("headers", {}), context)
        json_data = self.replace_vars(cmd.get("json"), context)
        form_data = self.replace_vars(cmd.get("data"), context)
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return await self._execute_request_once(cmd, url, headers, json_data, form_data, data_root)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                self.stats["retries"] += 1
                if attempt < self.max_retries - 1:
                    logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}, {self.retry_delay}s后重试...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    break
            except Exception as e:
                # 非网络错误，直接抛出
                raise RequestError(f"请求执行失败: {e}")
        
        self.stats["requests_failed"] += 1
        raise RequestError(f"请求失败 (已重试{self.max_retries}次): {last_error}")

    async def _execute_request_once(self, cmd: Dict[str, Any], url: str, headers: Dict, 
                                     json_data: Any, form_data: Any, data_root: str = None) -> List[Dict]:
        """执行单次请求 - V2改进：检查状态码"""
        import aiohttp
        
        logger.info(f"→ {cmd.get('method', 'GET')} {url[:60]}...")
        self.stats["requests_made"] += 1
        
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            method = getattr(session, cmd["method"].lower())
            kwargs = {"headers": headers}
            
            if json_data:
                kwargs["json"] = json_data
            elif form_data:
                kwargs["data"] = form_data
            
            async with method(url, **kwargs) as resp:
                # V2新增：检查状态码
                if resp.status >= 400:
                    body = await resp.text()
                    raise RequestError(f"HTTP {resp.status}: {body[:200]}")
                
                data = await resp.json()
                
                # 检查API返回的错误码
                if isinstance(data, dict) and data.get("code") not in [None, 200, 0]:
                    msg = data.get("msg", data.get("message", "Unknown error"))
                    raise RequestError(f"API错误: {msg}")
                
                root_path = data_root or self.data_root
                result = self.extractor.extract(data, root_path, always_list=True)
                
                logger.info(f"✓ 返回 {len(result)} 条数据")
                return result

    async def process_level(self,
                           level_idx: int,
                           items: List[Dict],
                           parent_data: Dict[str, Any],
                           parsed_cmds: List[Dict]) -> List[Dict[str, Any]]:
        """递归处理层级 - V2改进：更好的错误处理"""
        results = []

        if level_idx >= len(self.levels) or not items:
            return results

        level = self.levels[level_idx]
        level_name = level["name"]

        for item_idx, item in enumerate(items):
            try:
                level_data = self.extract_fields(item, level)

                row = parent_data.copy()
                for header, value in level_data.items():
                    row[f"{level_name}_{header}"] = value

                children = self.get_children(item, level)
                next_level = self.levels[level_idx + 1] if level_idx + 1 < len(self.levels) else None

                if not next_level:
                    results.append(row)
                elif next_level.get("source") == "children":
                    # V2改进：处理children为空的情况
                    if children:
                        child_results = await self.process_level(
                            level_idx + 1, children, row, parsed_cmds
                        )
                        results.extend(child_results)
                    else:
                        # 没有子节点，但还有后续层级，填充空值
                        results.extend(await self._fill_empty_levels(level_idx + 1, row))
                elif next_level.get("source") == "request":
                    req_idx = next_level.get("request_index")
                    if req_idx is not None and req_idx < len(parsed_cmds):
                        ctx = {}
                        params = next_level.get("params", {})
                        for param_name, field_ref in params.items():
                            if "." in field_ref:
                                ref_level, ref_field = field_ref.split(".", 1)
                                ctx[param_name] = row.get(f"{ref_level}_{ref_field}", "")
                            else:
                                ctx[param_name] = row.get(field_ref, "")

                        try:
                            level_data_root = next_level.get("data_root")
                            next_items = await self.execute_request_with_retry(
                                parsed_cmds[req_idx], ctx, level_data_root
                            )
                            if next_items:
                                child_results = await self.process_level(
                                    level_idx + 1, next_items, row, parsed_cmds
                                )
                                results.extend(child_results)
                            else:
                                # 请求返回空数据，填充空值
                                results.extend(await self._fill_empty_levels(level_idx + 1, row))
                        except Exception as e:
                            logger.error(f"请求失败 (item {item_idx}): {e}")
                            # 请求失败，填充空值而不是跳过
                            results.extend(await self._fill_empty_levels(level_idx + 1, row))
                else:
                    results.append(row)
            except Exception as e:
                logger.error(f"处理层级 '{level_name}' 第 {item_idx} 项时出错: {e}")
                # 继续处理下一项
                continue

        return results
    
    async def _fill_empty_levels(self, start_level_idx: int, parent_row: Dict) -> List[Dict]:
        """V2新增：填充剩余层级的空值"""
        result = parent_row.copy()
        for i in range(start_level_idx, len(self.levels)):
            level = self.levels[i]
            level_name = level["name"]
            for field in level.get("fields", []):
                header = field["header"]
                col_name = f"{level_name}_{header}"
                if col_name not in result:
                    result[col_name] = ""
        return [result]

    async def run(self) -> List[Dict[str, Any]]:
        """运行导入流程 - V2改进：更好的错误处理"""
        logger.info("=" * 60)
        logger.info(f"【{self.config.get('description', 'CURL导入')}】")
        logger.info(f"层级数: {len(self.levels)}, 请求数: {len(self.curl_commands)}")
        logger.info("=" * 60)

        start_time = datetime.now()

        # 解析 CURL 命令
        logger.info("\n[1/3] 解析 CURL 命令...")
        parsed_cmds = []
        for i, cmd in enumerate(self.curl_commands):
            try:
                parsed = CurlParser.parse(cmd)
                parsed_cmds.append(parsed)
                logger.info(f"  [{i}] {parsed['method']} {parsed['url'][:50]}...")
            except Exception as e:
                raise ConfigValidationError(f"解析CURL命令 {i} 失败: {e}")

        # 找到第一个 request 来源的层级
        first_request_level = None
        for i, lvl in enumerate(self.levels):
            if lvl.get("source") == "request":
                first_request_level = i
                break

        if first_request_level is None:
            raise ConfigValidationError("配置错误：没有找到 request 来源的层级")

        # 执行第一个请求
        req_idx = self.levels[first_request_level].get("request_index", 0)
        logger.info(f"\n[2/3] 执行初始请求 (层级: {self.levels[first_request_level]['name']})...")
        
        try:
            initial_data = await self.execute_request_with_retry(parsed_cmds[req_idx])
        except Exception as e:
            raise RequestError(f"初始请求失败: {e}")

        if not initial_data:
            logger.warning("⚠️ 初始请求返回空数据")
            return []

        # 递归处理所有层级
        logger.info(f"\n[3/3] 处理层级数据...")
        all_data = await self.process_level(
            first_request_level, initial_data, {}, parsed_cmds
        )

        self.stats["rows_generated"] = len(all_data)

        # 写入 CSV
        self.write_csv(all_data)

        # 统计
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ 完成！")
        logger.info(f"   总行数: {len(all_data)}")
        logger.info(f"   请求数: {self.stats['requests_made']} (失败: {self.stats['requests_failed']})")
        logger.info(f"   重试数: {self.stats['retries']}")
        logger.info(f"   耗时: {duration:.2f}s")
        logger.info(f"{'='*60}")

        return all_data

    def write_csv(self, data: List[Dict[str, Any]]):
        """写入 CSV - V2改进：临时文件保护"""
        if not data:
            logger.warning("⚠️ 没有数据可写入")
            return

        import tempfile
        import shutil

        # 确保目录存在
        output_dir = os.path.dirname(self.output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 构建表头
        headers = []
        for lvl in self.levels:
            for field in lvl.get("fields", []):
                headers.append(f"{lvl['name']}_{field['header']}")

        # V2改进：使用临时文件，写入成功后再替换
        temp_file = None
        try:
            # 创建临时文件
            fd, temp_file = tempfile.mkstemp(suffix='.csv', dir=output_dir or '.')
            os.close(fd)
            
            with open(temp_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for row in data:
                    writer.writerow({h: row.get(h, "") for h in headers})
            
            # 原子性替换
            shutil.move(temp_file, self.output_file)
            logger.info(f"\n📄 已保存: {self.output_file}")
            
        except Exception as e:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            raise CurlImportError(f"写入CSV失败: {e}")


# ==================== 主函数 ====================

async def main():
    import sys

    config_name = sys.argv[1] if len(sys.argv) > 1 else "single"

    configs = {
        "single": CONFIG_SINGLE,
        "cascade": CONFIG_CASCADE
    }

    if config_name not in configs:
        print(f"用法: python {sys.argv[0]} [single|cascade]")
        print(f"可用配置: {', '.join(configs.keys())}")
        return 1

    config = configs[config_name]
    
    try:
        engine = CurlImportEngine(config)
        await engine.run()
        return 0
    except ConfigValidationError as e:
        logger.error(f"配置错误:\n{e}")
        return 1
    except RequestError as e:
        logger.error(f"请求错误: {e}")
        return 2
    except CurlImportError as e:
        logger.error(f"导入错误: {e}")
        return 3
    except Exception as e:
        logger.exception(f"未预期的错误: {e}")
        return 99


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
