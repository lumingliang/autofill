#!/usr/bin/env python3
"""
测试混合情况：多行 vs 分号分隔的多条规则
"""
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.services.autofill.prompt_service import build_fields_instructions

# 测试数据1：纯多行（无分号）
test_fields_multiline = [
    {
        "field_type": "select_single",
        "field_name": "test1",
        "field_label": "测试1-纯多行",
        "fill_instruction": "",
        "corrections": [],
        "options": {
            "items": [
                {
                    "label": "选项A",
                    "fill_instruction": "第一行描述\n第二行描述\n第三行描述",
                    "corrections": [],
                    "is_deleted": False
                }
            ]
        }
    }
]

# 测试数据2：分号分隔的多条规则
test_fields_semicolon = [
    {
        "field_type": "select_single",
        "field_name": "test2",
        "field_label": "测试2-分号分隔",
        "fill_instruction": "",
        "corrections": [],
        "options": {
            "items": [
                {
                    "label": "选项B",
                    "fill_instruction": "规则1；规则2；规则3",
                    "corrections": [],
                    "is_deleted": False
                }
            ]
        }
    }
]

# 测试数据3：序号分隔的多条规则
test_fields_numbered = [
    {
        "field_type": "select_single",
        "field_name": "test3",
        "field_label": "测试3-序号分隔",
        "fill_instruction": "",
        "corrections": [],
        "options": {
            "items": [
                {
                    "label": "选项C",
                    "fill_instruction": "1. 第一条规则\n2. 第二条规则\n3. 第三条规则",
                    "corrections": [],
                    "is_deleted": False
                }
            ]
        }
    }
]

print("=" * 80)
print("测试1：纯多行（无分号）- 应该保留整体格式")
print("=" * 80)
result1 = build_fields_instructions(test_fields_multiline, is_plain=False)
print(result1)

print("\n" + "=" * 80)
print("测试2：分号分隔 - 应该分割成多条规则")
print("=" * 80)
result2 = build_fields_instructions(test_fields_semicolon, is_plain=False)
print(result2)

print("\n" + "=" * 80)
print("测试3：序号分隔 - 应该分割成多条规则")
print("=" * 80)
result3 = build_fields_instructions(test_fields_numbered, is_plain=False)
print(result3)
