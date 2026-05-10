#!/usr/bin/env python3
"""
详细测试各方法的字段提取情况
"""
import json
import requests

API_BASE_URL = "http://localhost:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
PAGE_NAME = "用户信息页"

# 需要提取的字段
REQUIRED_FIELDS = ["一级事件类型", "服务记录类型"]

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

print("=" * 80)
print("详细测试各方法的字段提取情况")
print(f"要求提取字段: {REQUIRED_FIELDS}")
print("=" * 80)

for method in METHODS:
    print(f"\n{'='*80}")
    print(f"方法: {method}")
    print(f"{'='*80}")

    payload = {
        "page_name": PAGE_NAME,
        "group_fields": {"default": REQUIRED_FIELDS},
        "query": QUERY,
        "method": method
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/autofill/llm/fill",
            json=payload,
            headers=HEADERS,
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200 or data.get("success"):
                result = data.get("data", {}).get("result", {})
                method_used = data.get("data", {}).get("_meta", {}).get("method_used", "unknown")

                print(f"✓ 成功")
                print(f"  实际使用方法: {method_used}")
                print(f"  提取字段数: {len(result)}")

                # 检查每个要求字段的提取情况
                print(f"\n  字段提取详情:")
                for field in REQUIRED_FIELDS:
                    if field in result:
                        value = result[field]
                        if isinstance(value, dict):
                            if "value" in value:
                                if isinstance(value["value"], dict):
                                    print(f"    ✓ {field}: {value['value'].get('label', value['value'])}")
                                else:
                                    print(f"    ✓ {field}: {value['value']}")
                            else:
                                print(f"    ✓ {field}: {value}")
                        else:
                            print(f"    ✓ {field}: {value}")
                    else:
                        print(f"    ✗ {field}: 未提取")

                # 显示原始结果
                print(f"\n  原始结果:")
                print(json.dumps(result, ensure_ascii=False, indent=4))
            else:
                print(f"✗ API错误: {data.get('message', '未知错误')}")
        else:
            print(f"✗ HTTP错误: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  错误信息: {error_data.get('msg', '未知错误')}")
            except:
                print(f"  响应内容: {response.text[:200]}")

    except Exception as e:
        print(f"✗ 异常: {e}")
