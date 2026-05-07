#!/usr/bin/env python3
"""
测试单选字段功能
"""
import json
import requests

# 配置
BASE_URL = "http://localhost:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"


def create_single_select_field():
    """创建一个单选字段"""
    url = f"{BASE_URL}/autofill/field_group/upsert"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "page_name": "用户信息页",
        "group_name": "test_single",
        "fields": [
            {
                "field_name": "scene_category",
                "field_label": "场景分类",
                "field_type": "select",
                "fill_instruction": "请根据对话内容判断场景分类",
                "options": {
                    "items": [
                        {"label": "道路救援请求", "value": "rescue", "fill_instruction": "用户需要道路救援"},
                        {"label": "咨询投诉", "value": "complaint", "fill_instruction": "用户咨询或投诉"},
                        {"label": "预约服务", "value": "booking", "fill_instruction": "用户预约服务"}
                    ],
                    "source": "static",
                    "selection_mode": 0  # 0=单选
                }
            }
        ]
    }

    print("=" * 60)
    print("创建单选字段")
    print("=" * 60)
    print(f"请求: POST {url}")
    print(f"请求体:\n{json.dumps(data, ensure_ascii=False, indent=2)}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        print(f"\n状态码: {resp.status_code}")
        result = resp.json()
        print(f"响应:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

        if result.get("code") == 200:
            print("\n✅ 创建成功！")
            return True
        else:
            print(f"\n❌ 创建失败: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


def test_single_select_fill():
    """测试单选填单"""
    url = f"{BASE_URL}/autofill/llm/fill"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 测试对话 - 用户需要道路救援
    conversation = "你好，我的车在高速上抛锚了，需要紧急救援！"

    data = {
        "page_name": "用户信息页",
        "group_names": ["test_single"],
        "field_names": ["scene_category"],
        "query": conversation.strip()
    }

    print("\n" + "=" * 60)
    print("测试单选 LLM 填单")
    print("=" * 60)
    print(f"请求: POST {url}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        result = resp.json()

        print(f"\n状态码: {resp.status_code}")
        print(f"响应:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

        if result.get("code") == 200:
            extracted = result.get("data", {}).get("result", {})
            scene_category = extracted.get("scene_category")

            print(f"\n提取结果:")
            print(f"  scene_category: {json.dumps(scene_category, ensure_ascii=False, indent=2)}")
            print(f"  类型: {type(scene_category)}")

            # 验证 enriched 格式
            if isinstance(scene_category, dict) and scene_category.get("type") == "select_single":
                value = scene_category.get("value", {})
                print(f"\n✅ 单选测试通过！返回 enriched 格式")
                print(f"   - type: {scene_category.get('type')}")
                print(f"   - value: {value.get('value')}")
                print(f"   - label: {value.get('label')}")
                return True
            else:
                print(f"\n⚠️  单选测试未通过！格式不正确: {type(scene_category)}")
                return False
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


def main():
    print("测试单选字段功能")
    print(f"API Key: {API_KEY}")

    # 步骤1: 创建单选字段
    success1 = create_single_select_field()

    # 步骤2: 测试单选填单
    if success1:
        success2 = test_single_select_fill()
    else:
        success2 = False

    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print(f"创建单选字段: {'✅ 成功' if success1 else '❌ 失败'}")
    print(f"单选填单测试: {'✅ 通过' if success2 else '❌ 未通过'}")


if __name__ == "__main__":
    main()
