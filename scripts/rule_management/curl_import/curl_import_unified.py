#!/usr/bin/env python3
"""
统一 CURL 导入引擎 - 命令行入口
复用 app.services.rule_management.curl_import_engine 的核心逻辑
"""
import asyncio
import sys
from typing import Dict, Any

# 添加项目根目录到路径
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from app.services.rule_management.curl_import_engine import CurlImportEngine


# ==================== 配置示例 ====================

CONFIG_SINGLE = {
    "description": "单请求树形结构展平 - 测试接口",
    "output_file": "test_server/single_output.csv",
    "global_vars": {
        "BASE_URL": "http://localhost:6666"
    },
    "data_root": "$.data",

    # 层级配置：定义每个层级的数据来源和提取规则
    "levels": [
        {
            "name": "level1",
            "source": "request",  # 来源：request = 从请求获取
            "request_index": 0,   # 使用第0个请求
            "fields": [
                {"header": "name_level1", "jsonpath": "$.option_value"},
                {"header": "summary_level1", "jsonpath": "$.summary"},
                {"header": "id_level1", "jsonpath": "$.id"},
                {"header": "code_level1", "jsonpath": "$.code"}
            ],
            "children_path": "$.children"  # 子节点路径，None表示无子节点
        },
        {
            "name": "level2",
            "source": "children",  # 来源：children = 从上级children展平
            "fields": [
                {"header": "name_level2", "jsonpath": "$.option_value"},
                {"header": "summary_level2", "jsonpath": "$.summary"},
                {"header": "id_level2", "jsonpath": "$.id"}
            ],
            "children_path": "$.children"
        },
        {
            "name": "level3",
            "source": "children",
            "fields": [
                {"header": "name_level3", "jsonpath": "$.option_value"},
                {"header": "summary_level3", "jsonpath": "$.summary"}
            ],
            "children_path": None  # 最后一层
        }
    ],

    # CURL 命令列表
    "curl_commands": [
        """curl -X POST "{BASE_URL}/api/test/tree" \\
  -H "Content-Type: application/json" \\
  -d '{"class_name": "事件类型"}'"""
    ]
}


CONFIG_CASCADE = {
    "description": "级联请求展平 - 测试接口",
    "output_file": "test_server/cascade_output.csv",
    "global_vars": {
        "BASE_URL": "http://localhost:6666"
    },
    "data_root": "$.data",

    "levels": [
        {
            "name": "level1",
            "source": "request",
            "request_index": 0,
            "fields": [
                {"header": "name_level1", "jsonpath": "$.option_value"},
                {"header": "summary_level1", "jsonpath": "$.summary"},
                {"header": "id_level1", "jsonpath": "$.id"}
            ],
            "children_path": "$.children"
        },
        {
            "name": "level2",
            "source": "request",  # 级联请求，从第1个请求获取
            "request_index": 1,
            "data_root": "$.data.children",  # 特殊：第二个请求的数据在children字段
            "fields": [
                {"header": "name_level2", "jsonpath": "$.option_value"},
                {"header": "summary_level2", "jsonpath": "$.summary"},
                {"header": "id_level2", "jsonpath": "$.id"}
            ],
            "children_path": "$.children",
            # 参数映射：{参数名: "header_name"}
            "params": {
                "first_level_value": "name_level1"  # 直接使用 header 名称
            }
        },
        {
            "name": "level3",
            "source": "children",  # 从level2的children展平
            "fields": [
                {"header": "name_level3", "jsonpath": "$.option_value"},
                {"header": "summary_level3", "jsonpath": "$.summary"}
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


# ==================== 主函数 ====================

async def main():
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
    
    # 使用 CurlImportEngine 执行导入
    engine = CurlImportEngine(config)
    result = await engine.fetch_data_as_csv()
    
    # 保存到文件
    output_file = config.get("output_file", "output.csv")
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        f.write(result["csv_content"])
    
    print(f"\n📄 已保存: {output_file}")
    print(f"✅ 完成！共 {result['row_count']} 行")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
