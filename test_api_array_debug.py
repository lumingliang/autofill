#!/usr/bin/env python3
"""
通过API接口测试多选字段，打印完整请求和响应
"""
import json
import requests

# 配置
BASE_URL = "http://localhost:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"


def create_multi_select_field():
    """创建一个多选字段用于测试"""
    url = f"{BASE_URL}/autofill/field_group/upsert"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "page_name": "用户信息页",
        "group_name": "test_array",
        "fields": [
            {
                "field_name": "test_multi_field",
                "field_label": "测试多选字段",
                "field_type": "select",
                "fill_instruction": "请从对话中识别用户选择的选项",
                "options": {
                    "items": [
                        {"label": "选项A", "value": "A"},
                        {"label": "选项B", "value": "B"},
                        {"label": "选项C", "value": "C"}
                    ],
                    "source": "static",
                    "selection_mode": 1,  # 1=多选
                    "min_selections": 1,
                    "max_selections": 3
                }
            }
        ]
    }

    print("=" * 70)
    print("【步骤1】创建多选字段")
    print("=" * 70)
    print(f"请求: POST {url}")
    print(f"请求体:\n{json.dumps(data, ensure_ascii=False, indent=2)}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        print(f"\n状态码: {resp.status_code}")
        result = resp.json()
        print(f"响应:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

        if result.get("code") == 200:
            print("\n✅ 字段创建成功")
            return True
        else:
            print(f"\n❌ 创建失败: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


def test_array_fill():
    """测试多选字段填单，打印完整请求和响应"""
    url = f"{BASE_URL}/autofill/llm/fill"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 测试对话 - 用户选择多个选项
    conversation = "我需要选项A和选项C"

    data = {
        "page_name": "用户信息页",
        "group_names": ["test_array"],
        "query": conversation
    }

    print("\n" + "=" * 70)
    print("【步骤2】测试多选填单")
    print("=" * 70)
    print(f"请求: POST {url}")
    print(f"请求体:\n{json.dumps(data, ensure_ascii=False, indent=2)}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        print(f"\n状态码: {resp.status_code}")
        result = resp.json()
        print(f"响应:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

        if result.get("code") == 200:
            extracted = result.get("data", {}).get("result", {})
            test_value = extracted.get("test_multi_field")
            
            print("\n" + "=" * 70)
            print("【结果分析】")
            print("=" * 70)
            print(f"提取值: {test_value}")
            print(f"类型: {type(test_value)}")
            print(f"是否为列表: {isinstance(test_value, list)}")
            
            if isinstance(test_value, list):
                print("\n✅ 正确返回数组格式")
            else:
                print("\n❌ 错误：返回非数组格式")
                
            # 打印debug信息
            debug_info = result.get("data", {}).get("_debug", {})
            if debug_info:
                print("\n【Debug信息】")
                print(f"  使用的方法: {result.get('data', {}).get('_meta', {}).get('method_used')}")
                print(f"  模型: {result.get('data', {}).get('_meta', {}).get('model')}")
                
                # 打印传递给LLM的tools
                tools = debug_info.get("tools", [])
                if tools:
                    print("\n【传递给LLM的Function Schema】")
                    print(json.dumps(tools, ensure_ascii=False, indent=2))
            
            return extracted
        else:
            print(f"\n❌ 错误: {result.get('msg')}")
            return None
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return None


def main():
    print("=" * 70)
    print("API接口测试 - 多选字段数组返回")
    print("=" * 70)
    
    # 创建字段
    if create_multi_select_field():
        # 测试填单
        result = test_array_fill()
        
        if result:
            print("\n" + "=" * 70)
            print("【测试完成】")
            print("=" * 70)
        else:
            print("\n❌ 填单测试失败")
    else:
        print("\n❌ 字段创建失败")


if __name__ == "__main__":
    main()
