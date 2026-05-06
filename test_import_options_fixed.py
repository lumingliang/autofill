#!/usr/bin/env python3
"""
导入选项到 complete_select_field 字段（填入 tenant_domain 和 group_name）
"""
import csv
import io
import requests

BASE_URL = "http://localhost:9999/api/v1/autofill"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJleHAiOjE3Nzg0MTE5NDMsImN1cnJlbnRfdGVuYW50X2lkIjowLCJ0ZW5hbnRfZG9tYWluIjoiIn0.7AaanOQA9d3akUWqwSTTDPkC9Pp3RKAzrgnQu3djpo0"


def import_options():
    """导入选项"""
    print("=" * 60)
    print("导入选项到 complete_select_field 字段")
    print("=" * 60)
    
    # 创建CSV - 填入 tenant_domain 和 group_name
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    # 添加3个选项 - 填入 localhost 和 default
    writer.writerow(["", "complete_select_field", "10", "选项十", "选项十的说明", "*选项十批注", "启用", "localhost", "default", ""])
    writer.writerow(["", "complete_select_field", "20", "选项二十", "选项二十的说明", "", "启用", "localhost", "default", ""])
    writer.writerow(["", "complete_select_field", "30", "选项三十", "选项三十的说明", "*选项三十批注1\n*选项三十批注2", "启用", "localhost", "default", ""])
    
    csv_content = output.getvalue()
    print("\n--- CSV内容 ---")
    print(csv_content)
    
    # 导入
    url = f"{BASE_URL}/field_spec/import"
    headers = {"token": TOKEN}
    files = {"file": ("test_options_fixed.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    response = requests.post(url, headers=headers, files=files)
    result = response.json()
    
    print(f"\n--- 导入结果 ---")
    print(f"Code: {result['code']}")
    print(f"Message: {result.get('msg', 'OK')}")
    if result['code'] == 200:
        print(f"Success count: {result['data']['success_count']}")
        if result['data'].get('errors'):
            print(f"Errors: {result['data']['errors']}")
        print("\n✅ 导入完成，请在浏览器中检查选项")
        return True
    else:
        print(f"Error: {result.get('msg', 'Unknown error')}")
        return False


if __name__ == "__main__":
    import_options()
