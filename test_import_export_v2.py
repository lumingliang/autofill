#!/usr/bin/env python3
"""
测试字段导入导出功能 V2 - 支持新增字段、删除字段、状态管理
"""
import csv
import io
import json
import requests

BASE_URL = "http://localhost:9999/api/v1/autofill"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJleHAiOjE3Nzg0MTE5NDMsImN1cnJlbnRfdGVuYW50X2lkIjowLCJ0ZW5hbnRfZG9tYWluIjoiIn0.7AaanOQA9d3akUWqwSTTDPkC9Pp3RKAzrgnQu3djpo0"

def test_export():
    """测试导出功能"""
    print("=" * 60)
    print("测试导出功能")
    print("=" * 60)
    
    url = f"{BASE_URL}/field_spec/export"
    headers = {
        "Content-Type": "application/json",
        "token": TOKEN
    }
    data = {"ids": [13]}  # 测试 scene_category 字段
    
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    
    if result["code"] == 200:
        print("✅ 导出成功")
        print("\n--- 基础字段信息CSV ---")
        print(result["data"]["base_csv"])
        print("\n--- 选项详情CSV ---")
        print(result["data"]["options_csv"])
        return result["data"]
    else:
        print(f"❌ 导出失败: {result.get('msg', '未知错误')}")
        return None

def test_import(csv_content, filename="test_import.csv"):
    """测试导入功能"""
    print("\n" + "=" * 60)
    print("测试导入功能")
    print("=" * 60)
    
    url = f"{BASE_URL}/field_spec/import"
    headers = {
        "token": TOKEN
    }
    
    # 创建文件上传
    files = {
        "file": (filename, io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    }
    
    response = requests.post(url, headers=headers, files=files)
    result = response.json()
    
    if result["code"] == 200:
        print(f"✅ 导入成功")
        print(f"   - 成功处理: {result['data']['success_count']} 条")
        print(f"   - 删除: {result['data'].get('delete_count', 0)} 条")
        if result["data"].get("errors"):
            print(f"   - 错误: {result['data']['errors']}")
        return True
    else:
        print(f"❌ 导入失败: {result.get('msg', '未知错误')}")
        return False

def create_test_base_csv():
    """创建测试基础字段CSV - 包含新增、更新、删除操作"""
    print("\n" + "=" * 60)
    print("创建测试基础字段CSV")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头 - 新格式
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    # 1. 更新已有字段（使用ID匹配）
    writer.writerow([
        "13",  # ID
        "scene_category",
        "场景分类-已更新",
        "select",
        "更新后的填写指引",
        "*更新后的批注",
        "启用",
        "",  # 租户域名
        "",  # 字段组名称
        ""   # 页面名称
    ])
    
    # 2. 新增字段（无ID，使用租户域名+字段组名称匹配）
    writer.writerow([
        "",  # 无ID，表示新增
        "new_test_field",
        "新增测试字段",
        "text",
        "这是新增字段的填写指引",
        "*新增字段批注1\n*新增字段批注2",
        "启用",
        "localhost",  # 租户域名
        "default",    # 字段组名称
        ""            # 页面名称
    ])
    
    # 3. 标记删除字段（状态为已删除）
    writer.writerow([
        "",  # 无ID，通过名称匹配
        "field_to_delete",
        "待删除字段",
        "text",
        "",
        "",
        "已删除",  # 标记删除
        "localhost",
        "default",
        ""
    ])
    
    csv_content = output.getvalue()
    print("✅ 测试CSV文件创建成功")
    print("\n--- CSV内容 ---")
    print(csv_content)
    
    return csv_content

def create_test_options_csv():
    """创建测试选项详情CSV - 包含新增、更新、删除选项"""
    print("\n" + "=" * 60)
    print("创建测试选项详情CSV")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头 - 新格式
    writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    # 1. 更新已有选项
    writer.writerow([
        "13",  # 字段ID
        "scene_category",
        "1",   # 选项值
        "预约充电故障-已更新",
        "更新后的填写说明",
        "*更新后的选项批注",
        "启用",
        "",
        "",
        ""
    ])
    
    # 2. 新增选项
    writer.writerow([
        "13",
        "scene_category",
        "99",  # 新选项值
        "新增选项",
        "新增选项的填写说明",
        "*新增选项批注",
        "启用",
        "",
        "",
        ""
    ])
    
    # 3. 删除选项（状态为已删除）
    writer.writerow([
        "13",
        "scene_category",
        "2",   # 要删除的选项值
        "动力电池故障",
        "",
        "",
        "已删除",  # 标记删除
        "",
        "",
        ""
    ])
    
    csv_content = output.getvalue()
    print("✅ 测试CSV文件创建成功")
    print("\n--- CSV内容 ---")
    print(csv_content)
    
    return csv_content

def verify_export_format():
    """验证导出格式是否正确"""
    print("\n" + "=" * 60)
    print("验证导出格式")
    print("=" * 60)
    
    url = f"{BASE_URL}/field_spec/export"
    headers = {
        "Content-Type": "application/json",
        "token": TOKEN
    }
    data = {"ids": [13]}
    
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    
    if result["code"] != 200:
        print(f"❌ 导出失败: {result.get('msg', '未知错误')}")
        return False
    
    base_csv = result["data"]["base_csv"]
    options_csv = result["data"]["options_csv"]
    
    print("--- 基础字段CSV内容 ---")
    print(base_csv)
    print("\n--- 选项详情CSV内容 ---")
    print(options_csv)
    
    # 验证基础字段CSV表头
    base_lines = base_csv.strip().split("\n")
    base_header = base_lines[0].replace('\r', '')
    expected_base_header = "ID,字段名,字段标签,字段类型,填写指引,corrections,状态,租户域名,字段组名称,页面名称"
    
    if base_header != expected_base_header:
        print(f"\n❌ 基础字段CSV表头不匹配")
        print(f"   期望: {repr(expected_base_header)}")
        print(f"   实际: {repr(base_header)}")
        return False
    
    print("\n✅ 基础字段CSV表头正确")
    
    # 验证选项详情CSV表头
    options_lines = options_csv.strip().split("\n")
    options_header = options_lines[0].replace('\r', '')
    expected_options_header = "字段ID,字段名,选项值,选项标签,填写说明,corrections,状态,租户域名,字段组名称,页面名称"
    
    if options_header != expected_options_header:
        print(f"\n❌ 选项详情CSV表头不匹配")
        print(f"   期望: {repr(expected_options_header)}")
        print(f"   实际: {repr(options_header)}")
        return False
    
    print("✅ 选项详情CSV表头正确")
    
    # 验证数据行包含状态字段
    if len(base_lines) > 1:
        first_data_row = base_lines[1].split(",")
        if len(first_data_row) >= 7:
            status = first_data_row[6]
            print(f"✅ 状态字段值: {status}")
    
    print("\n✅ 导出格式验证通过")
    return True

def main():
    """主函数"""
    print("开始测试导入导出功能 V2...\n")
    
    # 1. 先导出查看当前状态
    print("\n" + "=" * 60)
    print("步骤1: 查看当前导出状态")
    print("=" * 60)
    export_data = test_export()
    
    if not export_data:
        print("❌ 导出失败，终止测试")
        return
    
    # 2. 验证导出格式
    print("\n" + "=" * 60)
    print("步骤2: 验证导出格式")
    print("=" * 60)
    if not verify_export_format():
        print("❌ 格式验证失败")
        return
    
    # 3. 创建并导入基础字段CSV（测试更新和新增）
    print("\n" + "=" * 60)
    print("步骤3: 导入基础字段CSV（测试更新和新增）")
    print("=" * 60)
    base_csv = create_test_base_csv()
    if not test_import(base_csv, "base_import.csv"):
        print("❌ 基础字段导入失败")
        return
    
    # 4. 创建并导入选项详情CSV（测试选项更新、新增、删除）
    print("\n" + "=" * 60)
    print("步骤4: 导入选项详情CSV（测试选项更新、新增、删除）")
    print("=" * 60)
    options_csv = create_test_options_csv()
    if not test_import(options_csv, "options_import.csv"):
        print("❌ 选项详情导入失败")
        return
    
    # 5. 再次导出验证结果
    print("\n" + "=" * 60)
    print("步骤5: 再次导出验证结果")
    print("=" * 60)
    test_export()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
