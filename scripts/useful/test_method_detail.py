#!/usr/bin/env python3
"""
详细测试单个LLM方法，获取完整错误信息
"""
import json
import requests
import traceback

API_BASE_URL = "http://localhost:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
PAGE_NAME = "用户信息页"

# 测试失败的方法
METHODS_TO_TEST = ["bind_tools_stream", "custom_fc_non_stream"]

QUERY = """客服：您好，比亚迪汽车客服中心，请问有什么可以帮您？
用户：你好，我的车突然启动不了了，刚才还好好的。
客服：您好，请问您的车辆型号是什么？
用户：我是比亚迪汉EV。"""

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

for method in METHODS_TO_TEST:
    print(f"\n{'='*80}")
    print(f"测试方法: {method}")
    print(f"{'='*80}")

    payload = {
        "page_name": PAGE_NAME,
        "group_fields": {"default": ["一级事件类型", "服务记录类型"]},
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

        print(f"状态码: {response.status_code}")

        if response.status_code != 200:
            print(f"\n错误详情:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, ensure_ascii=False, indent=2))
            except:
                print(response.text)
        else:
            data = response.json()
            print(f"成功!")
            print(json.dumps(data.get("data", {}).get("result", {}), ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"异常: {e}")
        traceback.print_exc()
