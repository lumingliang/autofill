#!/usr/bin/env python3
"""
使用指定模型测试所有LLM调用方法
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

METHODS = [
    "with_structured_output",
    "bind_tools_non_stream",
    "bind_tools_stream",
    "custom_fc_non_stream",
    "custom_fc_stream",
    "pydantic_parser",
    "json_parser"
]

QUERY = """客服：您好，比亚迪汽车客服中心，请问有什么可以帮您？
用户：你好，我的车突然启动不了了，刚才还好好的。
客服：您好，请问您的车辆型号是什么？
用户：我是比亚迪汉EV。"""

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

    # 获取所有配置
    configs = await LLMConfig.filter(is_active=True).all()

    print("=" * 80)
    print("使用不同模型测试所有LLM调用方法")
    print("=" * 80)

    all_results = {}

    for config in configs:
        model_name = config.name
        litellm_params = config.litellm_params or {}
        model_id = litellm_params.get('model', 'unknown')

        print(f"\n{'='*80}")
        print(f"测试模型: {model_name} ({model_id})")
        print(f"{'='*80}")

        model_results = {}

        for method in METHODS:
            print(f"\n  测试方法: {method}...", end=" ", flush=True)
            result = await test_method(method, model_id)
            model_results[method] = result

            if result.get("success"):
                print(f"✓ 成功 ({result.get('fields_count', 0)} 字段)")
            else:
                print(f"✗ 失败: {result.get('error', '未知错误')[:50]}")

        all_results[model_name] = model_results

        # 输出该模型总结
        success_count = sum(1 for r in model_results.values() if r.get("success"))
        print(f"\n  模型 {model_name} 总结: {success_count}/{len(METHODS)} 方法成功")

    # 最终总结
    print("\n" + "=" * 80)
    print("所有模型测试结果总结")
    print("=" * 80)

    for model_name, model_results in all_results.items():
        success_count = sum(1 for r in model_results.values() if r.get("success"))
        print(f"\n{model_name}:")
        for method, result in model_results.items():
            status = "✓" if result.get("success") else "✗"
            print(f"  {status} {method}")
        print(f"  总计: {success_count}/{len(METHODS)} 成功")

    # 保存结果
    output_file = "/tmp/test_methods_by_model.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存到: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
