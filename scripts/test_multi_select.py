#!/usr/bin/env python3
"""
测试多选字段功能
"""
import json
import requests

# 配置
BASE_URL = "http://localhost:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"


def create_multi_select_field():
    """创建一个多选字段"""
    url = f"{BASE_URL}/autofill/field_group/upsert"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "page_name": "用户信息页",
        "group_name": "default",
        "fields": [
            {
                "field_name": "service_types",
                "field_label": "服务类型",
                "field_type": "select",
                "fill_instruction": "请根据对话内容判断用户需要哪些服务",
                "options": {
                    "items": [
                        {"label": "拖车服务", "value": "1", "fill_instruction": "用户需要拖车"},
                        {"label": "现场维修", "value": "2", "fill_instruction": "用户需要现场维修"},
                        {"label": "紧急救援", "value": "3", "fill_instruction": "用户需要紧急救援"},
                        {"label": "送油服务", "value": "4", "fill_instruction": "用户需要送油"},
                        {"label": "换胎服务", "value": "5", "fill_instruction": "用户需要换胎"}
                    ],
                    "source": "static",
                    "selection_mode": 1,  # 1=多选
                    "min_selections": 1,
                    "max_selections": 3   # 最多选3个
                }
            }
        ]
    }

    print("=" * 60)
    print("创建多选字段")
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


def test_multi_select_fill():
    """测试多选填单"""
    url = f"{BASE_URL}/autofill/llm/fill"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 测试对话 - 用户需要多个服务
    conversation = """
客服: 您好，欢迎致电400客服中心，请问有什么可以帮您？
用户: 你好，我的车在高速上抛锚了，需要救援。

客服: 好的，请问具体是什么情况？
用户: 车子突然熄火，打不着火了，而且轮胎也爆了。

客服: 明白，车辆无法启动且轮胎损坏。请问您需要拖车还是现场维修？
用户: 能现场修好吗？

客服: 轮胎问题可以现场更换，但发动机故障可能需要拖车。我们可以先派师傅过去检查。
用户: 那先派师傅来吧，如果修不好再拖车。

客服: 好的，我们会安排师傅携带备胎和维修工具前往。请问还有其他需要吗？
用户: 车子没油了，能顺便带点油吗？

客服: 可以，我们会安排送油服务。请问您现在的具体位置？
用户: 我在京沪高速K1123处。

客服: 收到，我们会安排紧急救援、现场维修、送油服务。还有其他问题吗？
用户: 没有了，谢谢。
"""

    data = {
        "page_name": "用户信息页",
        "group_names": ["default"],
        "field_names": ["service_types"],
        "query": conversation.strip()
    }

    print("\n" + "=" * 60)
    print("测试多选 LLM 填单")
    print("=" * 60)
    print(f"请求: POST {url}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        result = resp.json()

        print(f"\n状态码: {resp.status_code}")
        print(f"响应:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

        if result.get("code") == 200:
            extracted = result.get("data", {}).get("result", {})
            service_types = extracted.get("service_types")

            print(f"\n提取结果:")
            print(f"  service_types: {json.dumps(service_types, ensure_ascii=False, indent=2)}")
            print(f"  类型: {type(service_types)}")

            # 验证新的 enriched 格式
            if isinstance(service_types, dict) and service_types.get("type") == "select_multi":
                values = service_types.get("values", [])
                labels = service_types.get("labels", [])
                print(f"\n✅ 多选测试通过！返回 enriched 格式")
                print(f"   - type: {service_types.get('type')}")
                print(f"   - values: {values}")
                print(f"   - labels: {labels}")
                return True
            elif isinstance(service_types, list):
                # 兼容旧格式
                print(f"\n✅ 多选测试通过！返回数组格式（旧格式）")
                return True
            else:
                print(f"\n⚠️  多选测试未通过！格式不正确: {type(service_types)}")
                return False
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


def main():
    print("测试多选字段功能")
    print(f"API Key: {API_KEY}")

    # 步骤1: 创建多选字段
    success1 = create_multi_select_field()

    # 步骤2: 测试多选填单
    if success1:
        success2 = test_multi_select_fill()
    else:
        success2 = False

    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print(f"创建多选字段: {'✅ 成功' if success1 else '❌ 失败'}")
    print(f"多选填单测试: {'✅ 通过' if success2 else '❌ 未通过'}")


if __name__ == "__main__":
    main()
