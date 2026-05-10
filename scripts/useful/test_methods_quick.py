#!/usr/bin/env python3
"""
快速测试所有LLM调用方法
"""
import json
import requests
import sys

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

PAYLOAD = {
    "page_name": PAGE_NAME,
    "group_fields": {"default": ["一级事件类型", "服务记录类型"]},
    "query": QUERY
}

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

print("=" * 80)
print("快速测试所有LLM调用方法")
print("=" * 80)

results = {}

for method in METHODS:
    print(f"\n{'='*60}")
    print(f"测试方法: {method}")
    print(f"{'='*60}")

    payload = PAYLOAD.copy()
    payload["method"] = method

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/autofill/llm/fill",
            json=payload,
            headers=HEADERS,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        if data.get("code") == 200 or data.get("success"):
            result = data.get("data", {}).get("result", {})
            method_used = data.get("data", {}).get("_meta", {}).get("method_used", "unknown")

            print(f"✓ 成功")
            print(f"  实际使用方法: {method_used}")
            print(f"  提取字段数: {len(result)}")

            # 显示提取的关键字段
            if result:
                for key in ["一级事件类型", "服务记录类型"]:
                    if key in result:
                        value = result[key]
                        if isinstance(value, dict) and "value" in value:
                            if isinstance(value["value"], dict):
                                print(f"  {key}: {value['value'].get('label', value['value'])}")
                            else:
                                print(f"  {key}: {value['value']}")

            results[method] = {
                "success": True,
                "method_used": method_used,
                "fields_count": len(result),
                "result": result
            }
        else:
            print(f"✗ 失败: {data.get('message', '未知错误')}")
            results[method] = {
                "success": False,
                "error": data.get('message', '未知错误')
            }

    except Exception as e:
        print(f"✗ 异常: {e}")
        results[method] = {
            "success": False,
            "error": str(e)
        }

# 输出总结
print("\n" + "=" * 80)
print("测试结果总结")
print("=" * 80)

success_count = sum(1 for r in results.values() if r.get("success"))
print(f"成功: {success_count}/{len(METHODS)}")
print()

for method, result in results.items():
    status = "✓" if result.get("success") else "✗"
    error = result.get("error", "")
    if error:
        print(f"{status} {method}: {error}")
    else:
        print(f"{status} {method}: {result.get('fields_count', 0)} 字段")

# 保存结果
output_file = "/tmp/test_methods_quick.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n详细结果已保存到: {output_file}")
