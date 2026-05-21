#!/usr/bin/env python3
"""
测试字段说明生成格式
"""
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.services.autofill.prompt_service import build_fields_instructions

# 测试数据：模拟字段配置
test_fields = [
    {
        "field_type": "text",
        "field_name": "customer_name",
        "field_label": "客户姓名",
        "fill_instruction": "必填；提取客户真实姓名；格式：2-10个汉字",
        "corrections": [{"text": "如用户未提供，填写\"未提供\""}],
        "options": {}
    },
    {
        "field_type": "select_single",
        "field_name": "一级事件类型",
        "field_label": "一级事件类型",
        "fill_instruction": "根据用户意图选择；必填",
        "corrections": [],
        "options": {
            "items": [
                {
                    "label": "道路救援",
                    "fill_instruction": "车辆故障、事故等需要救援的情况",
                    "corrections": [{"text": "用户提到抛锚、爆胎、事故等选此项"}],
                    "is_deleted": False
                },
                {
                    "label": "保养预约",
                    "fill_instruction": "定期保养、维护等",
                    "corrections": [],
                    "is_deleted": False
                },
                {
                    "label": "质量问题",
                    "fill_instruction": "产品质量投诉、故障反馈",
                    "corrections": [{"text": "用户抱怨产品质量问题选此项"}],
                    "is_deleted": False
                }
            ]
        }
    },
    {
        "field_type": "select_multi",
        "field_name": "服务需求",
        "field_label": "服务需求",
        "fill_instruction": "选择用户提到的所有服务需求",
        "corrections": [],
        "options": {
            "min_selections": 1,
            "max_selections": 3,
            "items": [
                {
                    "label": "上门维修",
                    "fill_instruction": "需要技术人员上门",
                    "corrections": [],
                    "is_deleted": False
                },
                {
                    "label": "拖车服务",
                    "fill_instruction": "车辆无法行驶需要拖车",
                    "corrections": [],
                    "is_deleted": False
                },
                {
                    "label": "备用车",
                    "fill_instruction": "需要提供备用车辆",
                    "corrections": [],
                    "is_deleted": False
                }
            ]
        }
    }
]

print("=" * 80)
print("PLAIN 模式（简化格式）")
print("=" * 80)
plain_result = build_fields_instructions(test_fields, is_plain=True)
print(plain_result)

print("\n" + "=" * 80)
print("JSON 模式（结构化格式）")
print("=" * 80)
json_result = build_fields_instructions(test_fields, is_plain=False)
print(json_result)
