#!/usr/bin/env python3
"""
优化 scene_category 字段的 fill_instruction
通过 upsert_field_group 接口更新字段指引
"""
import json
import requests

# 配置
BASE_URL = "http://localhost:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

# 优化后的 fill_instruction（字段级别 - 整体判断逻辑）
OPTIMIZED_INSTRUCTION = """请根据对话内容判断场景分类。

【核心判断原则】
1. 优先识别用户的核心诉求（用户想要什么？）
2. 当用户明确请求救援/拖车服务时，必须选择"道路救援请求"
3. 当用户仅描述故障现象、咨询问题时，选择对应的故障类型

【关键区分】
- 用户说"我的车坏了" → 咨询故障，选对应故障类型
- 用户说"我的车坏了，需要救援" → 请求救援，必须选"道路救援请求"""

# 优化后的 options（选项级别 - 每个选项的具体指引）
# 对齐表结构：每个 item 包含 label, value, fill_instruction
OPTIMIZED_OPTIONS = {
    "items": [
        {
            "label": "预约充电故障",
            "value": "1",
            "fill_instruction": "用户反馈预约充电功能异常，仅涉及充电设置问题，不涉及救援请求"
        },
        {
            "label": "动力电池故障",
            "value": "2",
            "fill_instruction": "用户反馈动力电池异常报警，咨询故障原因或维修，未主动请求救援"
        },
        {
            "label": "车机系统卡顿",
            "value": "3",
            "fill_instruction": "用户反馈车机系统卡顿/黑屏/死机，属于软件问题咨询"
        },
        {
            "label": "空调制冷异常",
            "value": "4",
            "fill_instruction": "用户反馈空调制冷效果差或不制冷，属于舒适性问题咨询"
        },
        {
            "label": "制动系统报警",
            "value": "5",
            "fill_instruction": "用户反馈制动系统异常报警，咨询故障原因，注意：如用户明确要求救援则选'道路救援请求'"
        },
        {
            "label": "车辆无法启动",
            "value": "6",
            "fill_instruction": "用户反馈车辆无法启动/打不着火，咨询故障原因或维修方案，未主动说需要救援"
        },
        {
            "label": "异响投诉",
            "value": "7",
            "fill_instruction": "用户反馈车辆行驶中有异响，咨询异响来源"
        },
        {
            "label": "漆面质量问题",
            "value": "8",
            "fill_instruction": "用户反馈车辆漆面存在质量问题"
        },
        {
            "label": "保养预约",
            "value": "9",
            "fill_instruction": "用户来电预约车辆保养服务"
        },
        {
            "label": "道路救援请求",
            "value": "10",
            "fill_instruction": "【最高优先级】用户明确请求道路救援、拖车服务。关键词：需要救援、需要拖车、请求救援、紧急救援、抛锚了需要救援。只要用户明确表达需要救援服务，无论是什么故障，都必须选此项！"
        }
    ],
    "source": "static"
}


def update_field_instruction():
    """更新 scene_category 字段的 fill_instruction"""
    url = f"{BASE_URL}/autofill/field_group/upsert"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 构建请求体 - 同时更新字段级别和选项级别的 fill_instruction
    # is_append: True=合并新旧 options，False=覆盖（默认）
    data = {
        "page_name": "用户信息页",
        "group_name": "default",
        "is_append": False,  # 设置为 True 可合并新旧 options，而不是覆盖
        "fields": [
            {
                "field_name": "scene_category",
                "field_label": "场景分类",
                "field_type": "select",
                "fill_instruction": OPTIMIZED_INSTRUCTION,
                "options": OPTIMIZED_OPTIONS
            }
        ]
    }

    print("=" * 60)
    print("更新 scene_category 字段 fill_instruction")
    print("=" * 60)
    print(f"请求: POST {url}")
    print(f"请求体:\n{json.dumps(data, ensure_ascii=False, indent=2)}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        print(f"\n状态码: {resp.status_code}")
        result = resp.json()
        print(f"响应:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

        if result.get("code") == 200:
            print("\n✅ 更新成功！")
            return True
        else:
            print(f"\n❌ 更新失败: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


def test_llm_fill():
    """测试 LLM 填单效果"""
    url = f"{BASE_URL}/autofill/llm/fill"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 测试对话 - 用户明确请求救援
    conversation = """
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

    data = {
        "page_name": "用户信息页",
        "group_names": ["default"],
        "field_names": ["scene_category"],
        "query": conversation.strip()
    }

    print("\n" + "=" * 60)
    print("测试 LLM 填单效果")
    print("=" * 60)
    print(f"请求: POST {url}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        result = resp.json()

        if result.get("code") == 200:
            extracted = result.get("data", {}).get("result", {})
            scene_category = extracted.get("scene_category")

            print(f"\n提取结果:")
            print(f"  scene_category: {scene_category}")

            if scene_category == "道路救援请求":
                print("\n✅ 测试通过！正确识别为'道路救援请求'")
                return True
            else:
                print(f"\n⚠️  测试未通过！期望'道路救援请求'，实际'{scene_category}'")
                return False
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


def main():
    print("优化 scene_category 字段 fill_instruction")
    print(f"API Key: {API_KEY}")
    print(f"目标页面: 用户信息页")
    print(f"字段组: default")
    print(f"字段: scene_category")

    # 步骤1: 更新字段指引
    success1 = update_field_instruction()

    # 步骤2: 测试效果
    if success1:
        success2 = test_llm_fill()
    else:
        success2 = False

    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print(f"更新字段指引: {'✅ 成功' if success1 else '❌ 失败'}")
    print(f"LLM填单测试: {'✅ 通过' if success2 else '❌ 未通过'}")


if __name__ == "__main__":
    main()
