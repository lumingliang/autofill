#!/usr/bin/env python3
"""
最终测试导入导出功能，包含所有必要字段（修复后）
"""
import csv
import io
import requests

BASE_URL = "http://localhost:9999/api/v1/autofill"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJleHAiOjE3Nzg0MTE5NDMsImN1cnJlbnRfdGVuYW50X2lkIjowLCJ0ZW5hbnRfZG9tYWluIjoiIn0.7AaanOQA9d3akUWqwSTTDPkC9Pp3RKAzrgnQu3djpo0"


def import_field_with_options():
    """导入新字段（包含选择模式和选项来源）"""
    print("=" * 60)
    print("测试导入新字段（包含选择模式和选项来源）")
    print("=" * 60)
    
    # 创建CSV - 包含所有必要字段
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头（包含选择模式和选项来源）
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称', '选择模式', '选项来源'])
    
    # 添加一个新下拉字段 - 多选 + 静态选项
    writer.writerow([
        "",  # ID为空表示新建
        "test_select_multi_v2",
        "多选静态选项测试字段V2",
        "select",
        "这是一个多选静态选项测试字段",
        "*测试批注1\n*测试批注2",
        "启用",
        "localhost",
        "default",
        "",
        "多选",  # 选择模式：单选/多选
        "静态选项"  # 选项来源：静态选项/API接口
    ])
    
    # 添加一个新下拉字段 - 单选 + API接口
    writer.writerow([
        "",  # ID为空表示新建
        "test_select_single_api_v2",
        "单选API接口测试字段V2",
        "select",
        "这是一个单选API接口测试字段",
        "",
        "启用",
        "localhost",
        "default",
        "",
        "单选",  # 选择模式：单选/多选
        "API接口"  # 选项来源：静态选项/API接口
    ])
    
    csv_content = output.getvalue()
    print("\n--- CSV内容 ---")
    print(csv_content)
    
    # 导入
    url = f"{BASE_URL}/field_spec/import"
    headers = {"token": TOKEN}
    files = {"file": ("test_field_final.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    response = requests.post(url, headers=headers, files=files)
    result = response.json()
    
    print(f"\n--- 导入结果 ---")
    print(f"Code: {result['code']}")
    print(f"Message: {result.get('msg', 'OK')}")
    if result['code'] == 200:
        print(f"Success count: {result['data']['success_count']}")
        if result['data'].get('errors'):
            print(f"Errors: {result['data']['errors']}")
        print("\n✅ 字段导入成功")
        return True
    else:
        print(f"Error: {result.get('msg', 'Unknown error')}")
        return False


def import_options():
    """测试导入选项"""
    print("\n" + "=" * 60)
    print("测试导入选项到 test_select_multi_v2")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    # 添加选项
    writer.writerow(["", "test_select_multi_v2", "A", "选项A", "选项A的说明", "*选项A批注", "启用", "localhost", "default", ""])
    writer.writerow(["", "test_select_multi_v2", "B", "选项B", "选项B的说明", "", "启用", "localhost", "default", ""])
    writer.writerow(["", "test_select_multi_v2", "C", "选项C", "选项C的说明", "*选项C批注1\n*选项C批注2", "启用", "localhost", "default", ""])
    
    csv_content = output.getvalue()
    print("\n--- CSV内容 ---")
    print(csv_content)
    
    # 导入
    url = f"{BASE_URL}/field_spec/import"
    headers = {"token": TOKEN}
    files = {"file": ("test_options_final.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
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
        # 找到 test_select_multi_v2 的ID
        target_id = None
        for item in result['data']['items']:
            if item['field_name'] == 'test_select_multi_v2':
                target_id = item['id']
                break
        
        if target_id:
            # 导出该字段
            url = f"{BASE_URL}/field_spec/export"
            headers = {"token": TOKEN, "Content-Type": "application/json"}
            data = {"ids": [target_id]}
            
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
    # 测试导入字段
    if import_field_with_options():
        # 测试导入选项
        import_options()
        # 测试导出
        test_export()
        
        print("\n" + "=" * 60)
        print("请打开浏览器检查以下字段：")
        print("1. test_select_multi_v2 - 选择模式应为'多选'，选项来源应为'静态选项'")
        print("2. test_select_single_api_v2 - 选择模式应为'单选'，选项来源应为'API接口'")
        print("3. 选项列表是否正确显示（不需要手动选择静态选项）")
        print("=" * 60)
