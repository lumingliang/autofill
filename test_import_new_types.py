#!/usr/bin/env python3
"""
测试导入功能 - 修改已有字段
"""
import csv
import io
import requests

BASE_URL = "http://localhost:9999/api/v1/autofill"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJleHAiOjE3Nzg0MTE5NDMsImN1cnJlbnRfdGVuYW50X2lkIjowLCJ0ZW5hbnRfZG9tYWluIjoiIn0.7AaanOQA9d3akUWqwSTTDPkC9Pp3RKAzrgnQu3djpo0"


def test_import_modify():
    """测试修改已有字段"""
    print("=" * 60)
    print("测试修改已有字段")
    print("=" * 60)
    
    url = f"{BASE_URL}/field_spec/import"
    headers = {"token": TOKEN}
    
    # 创建CSV - 修改文本字段的批注
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 新的CSV表头
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称', '选项来源'])
    
    # 修改文本字段的批注
    writer.writerow([
        "34",  # ID不变表示修改
        "test_text_field",
        "文本输入测试字段-已修改",
        "text",
        "这是一个文本输入测试字段-已修改",
        "*新的批注1\n*新的批注2\n*新的批注3",  # 修改批注
        "启用",
        "tenant-a",
        "default",
        "用户信息页",
        ""
    ])
    
    csv_content = output.getvalue()
    print("\n--- CSV内容 ---")
    print(csv_content)
    
    # 导入
    files = {"file": ("test_modify.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = requests.post(url, headers=headers, files=files)
    result = response.json()
    
    print(f"\n--- 导入结果 ---")
    print(f"Code: {result['code']}")
    print(f"Message: {result.get('msg', 'OK')}")
    if result['code'] == 200:
        print(f"Success count: {result['data']['success_count']}")
        if result['data'].get('errors'):
            print(f"Errors: {result['data']['errors']}")
        print("\n✅ 字段修改成功")
        return True
    else:
        print(f"Error: {result.get('msg', 'Unknown error')}")
        return False


def test_import_modify_options():
    """测试修改选项"""
    print("\n" + "=" * 60)
    print("测试修改选项")
    print("=" * 60)
    
    url = f"{BASE_URL}/field_spec/import"
    headers = {"token": TOKEN}
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    # 修改选项A的批注
    writer.writerow(["35", "test_select_single", "A", "选项A-已修改", "选项A的说明-已修改", "*修改后的选项A批注", "启用", "tenant-a", "default", "用户信息页"])
    
    # 添加新选项C
    writer.writerow(["", "test_select_single", "C", "选项C-新增", "选项C的说明", "*新选项批注", "启用", "tenant-a", "default", "用户信息页"])
    
    csv_content = output.getvalue()
    print("\n--- CSV内容 ---")
    print(csv_content)
    
    # 导入
    files = {"file": ("test_modify_options.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = requests.post(url, headers=headers, files=files)
    result = response.json()
    
    print(f"\n--- 导入结果 ---")
    print(f"Code: {result['code']}")
    print(f"Message: {result.get('msg', 'OK')}")
    if result['code'] == 200:
        print(f"Success count: {result['data']['success_count']}")
        if result['data'].get('errors'):
            print(f"Errors: {result['data']['errors']}")
        print("\n✅ 选项修改成功")
        return True
    else:
        print(f"Error: {result.get('msg', 'Unknown error')}")
        return False


if __name__ == "__main__":
    # 测试修改字段
    test_import_modify()
    # 测试修改选项
    test_import_modify_options()
    
    print("\n" + "=" * 60)
    print("请打开浏览器检查修改后的字段：")
    print("1. test_text_field - 字段标签和批注应该已更新")
    print("2. test_select_single - 选项A应该已修改，选项C应该已添加")
    print("=" * 60)
