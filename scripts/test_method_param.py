#!/usr/bin/env python3
"""
测试指定 method 参数
"""
import json
import requests

# 配置
BASE_URL = "http://localhost:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"


def test_with_method(method_name):
    """测试指定 method 参数"""
    url = f"{BASE_URL}/autofill/llm/fill"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "page_name": "用户信息页",
        "group_names": ["test_single"],
        "field_names": ["scene_category"],
        "query": "你好，我的车在高速上抛锚了，需要紧急救援！",
        "method": method_name  # 指定调用方法
    }

    print(f"\n{'='*60}")
    print(f"测试 method={method_name}")
    print(f"{'='*60}")
    print(f"请求: POST {url}")
    print(f"请求体:\n{json.dumps(data, ensure_ascii=False, indent=2)}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        result = resp.json()

        print(f"\n状态码: {resp.status_code}")

        if result.get("code") == 200:
            meta = result.get("data", {}).get("_meta", {})
            method_used = meta.get("method_used", "unknown")
            print(f"✅ 请求成功！")
            print(f"   - 指定 method: {method_name}")
            print(f"   - 实际使用 method: {method_used}")
            print(f"   - 模型: {meta.get('model')}")
            print(f"   - 延迟: {meta.get('latency_ms')}ms")
            return True
        else:
            print(f"❌ 请求失败: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_without_method():
    """测试不指定 method 参数（使用默认）"""
    url = f"{BASE_URL}/autofill/llm/fill"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "page_name": "用户信息页",
        "group_names": ["test_single"],
        "field_names": ["scene_category"],
        "query": "你好，我的车在高速上抛锚了，需要紧急救援！"
        # 不指定 method
    }

    print(f"\n{'='*60}")
    print(f"测试不指定 method（使用默认）")
    print(f"{'='*60}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        result = resp.json()

        if result.get("code") == 200:
            meta = result.get("data", {}).get("_meta", {})
            print(f"✅ 请求成功！")
            print(f"   - 实际使用 method: {meta.get('method_used', 'unknown')}")
            print(f"   - 模型: {meta.get('model')}")
            return True
        else:
            print(f"❌ 请求失败: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def main():
    print("测试 method 参数功能")
    print(f"API Key: {API_KEY}")

    # 测试不同的 method
    methods = [
        None,  # 不指定
        "with_structured_output",
        "bind_tools",
        "custom_fc_non_stream"
    ]

    results = []
    for method in methods:
        if method is None:
            success = test_without_method()
        else:
            success = test_with_method(method)
        results.append((method or "default", success))

    print("\n" + "="*60)
    print("总结")
    print("="*60)
    for method, success in results:
        print(f"  {method}: {'✅ 通过' if success else '❌ 失败'}")


if __name__ == "__main__":
    main()
