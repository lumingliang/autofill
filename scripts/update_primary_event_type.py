#!/usr/bin/env python3
"""
更新一级事件类型字段的指引，优化救援场景的识别
"""
import json
import requests

# 配置
BASE_URL = "http://localhost:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"


def update_primary_event_type():
    """
    更新一级事件类型字段的 fill_instruction
    使用 field_group/upsert 接口
    """
    url = f"{BASE_URL}/autofill/field_group/upsert"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 优化后的一级事件类型选项和指引
    data = {
        "page_name": "用户信息页",
        "group_name": "default",
        "fields": [
            {
                "field_name": "一级事件类型",
                "field_label": "一级事件类型",
                "field_type": "select",
                "fill_instruction": """【核心判断原则】优先识别用户的核心诉求和紧急程度：
1. 当用户明确表示需要救援、拖车、紧急帮助时 → 必须选择"救援"
2. 当用户反馈车辆故障并需要维修时 → 选择"售后投诉"
3. 当用户咨询产品信息时 → 选择"产品咨询"
4. 当用户预约服务时 → 选择"4S店"

【关键区分】
- 用户说"需要救援/需要拖车/紧急救援" → 必须选"救援"
- 用户说"车坏了需要修/有故障" → 选"售后投诉"
- 用户说"想了解车型/价格" → 选"产品咨询"
- 用户说"想预约保养/维修" → 选"4S店"

请根据用户的第一诉求选择最准确的事件类型。""",
                "options": {
                    "source": "static",
                    "items": [
                        {
                            "label": "智能网联",
                            "value": "1",
                            "fill_instruction": "用户咨询智能网联相关问题，如APP、车机系统、远程控制等"
                        },
                        {
                            "label": "产品咨询",
                            "value": "2",
                            "fill_instruction": "用户咨询车辆产品信息，如配置、价格、性能等"
                        },
                        {
                            "label": "4S店",
                            "value": "3",
                            "fill_instruction": "用户需要预约4S店服务，如保养、维修预约等"
                        },
                        {
                            "label": "救援",
                            "value": "4",
                            "fill_instruction": "【最高优先级】用户明确请求道路救援、拖车服务、紧急救援。关键词：需要救援、需要拖车、紧急救援、抛锚了、车坏了走不了。只要用户明确表达需要救援服务，无论是什么故障，都必须选此项！"
                        },
                        {
                            "label": "业务互转",
                            "value": "5",
                            "fill_instruction": "用户需要转接其他业务部门"
                        },
                        {
                            "label": "表扬",
                            "value": "6",
                            "fill_instruction": "用户对服务或产品表示赞扬"
                        },
                        {
                            "label": "建议",
                            "value": "7",
                            "fill_instruction": "用户提出产品或服务建议"
                        },
                        {
                            "label": "售前投诉",
                            "value": "8",
                            "fill_instruction": "用户在购车前对销售服务不满"
                        },
                        {
                            "label": "售后投诉",
                            "value": "9",
                            "fill_instruction": "用户反馈车辆故障需要维修，但未明确请求救援服务"
                        },
                        {
                            "label": "内部投诉",
                            "value": "10",
                            "fill_instruction": "用户投诉内部服务问题"
                        },
                        {
                            "label": "三级报警",
                            "value": "11",
                            "fill_instruction": "系统三级报警事件"
                        }
                    ]
                }
            }
        ]
    }
    
    print("=" * 70)
    print("更新一级事件类型字段指引")
    print("=" * 70)
    print(f"请求: POST {url}")
    print(f"请求体: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        print(f"\n状态码: {resp.status_code}")
        result = resp.json()
        print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result.get("code") == 200:
            print("\n✅ 更新成功")
            return True
        else:
            print(f"\n❌ 更新失败: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return False


if __name__ == "__main__":
    update_primary_event_type()
