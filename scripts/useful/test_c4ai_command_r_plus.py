#!/usr/bin/env python3
"""
测试 C4AI-Command-R-Plus 模型的所有LLM方法
"""
import json
import requests
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
os.environ.setdefault("APP_ENV", "dev")

import asyncio
from app.core.init_app import init_db
from app.models.llm_config import LLMConfig

API_BASE_URL = "http://localhost:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
PAGE_NAME = "用户信息页"

# C4AI-Command-R-Plus 模型ID
MODEL_ID = "openai/LLM-Research/c4ai-command-r-plus-08-2024"

METHODS = [
    # "with_structured_output",
    # "bind_tools_non_stream",
    "bind_tools_stream",
    # "custom_fc_non_stream",
    # "custom_fc_stream",
    # "pydantic_parser",
    # "json_parser"
]

# 测试查询 - 包含明确的字段信息
QUERY = """客服：您好，比亚迪汽车客服中心，请问有什么可以帮您？
用户：你好，我的车突然启动不了了，刚才还好好的。
客服：您好，请问您的车辆型号是什么？
用户：我是比亚迪汉EV。
客服：请问是什么问题呢？
用户：仪表盘显示动力系统故障，可能是电池问题。"""

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

async def test_method(method: str, model: str = None):
    """测试单个方法"""
    payload = {
        "page_name": PAGE_NAME,
        "group_fields": {"default": ["一级事件类型", "服务记录类型"]},
        "query": QUERY,
        "method": method
    }

    if model:
        payload["model"] = model

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/autofill/llm/fill",
            json=payload,
            headers=HEADERS,
            timeout=120
        )
        response.raise_for_status()
        data = response.json()

        if data.get("code") == 200 or data.get("success"):
            result = data.get("data", {}).get("result", {})
            method_used = data.get("data", {}).get("_meta", {}).get("method_used", "unknown")
            return {
                "success": True,
                "method_used": method_used,
                "fields_count": len(result),
                "result": result
            }
        else:
            return {
                "success": False,
                "error": data.get('message', '未知错误')
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def main():
    await init_db()

    # 获取 C4AI-Command-R-Plus 配置
    config = await LLMConfig.filter(name="C4AI-Command-R-Plus", is_active=True).first()
    if not config:
        print("错误: 找不到 C4AI-Command-R-Plus 配置")
        return

    print("=" * 80)
    print("测试 C4AI-Command-R-Plus 模型的所有LLM方法")
    print(f"模型ID: {MODEL_ID}")
    print(f"测试字段: 一级事件类型, 服务记录类型")
    print("=" * 80)

    results = {}

    for method in METHODS:
        print(f"\n{'='*60}")
        print(f"测试方法: {method}")
        print(f"{'='*60}")

        result = await test_method(method, MODEL_ID)
        results[method] = result

        if result.get("success"):
            print(f"✓ 成功")
            print(f"  实际使用方法: {result.get('method_used')}")
            print(f"  提取字段数: {result.get('fields_count')}")

            # 显示提取的字段详情
            extracted_result = result.get("result", {})
            print(f"\n  字段提取详情:")
            for field_name in ["一级事件类型", "服务记录类型"]:
                if field_name in extracted_result:
                    field_data = extracted_result[field_name]
                    if isinstance(field_data, dict) and "value" in field_data:
                        value_data = field_data["value"]
                        if isinstance(value_data, dict):
                            print(f"    ✓ {field_name}: {value_data.get('label', value_data)}")
                        else:
                            print(f"    ✓ {field_name}: {value_data}")
                    else:
                        print(f"    ✓ {field_name}: {field_data}")
                else:
                    print(f"    ✗ {field_name}: 未提取")

            # 显示原始结果
            print(f"\n  原始结果:")
            print(json.dumps(extracted_result, ensure_ascii=False, indent=4))
        else:
            print(f"✗ 失败")
            print(f"  错误: {result.get('error', '未知错误')}")

    # 输出总结
    print("\n" + "=" * 80)
    print("测试结果总结")
    print("=" * 80)

    success_count = sum(1 for r in results.values() if r.get("success"))
    print(f"\n成功: {success_count}/{len(METHODS)}")
    print()

    for method, result in results.items():
        if result.get("success"):
            fields_count = result.get("fields_count", 0)
            print(f"✓ {method}: {fields_count} 字段")
        else:
            error = result.get("error", "")[:50]
            print(f"✗ {method}: {error}")

    # 保存结果
    output_file = "/tmp/test_c4ai_command_r_plus.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存到: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
