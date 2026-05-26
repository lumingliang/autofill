#!/usr/bin/env python3
"""
统一 CURL 导入引擎
支持：单请求树形展平、多请求级联展平
核心思想：通过配置定义层级来源（request/children）统一处理
"""

import asyncio
import json
import csv
import re
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JSONPathError


# ==================== 配置示例 ====================

CONFIG_SINGLE = {
    "description": "单请求树形结构展平 - 事件类型",
    "output_file": "single_output.csv",
    "global_vars": {
        "TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJleHAiOjE3ODAxMDExMDAsImN1cnJlbnRfdGVuYW50X2lkIjozLCJ0ZW5hbnRfZG9tYWluIjoiIn0.vX0vLFzm93vpkI0_x2dqOYucajcAgoI67T1SJaOpVvU",
        "BASE_URL": "http://localhost:3200"
    },
    "data_root": "$.data",

    # 层级配置：定义每个层级的数据来源和提取规则
    "levels": [
        {
            "name": "level1",
            "source": "request",  # 来源：request = 从请求获取
            "request_index": 0,   # 使用第0个请求
            "fields": [
                {"header": "name", "jsonpath": "$.option_value"},
                {"header": "summary", "jsonpath": "$.summary"},
                {"header": "id", "jsonpath": "$.id"},
                {"header": "code", "jsonpath": "$.code"}
            ],
            "children_path": "$.children"  # 子节点路径，None表示无子节点
        },
        {
            "name": "level2",
            "source": "children",  # 来源：children = 从上级children展平
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
            "children_path": None  # 最后一层
        }
    ],

    # CURL 命令列表
    "curl_commands": [
        """curl '{BASE_URL}/api/v1/autofill/dropdown/tree?app_name=test_app&class_name=%E4%BA%8B%E4%BB%B6%E7%B1%BB%E5%9E%8B' \\
   -H 'Accept: application/json' \\
   -H 'token: {TOKEN}'"""
    ]
}


CONFIG_CASCADE = {
    "description": "级联请求展平 - 事件类型(2层请求+1层children)",
    "output_file": "cascade_output.csv",
    "global_vars": {
        "API_KEY": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
        "BASE_URL": "http://localhost:9999",
        "CLASS_NAME": "事件类型"
    },
    "data_root": "$.data",

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
            "source": "request",  # 级联请求，从第1个请求获取
            "request_index": 1,
            "data_root": "$.data.children",  # 特殊：第二个请求的数据在children字段
            "fields": [
                {"header": "name", "jsonpath": "$.option_value"},
                {"header": "summary", "jsonpath": "$.summary"}
            ],
            "children_path": "$.children",
            # 参数映射：{参数名: "层级名.字段名"}
            "params": {
                "parent_value": "level1.name"  # 使用level1的name字段
            }
        },
        {
            "name": "level3",
            "source": "children",  # 从level2的children展平
            "fields": [
                {"header": "name", "jsonpath": "$.option_value"},
                {"header": "summary", "jsonpath": "$.summary"}
            ],
            "children_path": None
        }
    ],

    "curl_commands": [
        """curl -X POST "http://localhost:9999/api/autofill/dropdown/first_level" \\
  -H "Authorization: Bearer {API_KEY}" \\
  -H "Content-Type: application/json" \\
  -d '{"class_name": "事件类型"}'""",
        """curl -X POST "http://localhost:9999/api/autofill/dropdown/submenus_tree" \\
  -H "Authorization: Bearer {API_KEY}" \\
  -H "Content-Type: application/json" \\
  -d '{"first_level_value": "{parent_value}", "class_name": "事件类型"}'"""
    ]
}


# ==================== 核心类 ====================

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
            print(f"  ⚠️ JSONPath错误: {e}")
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
    """统一 CURL 导入引擎"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.global_vars = config.get("global_vars", {})
        self.levels = config.get("levels", [])
        self.data_root = config.get("data_root", "$.data")
        self.output_file = config.get("output_file", "output.csv")
        self.curl_commands = config.get("curl_commands", [])
        self.extractor = JsonPathExtractor()
        
        # 构建层级索引映射
        self.level_map = {lvl["name"]: i for i, lvl in enumerate(self.levels)}
        
        # 构建请求索引到层级的映射
        self.request_level_map = {}
        for lvl in self.levels:
            if lvl.get("source") == "request" and "request_index" in lvl:
                self.request_level_map[lvl["request_index"]] = lvl["name"]

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
        import aiohttp

        context = context or {}
        url = self.replace_vars(cmd["url"], context)
        headers = self.replace_vars(cmd.get("headers", {}), context)
        json_data = self.replace_vars(cmd.get("json"), context)

        print(f"  → {cmd.get('method', 'GET')} {url[:60]}...")

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
                print(f"  ✓ 返回 {len(result)} 条数据")
                return result

    async def process_level(self, 
                           level_idx: int,
                           items: List[Dict],
                           parent_data: Dict[str, Any],
                           parsed_cmds: List[Dict]) -> List[Dict[str, Any]]:
        """递归处理层级"""
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
                row[f"{level_name}_{header}"] = value
            
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
                        # field_ref 格式: "level_name.field_name"
                        if "." in field_ref:
                            ref_level, ref_field = field_ref.split(".", 1)
                            ctx[param_name] = row.get(f"{ref_level}_{ref_field}", "")

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
                        print(f"  ✗ 请求失败: {e}")
                        results.append(row)
            else:
                # 无子节点，添加当前行
                results.append(row)
        
        return results

    async def run(self) -> List[Dict[str, Any]]:
        """运行导入流程"""
        print("=" * 60)
        print(f"【{self.config.get('description', 'CURL导入')}】")
        print(f"层级数: {len(self.levels)}, 请求数: {len(self.curl_commands)}")
        print("=" * 60)
        
        start_time = datetime.now()
        
        # 解析 CURL 命令
        print("\n[1/3] 解析 CURL 命令...")
        parsed_cmds = [CurlParser.parse(cmd) for cmd in self.curl_commands]
        for i, cmd in enumerate(parsed_cmds):
            print(f"  [{i}] {cmd['method']} {cmd['url'][:50]}...")
        
        # 找到第一个 request 来源的层级
        first_request_level = None
        for i, lvl in enumerate(self.levels):
            if lvl.get("source") == "request":
                first_request_level = i
                break
        
        if first_request_level is None:
            print("❌ 配置错误：没有找到 request 来源的层级")
            return []
        
        # 执行第一个请求
        print(f"\n[2/3] 执行初始请求 (层级: {self.levels[first_request_level]['name']})...")
        req_idx = self.levels[first_request_level].get("request_index", 0)
        initial_data = await self.execute_request(parsed_cmds[req_idx])
        
        if not initial_data:
            print("❌ 初始请求无数据")
            return []
        
        # 递归处理所有层级
        print(f"\n[3/3] 处理层级数据...")
        all_data = await self.process_level(
            first_request_level, initial_data, {}, parsed_cmds
        )
        
        # 写入 CSV
        self.write_csv(all_data)
        
        # 统计
        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n✅ 完成！共 {len(all_data)} 行，耗时 {duration:.2f}s")
        
        return all_data

    def write_csv(self, data: List[Dict[str, Any]]):
        """写入 CSV"""
        if not data:
            return
        
        # 构建表头
        headers = []
        for lvl in self.levels:
            for field in lvl.get("fields", []):
                headers.append(f"{lvl['name']}_{field['header']}")
        
        with open(self.output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in data:
                writer.writerow({h: row.get(h, "") for h in headers})
        
        print(f"\n📄 已保存: {self.output_file}")


# ==================== 主函数 ====================

async def main():
    import sys
    
    # 选择配置：single 或 cascade
    config_name = sys.argv[1] if len(sys.argv) > 1 else "single"
    
    configs = {
        "single": CONFIG_SINGLE,
        "cascade": CONFIG_CASCADE
    }
    
    if config_name not in configs:
        print(f"用法: python {sys.argv[0]} [single|cascade]")
        print(f"可用配置: {', '.join(configs.keys())}")
        return
    
    config = configs[config_name]
    engine = CurlImportEngine(config)
    await engine.run()


if __name__ == "__main__":
    asyncio.run(main())
