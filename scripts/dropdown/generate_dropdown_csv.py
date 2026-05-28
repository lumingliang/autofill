#!/usr/bin/env python3
"""
生成下拉选项测试数据 CSV 文件
用于测试 CSV 导入功能
"""

import csv
import os

# 测试数据目录
DATA_DIR = "/Users/lu/code/code/py/autofill/scripts/data"

def generate_dropdown_csv():
    """
    生成下拉选项测试数据 CSV 文件
    包含一级、二级、三级菜单数据
    """
    
    # 确保目录存在
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 测试数据
    dropdown_data = [
        # 一级菜单
        {"id": "EVT001", "summary": "道路救援", "class_name": "事件类型", "parent_id": "", "level": 1, "status": "active"},
        {"id": "EVT002", "summary": "保养预约", "class_name": "事件类型", "parent_id": "", "level": 1, "status": "active"},
        {"id": "EVT003", "summary": "质量问题", "class_name": "事件类型", "parent_id": "", "level": 1, "status": "active"},
        
        # 二级菜单 - 道路救援
        {"id": "EVT001001", "summary": "拖车服务", "class_name": "事件类型", "parent_id": "EVT001", "level": 2, "status": "active"},
        {"id": "EVT001002", "summary": "现场维修", "class_name": "事件类型", "parent_id": "EVT001", "level": 2, "status": "active"},
        
        # 三级菜单 - 拖车服务
        {"id": "EVT001001001", "summary": "标准拖车", "class_name": "事件类型", "parent_id": "EVT001001", "level": 3, "status": "active"},
        {"id": "EVT001001002", "summary": "紧急拖车", "class_name": "事件类型", "parent_id": "EVT001001", "level": 3, "status": "active"},
        
        # 三级菜单 - 现场维修
        {"id": "EVT001002001", "summary": "电池更换", "class_name": "事件类型", "parent_id": "EVT001002", "level": 3, "status": "active"},
        {"id": "EVT001002002", "summary": "更换轮胎", "class_name": "事件类型", "parent_id": "EVT001002", "level": 3, "status": "active"},
        {"id": "EVT001002003", "summary": "送油服务", "class_name": "事件类型", "parent_id": "EVT001002", "level": 3, "status": "active"},
        
        # 二级菜单 - 保养预约
        {"id": "EVT002001", "summary": "常规保养", "class_name": "事件类型", "parent_id": "EVT002", "level": 2, "status": "active"},
        {"id": "EVT002002", "summary": "专项保养", "class_name": "事件类型", "parent_id": "EVT002", "level": 2, "status": "active"},
        
        # 三级菜单 - 常规保养
        {"id": "EVT002001001", "summary": "机油更换", "class_name": "事件类型", "parent_id": "EVT002001", "level": 3, "status": "active"},
        {"id": "EVT002001002", "summary": "滤芯更换", "class_name": "事件类型", "parent_id": "EVT002001", "level": 3, "status": "active"},
        
        # 新增数据 - 用于测试增量导入
        {"id": "EVT004", "summary": "投诉建议", "class_name": "事件类型", "parent_id": "", "level": 1, "status": "active"},
        {"id": "EVT004001", "summary": "服务投诉", "class_name": "事件类型", "parent_id": "EVT004", "level": 2, "status": "active"},
        {"id": "EVT004002", "summary": "产品投诉", "class_name": "事件类型", "parent_id": "EVT004", "level": 2, "status": "active"},
    ]
    
    # CSV 文件路径
    csv_file = os.path.join(DATA_DIR, "dropdown_options_test.csv")
    
    # 写入 CSV 文件
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "summary", "class_name", "parent_id", "level", "status"])
        writer.writeheader()
        writer.writerows(dropdown_data)
    
    print(f"✅ CSV 文件已生成: {csv_file}")
    print(f"   共 {len(dropdown_data)} 条数据")
    
    return csv_file


def generate_curl_commands():
    """
    生成 curl 请求命令
    用于测试 CURL 导入功能
    """
    
    api_key = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
    base_url = "http://localhost:9999"
    
    print("\n" + "=" * 60)
    print("         CURL 请求命令")
    print("=" * 60)
    
    # 1. 获取一级菜单
    print("\n📋 请求1: 获取一级菜单")
    print("-" * 40)
    curl_cmd_1 = f'''curl -X POST "{base_url}/api/autofill/dropdown/first_level" \\
  -H "Authorization: Bearer {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{"class_name": "事件类型"}}'
'''
    print(curl_cmd_1)
    
    # 2. 获取二三级菜单树形结构
    print("\n📋 请求2: 获取二三级菜单树形结构")
    print("-" * 40)
    curl_cmd_2 = f'''curl -X POST "{base_url}/api/autofill/dropdown/submenus_tree" \\
  -H "Authorization: Bearer {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{"first_level_value": "EVT001", "class_name": "事件类型"}}'
'''
    print(curl_cmd_2)
    
    return curl_cmd_1, curl_cmd_2


def main():
    print("=" * 60)
    print("         下拉选项测试数据生成")
    print("=" * 60)
    
    # 1. 生成 CSV 文件
    csv_file = generate_dropdown_csv()
    
    # 2. 生成 curl 命令
    curl_cmd_1, curl_cmd_2 = generate_curl_commands()
    
    print("\n" + "=" * 60)
    print("         测试说明")
    print("=" * 60)
    print(f"""
1. CSV 文件导入测试:
   - 文件路径: {csv_file}
   - 可在浏览器中上传此文件进行导入测试
   - 支持增量导入（覆盖/新增）

2. CURL 导入测试:
   - 使用上面的 curl 命令请求 API
   - 可将响应数据转换为 CSV 格式
   - 支持动态参数替换

3. 唯一标识字段:
   - 建议使用 "id" 字段作为唯一标识
   - 可同时选择 "id" + "class_name" 作为复合唯一标识
""")


if __name__ == "__main__":
    main()
