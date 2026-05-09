#!/usr/bin/env python3
"""
导出总结模板数据到CSV文件
"""

import csv
import requests
import sys

# API配置
API_BASE_URL = "http://localhost:9999"
# 从浏览器获取的token（需要替换为实际的token）
TOKEN = ""

def get_templates(token: str) -> list:
    """获取所有模板数据"""
    url = f"{API_BASE_URL}/api/v1/autofill/template/list"
    headers = {
        "token": token
    }
    params = {
        "page": 1,
        "page_size": 100
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 200:
            return data.get("data", [])
        else:
            print(f"获取数据失败: {data.get('msg')}")
            return []
    except Exception as e:
        print(f"请求失败: {e}")
        return []

def export_to_csv(templates: list, output_path: str):
    """导出模板数据到CSV"""
    if not templates:
        print("没有数据可导出")
        return
    
    # 定义CSV列
    fieldnames = [
        "id",
        "name",
        "app_name",
        "tenant_id",
        "class_name",
        "summary",
        "template_content",
        "created_at",
        "updated_at"
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for template in templates:
            row = {
                "id": template.get("id", ""),
                "name": template.get("name", ""),
                "app_name": template.get("app_name", ""),
                "tenant_id": template.get("tenant_id", ""),
                "class_name": template.get("class_name", ""),
                "summary": template.get("summary", ""),
                "template_content": template.get("template_content", ""),
                "created_at": template.get("created_at", ""),
                "updated_at": template.get("updated_at", "")
            }
            writer.writerow(row)
    
    print(f"✓ 成功导出 {len(templates)} 条模板数据到: {output_path}")

def main():
    # 获取token
    token = input("请输入浏览器中的token值: ").strip()
    
    if not token:
        print("错误: 需要提供token才能访问API")
        print("请从浏览器开发者工具中获取token值")
        sys.exit(1)
    
    print("=" * 60)
    print("导出总结模板数据")
    print("=" * 60)
    
    # 获取模板数据
    print("\n正在获取模板数据...")
    templates = get_templates(token)
    
    if not templates:
        print("获取数据失败，请检查token是否正确")
        sys.exit(1)
    
    print(f"获取到 {len(templates)} 条模板数据")
    
    # 导出到CSV
    output_path = "/Users/lu/code/code/py/autofill/test_csv_data/templates_export.csv"
    export_to_csv(templates, output_path)
    
    # 显示数据预览
    print("\n" + "=" * 60)
    print("数据预览（前3条）:")
    print("=" * 60)
    for i, template in enumerate(templates[:3], 1):
        print(f"\n[{i}] {template.get('name', 'N/A')}")
        print(f"    应用: {template.get('app_name', 'N/A')}")
        print(f"    分类: {template.get('class_name', 'N/A')}")
        print(f"    摘要: {template.get('summary', 'N/A')}")
        content = template.get('template_content', '')
        print(f"    模板内容: {content[:80]}..." if len(content) > 80 else f"    模板内容: {content}")

if __name__ == "__main__":
    main()
