#!/usr/bin/env python3
"""
测试新的字段类型：文本输入、下拉单选、下拉多选
"""
import csv
import io
import requests

BASE_URL = "http://localhost:9999/api/v1/autofill"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJleHAiOjE3Nzg0MTE5NDMsImN1cnJlbnRfdGVuYW50X2lkIjowLCJ0ZW5hbnRfZG9tYWluIjoiIn0.7AaanOQA9d3akUWqwSTTDPkC9Pp3RKAzrgnQu3djpo0"


def test_create_fields():
    """测试创建三种类型的字段"""
    print("=" * 60)
    print("测试创建三种类型的字段")
    print("=" * 60)
    
    url = f"{BASE_URL}/field_spec/import"
    headers = {"token": TOKEN}
    
    # 创建CSV - 包含所有三种类型
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 新的CSV表头（移除了选择模式）
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称', '选项来源'])
    
    # 1. 文本输入字段
    writer.writerow([
        "",  # ID为空表示新建
        "test_text_field",
        "文本输入测试字段",
        "text",
        "这是一个文本输入测试字段",
        "*文本批注1\n*文本批注2",
        "启用",
        "localhost",
        "default",
        "",
        ""  # 文本类型没有选项来源
    ])
    
    # 2. 下拉单选字段
    writer.writerow([
        "",  # ID为空表示新建
        "test_select_single",
        "下拉单选测试字段",
        "select_single",
        "这是一个下拉单选测试字段",
        "",
        "启用",
        "localhost",
        "default",
        "",
        "静态选项"
    ])
    
    # 3. 下拉多选字段
    writer.writerow([
        "",  # ID为空表示新建
        "test_select_multi",
        "下拉多选测试字段",
        "select_multi",
        "这是一个下拉多选测试字段",
        "",
        "启用",
        "localhost",
        "default",
        "",
        "静态选项"
    ])
    
    csv_content = output.getvalue()
    print("\n--- CSV内容 ---")
    print(csv_content)
    
    # 导入
    files = {"file": ("test_new_types.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = requests.post(url, headers=headers, files=files)
    result = response.json()
    
    print(f"\n--- 导入结果 ---")
    print(f"Code: {result['code']}")
    print(f"Message: {result.get('msg', 'OK')}")
    if result['code'] == 200:
        print(f"Success count: {result['data']['success_count']}")
        if result['data'].get('errors'):
            print(f"Errors: {result['data']['errors']}")
        print("\n✅ 字段创建成功")
        return True
    else:
        print(f"Error: {result.get('msg', 'Unknown error')}")
        return False


def test_import_options():
    """测试导入选项"""
    print("\n" + "=" * 60)
    print("测试导入选项")
    print("=" * 60)
    
    url = f"{BASE_URL}/field_spec/import"
    headers = {"token": TOKEN}
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    # 下拉单选的选项
    writer.writerow(["", "test_select_single", "A", "选项A", "选项A的说明", "*选项A批注", "启用", "localhost", "default", ""])
    writer.writerow(["", "test_select_single", "B", "选项B", "选项B的说明", "", "启用", "localhost", "default", ""])
    
    # 下拉多选的选项
    writer.writerow(["", "test_select_multi", "X", "选项X", "选项X的说明", "", "启用", "localhost", "default", ""])
    writer.writerow(["", "test_select_multi", "Y", "选项Y", "选项Y的说明", "*选项Y批注1\n*选项Y批注2", "启用", "localhost", "default", ""])
    writer.writerow(["", "test_select_multi", "Z", "选项Z", "选项Z的说明", "", "启用", "localhost", "default", ""])
    
    csv_content = output.getvalue()
    print("\n--- CSV内容 ---")
    print(csv_content)
    
    # 导入
    files = {"file": ("test_options.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = requests.post(url, headers=headers, files=files)
    result = response.json()
    
    print(f"\n--- 导入结果 ---")
    print(f"Code: {result['code']}")
    print(f"Message: {result.get('msg', 'OK')}")
    if result['code'] == 200:
        print(f"Success count: {result['data']['success_count']}")
        if result['data'].get('errors'):
            print(f"Errors: {result['data']['errors']}")
        print("\n✅ 选项导入成功")
        return True
    else:
        print(f"Error: {result.get('msg', 'Unknown error')}")
        return False


def test_export():
    """测试导出功能"""
    print("\n" + "=" * 60)
    print("测试导出功能")
    print("=" * 60)
    
    # 先获取字段列表找到ID
    url = f"{BASE_URL}/field_spec/list"
    headers = {"token": TOKEN}
    params = {"page": 1, "page_size": 100}
    
    response = requests.get(url, headers=headers, params=params)
    result = response.json()
    
    if result['code'] == 200:
        # 找到测试字段的ID
        target_ids = []
        for item in result['data']['items']:
            if item['field_name'] in ['test_text_field', 'test_select_single', 'test_select_multi']:
                target_ids.append(item['id'])
        
        if target_ids:
            # 导出这些字段
            url = f"{BASE_URL}/field_spec/export"
            headers = {"token": TOKEN, "Content-Type": "application/json"}
            data = {"ids": target_ids}
            
            response = requests.post(url, headers=headers, json=data)
            result = response.json()
            
            if result['code'] == 200:
                print("\n--- 基础字段CSV ---")
                print(result['data']['base_csv'])
                print("\n--- 选项详情CSV ---")
                print(result['data']['options_csv'])
                return True
    
    print("导出失败")
    return False


if __name__ == "__main__":
    # 测试创建字段
    if test_create_fields():
        # 测试导入选项
        test_import_options()
        # 测试导出
        test_export()
        
        print("\n" + "=" * 60)
        print("请打开浏览器检查以下字段：")
        print("1. test_text_field - 应为'文本输入'类型")
        print("2. test_select_single - 应为'下拉单选'类型")
        print("3. test_select_multi - 应为'下拉多选'类型，应显示选项数限制配置")
        print("=" * 60)
