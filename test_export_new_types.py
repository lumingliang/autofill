#!/usr/bin/env python3
"""
测试导出功能 - 新的字段类型
"""
import requests

BASE_URL = "http://localhost:9999/api/v1/autofill"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJleHAiOjE3Nzg0MTE5NDMsImN1cnJlbnRfdGVuYW50X2lkIjowLCJ0ZW5hbnRfZG9tYWluIjoiIn0.7AaanOQA9d3akUWqwSTTDPkC9Pp3RKAzrgnQu3djpo0"


def test_export():
    """测试导出功能"""
    print("=" * 60)
    print("测试导出功能")
    print("=" * 60)
    
    # 先获取字段列表找到测试字段的ID
    url = f"{BASE_URL}/field_spec/list"
    headers = {"token": TOKEN}
    params = {"page": 1, "page_size": 100}
    
    response = requests.get(url, headers=headers, params=params)
    result = response.json()
    
    if result['code'] == 200:
        # 找到测试字段的ID
        target_ids = []
        items = result['data'].get('items', result['data']) if isinstance(result['data'], dict) else result['data']
        for item in items:
            if item['field_name'] in ['test_text_field', 'test_select_single', 'test_select_multi']:
                target_ids.append(item['id'])
                print(f"找到字段: {item['field_name']} (ID={item['id']}, 类型={item['field_type']})")
        
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
            else:
                print(f"导出失败: {result}")
        else:
            print("未找到测试字段")
    else:
        print(f"获取字段列表失败: {result}")
    
    return False


if __name__ == "__main__":
    test_export()
