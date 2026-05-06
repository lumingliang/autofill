#!/usr/bin/env python3
"""
导入 test_field_with_group 字段并关联到字段组
"""
import csv
import io
import requests

BASE_URL = "http://localhost:9999/api/v1/autofill"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJleHAiOjE3Nzg0MTE5NDMsImN1cnJlbnRfdGVuYW50X2lkIjowLCJ0ZW5hbnRfZG9tYWluIjoiIn0.7AaanOQA9d3akUWqwSTTDPkC9Pp3RKAzrgnQu3djpo0"


def import_field():
    """导入 test_field_with_group 字段"""
    print("=" * 60)
    print("导入 test_field_with_group 字段")
    print("=" * 60)
    
    # 创建CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    # 新增字段 - 使用字段组名称
    writer.writerow([
        "",  # 无ID，表示新增
        "test_field_with_group",
        "测试字段-带字段组",
        "text",
        "这是测试字段的填写指引",
        "*测试批注1\n*测试批注2",
        "启用",
        "",  # 租户域名留空，使用当前用户租户
        "default",  # 字段组名称
        ""   # 页面名称
    ])
    
    csv_content = output.getvalue()
    print("\n--- CSV内容 ---")
    print(csv_content)
    
    # 导入
    url = f"{BASE_URL}/field_spec/import"
    headers = {"token": TOKEN}
    files = {"file": ("test_field_with_group.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    response = requests.post(url, headers=headers, files=files)
    result = response.json()
    
    print(f"\n--- 导入结果 ---")
    print(f"Code: {result['code']}")
    print(f"Message: {result.get('msg', 'OK')}")
    if result['code'] == 200:
        print(f"Success count: {result['data']['success_count']}")
        if result['data'].get('errors'):
            print(f"Errors: {result['data']['errors']}")
        return True
    else:
        print(f"Error: {result.get('msg', 'Unknown error')}")
        return False


if __name__ == "__main__":
    import_field()
    print("\n导入完成，请在浏览器中检查字段组关联情况")
