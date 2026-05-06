#!/usr/bin/env python3
"""
测试 LLM 填单接口
页面 = 用户信息页
字段组 = default
字段 = scene_category
API Key = af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR
"""
import json
import requests

# 配置
BASE_URL = "http://localhost:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

# 10轮400客服和用户的对话
CONVERSATION = """
客服: 您好，欢迎致电400客服中心，请问有什么可以帮您？
用户: 你好，我的车在路上抛锚了，需要救援。

客服: 好的，请问您的车辆是什么品牌和型号？
用户: 比亚迪汉EV，2022款。

客服: 收到，请问您现在具体位置在哪里？
用户: 我在京沪高速上海方向，大概是在苏州段。

客服: 好的，能否提供更具体的位置信息，比如公里牌号？
用户: 我看到路边有个牌子写着K1123。

客服: 收到，K1123公里牌。请问您的姓名和联系电话？
用户: 我叫张三，电话是13800138000。

客服: 好的张先生，请问车辆目前是什么情况？
用户: 仪表盘显示电池故障，车子突然失去动力，现在停在应急车道。

客服: 明白，车辆电池故障导致失去动力。请问车上还有几位乘客？
用户: 就我一个人。

客服: 好的，请问您需要拖车服务还是现场维修？
用户: 需要拖车，拖到最近的4S店。

客服: 收到，我们会安排拖车将您的车辆拖至最近的比亚迪4S店。请问您方便接收短信通知吗？
用户: 可以，发到我这个手机号就行。

客服: 好的，已经记录。救援人员预计30分钟内到达，请您在车内等候，注意安全。还有其他问题吗？
用户: 没有了，谢谢。
"""


def test_field_group_api():
    """测试查询字段组配置接口"""
    url = f"{BASE_URL}/autofill/field_group"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "page_name": "用户信息页",
        "group_names": ["default"]
    }

    print("=" * 60)
    print("测试1: 查询字段组配置")
    print("=" * 60)
    print(f"请求: POST {url}")
    print(f"请求体: {json.dumps(data, ensure_ascii=False, indent=2)}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        print(f"\n状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_llm_fill():
    """测试 LLM 填单接口"""
    url = f"{BASE_URL}/autofill/llm/fill"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "page_name": "用户信息页",
        "group_names": ["default"],
        "field_names": ["scene_category"],
        "query": CONVERSATION.strip()
    }

    print("\n" + "=" * 60)
    print("测试2: LLM 填单")
    print("=" * 60)
    print(f"请求: POST {url}")
    print(f"请求体: {json.dumps(data, ensure_ascii=False, indent=2)}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        print(f"\n状态码: {resp.status_code}")
        result = resp.json()
        print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

        # 检查是否成功提取 scene_category
        if result.get("code") == 200:
            extracted = result.get("data", {}).get("result", {})
            print(f"\n提取结果:")
            for key, value in extracted.items():
                print(f"  {key}: {value}")
            return True
        else:
            print(f"\n错误: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"错误: {e}")
        return False


def main():
    print("LLM 填单接口测试脚本")
    print(f"API Key: {API_KEY}")
    print(f"目标页面: 用户信息页")
    print(f"字段组: default")
    print(f"字段: scene_category")

    # 测试1: 查询字段组配置
    success1 = test_field_group_api()

    # 测试2: LLM 填单
    success2 = test_llm_fill()

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"字段组查询: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"LLM 填单: {'✅ 通过' if success2 else '❌ 失败'}")


if __name__ == "__main__":
    main()
