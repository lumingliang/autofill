#!/usr/bin/env python3
"""
测试新增字段时是否正确关联字段组
"""
import csv
import io
import requests

BASE_URL = "http://localhost:9999/api/v1/autofill"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJleHAiOjE3Nzg0MTE5NDMsImN1cnJlbnRfdGVuYW50X2lkIjowLCJ0ZW5hbnRfZG9tYWluIjoiIn0.7AaanOQA9d3akUWqwSTTDPkC9Pp3RKAzrgnQu3djpo0"


def test_import_new_field():
    """测试导入新增字段并关联到字段组"""
    print("=" * 60)
    print("测试导入新增字段并关联到字段组")
    print("=" * 60)
    
    # 创建测试CSV - 新增字段
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
        "*测试批注",
        "启用",
        "",  # 租户域名留空，使用当前用户租户
        "default",  # 字段组名称
        ""   # 页面名称
    ])
    
    csv_content = output.getvalue()
    print("\n--- 测试CSV内容 ---")
    print(csv_content)
    
    # 导入
    url = f"{BASE_URL}/field_spec/import"
    headers = {"token": TOKEN}
    files = {"file": ("test_new_field.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    response = requests.post(url, headers=headers, files=files)
    result = response.json()
    
    print(f"\n--- 导入结果 ---")
    print(f"Code: {result['code']}")
    print(f"Message: {result.get('msg', 'OK')}")
    if result['code'] == 200:
        print(f"Success count: {result['data']['success_count']}")
        print(f"Delete count: {result['data'].get('delete_count', 0)}")
        if result['data'].get('errors'):
            print(f"Errors: {result['data']['errors']}")
        return True
    else:
        print(f"Error: {result.get('msg', 'Unknown error')}")
        return False


def verify_field_group_relation():
    """验证字段是否正确关联到字段组"""
    print("\n" + "=" * 60)
    print("验证字段是否正确关联到字段组")
    print("=" * 60)
    
    # 查询字段列表
    url = f"{BASE_URL}/field_spec/list"
    headers = {"token": TOKEN}
    params = {"page": 1, "page_size": 100, "field_name": "test_field_with_group"}
    
    response = requests.get(url, headers=headers, params=params)
    result = response.json()
    
    if result['code'] != 200:
        print(f"❌ 查询失败: {result.get('msg', 'Unknown error')}")
        return False
    
    data = result['data']
    if not data:
        print("❌ 未找到字段")
        return False
    
    # 处理不同的返回格式
    if isinstance(data, list):
        if len(data) == 0:
            print("❌ 未找到字段")
            return False
        field = data[0]
    elif isinstance(data, dict) and 'data' in data:
        if not data['data']:
            print("❌ 未找到字段")
            return False
        field = data['data'][0]
    else:
        print("❌ 返回数据格式异常")
        return False
    print(f"\n字段信息:")
    print(f"  ID: {field['id']}")
    print(f"  字段名: {field['field_name']}")
    print(f"  字段标签: {field['field_label']}")
    print(f"  关联字段组: {field.get('field_groups', [])}")
    
    field_groups = field.get('field_groups', [])
    if field_groups:
        group_names = [g['group_name'] for g in field_groups]
        if 'default' in group_names:
            print("\n✅ 字段正确关联到 'default' 字段组")
            return True
        else:
            print(f"\n❌ 字段未关联到 'default' 字段组，实际关联: {group_names}")
            return False
    else:
        print("\n❌ 字段未关联到任何字段组")
        return False


def cleanup_test_field():
    """清理测试字段"""
    print("\n" + "=" * 60)
    print("清理测试字段")
    print("=" * 60)
    
    # 查询字段
    url = f"{BASE_URL}/field_spec/list"
    headers = {"token": TOKEN}
    params = {"page": 1, "page_size": 100, "field_name": "test_field_with_group"}
    
    response = requests.get(url, headers=headers, params=params)
    result = response.json()
    
    if result['code'] == 200 and result['data']:
        # 处理不同的返回格式
        if isinstance(result['data'], list) and len(result['data']) > 0:
            field = result['data'][0]
        elif isinstance(result['data'], dict) and result['data'].get('data'):
            field = result['data']['data'][0]
        else:
            print("ℹ️ 未找到需要清理的测试字段")
            return
        field_id = field['id']
        
        # 删除字段
        delete_url = f"{BASE_URL}/field_spec/delete"
        delete_params = {"id": field_id}
        
        delete_response = requests.delete(delete_url, headers=headers, params=delete_params)
        delete_result = delete_response.json()
        
        if delete_result['code'] == 200:
            print(f"✅ 已删除测试字段 (ID: {field_id})")
        else:
            print(f"⚠️ 删除测试字段失败: {delete_result.get('msg', 'Unknown error')}")
    else:
        print("ℹ️ 未找到需要清理的测试字段")


def main():
    """主函数"""
    print("开始测试新增字段关联字段组功能...\n")
    
    try:
        # 1. 导入新增字段
        if not test_import_new_field():
            print("\n❌ 导入测试失败")
            return
        
        # 2. 验证字段组关联
        if verify_field_group_relation():
            print("\n✅ 测试通过！")
        else:
            print("\n❌ 验证失败")
    finally:
        # 3. 清理测试数据
        cleanup_test_field()


if __name__ == "__main__":
    main()
