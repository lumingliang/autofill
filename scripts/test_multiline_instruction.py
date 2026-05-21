#!/usr/bin/env python3
"""
测试多行填写说明的 Prompt 生成
"""
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.services.autofill.prompt_service import build_fields_instructions

# 测试数据：模拟带有多行填写说明的下拉选项
test_fields = [
    {
        "field_type": "select_single",
        "field_name": "二级事件类型",
        "field_label": "二级事件类型",
        "fill_instruction": "根据用户描述选择具体的二级事件类型",
        "corrections": [],
        "options": {
            "items": [
                {
                    "label": "现场维修-电瓶搭电",
                    "fill_instruction": "现场可修复的故障\n电瓶没电时搭电启动\n需要携带搭电设备",
                    "corrections": [{"text": "用户提到电瓶没电、无法启动时选择此项\n注意确认车辆位置"}],
                    "is_deleted": False
                },
                {
                    "label": "现场维修-轮胎更换",
                    "fill_instruction": "轮胎相关问题\n包括爆胎、漏气、扎钉等",
                    "corrections": [],
                    "is_deleted": False
                },
                {
                    "label": "拖车服务",
                    "fill_instruction": "车辆无法现场修复\n需要拖至维修点",
                    "corrections": [{"text": "用户要求拖车服务时选择"}],
                    "is_deleted": False
                }
            ]
        }
    }
]

print("=" * 80)
print("测试多行填写说明的 Prompt 生成")
print("=" * 80)

result = build_fields_instructions(test_fields, is_plain=False)
print(result)

print("\n" + "=" * 80)
print("验证：检查是否保留了多行格式")
print("=" * 80)

# 检查关键内容是否在结果中
if "现场可修复的故障" in result and "电瓶没电时搭电启动" in result:
    print("✅ 多行填写说明已正确保留")
else:
    print("❌ 多行填写说明可能丢失")

if "用户提到电瓶没电" in result and "注意确认车辆位置" in result:
    print("✅ 多行批注已正确保留")
else:
    print("❌ 多行批注可能丢失")
