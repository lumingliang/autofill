#!/usr/bin/env python3
"""
调试 group_fields 参数
"""
import json
import requests

BASE_URL = "http://localhost:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"


def test_group_fields():
    """测试 group_fields 参数"""
    url = f"{BASE_URL}/autofill/llm/fill"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 使用 group_fields 参数
    data = {
        "page_name": "用户信息页",
        "group_fields": {
            "default": ["救援-二三级"],
            "服务记录-道路救援请求": []
        },
        "query": "测试查询"
    }
    
    print("=" * 70)
    print("测试 group_fields 参数")
    print("=" * 70)
    print(f"请求体: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        result = resp.json()
        
        if result.get("code") == 200:
            print(f"\n✅ 请求成功")
            print(f"\n提取结果:")
            extracted = result.get("data", {}).get("result", {})
            for key, value in extracted.items():
                print(f"  {key}: {value}")
            
            # 打印调试信息
            debug_info = result.get("data", {}).get("_debug", {})
            if debug_info:
                print(f"\n调试信息 - Function Schema:")
                tools = debug_info.get("tools", [])
                if tools:
                    func = tools[0].get("function", {})
                    params = func.get("parameters", {})
                    print(f"  函数名: {func.get('name')}")
                    print(f"  描述: {func.get('description')}")
                    print(f"  参数属性:")
                    for prop_name, prop_info in params.get("properties", {}).items():
                        print(f"    - {prop_name}: {prop_info.get('type', 'string')}")
                    print(f"  required: {params.get('required', [])}")
        else:
            print(f"\n❌ 错误: {result.get('msg')}")
    except Exception as e:
        print(f"\n❌ 异常: {e}")


if __name__ == "__main__":
    test_group_fields()
