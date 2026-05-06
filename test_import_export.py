#!/usr/bin/env python3
"""
测试字段导入导出功能
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
        print("\n--- 选项详情CSV ---")
        print(result["data"]["options_csv"])
        return result["data"]["options_csv"]
    else:
        print(f"❌ 导出失败: {result.get('msg', '未知错误')}")
        return None

def test_import(csv_content):
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
        "file": ("test_import.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    }
    
    response = requests.post(url, headers=headers, files=files)
    result = response.json()
    
    if result["code"] == 200:
        print(f"✅ 导入成功: {result['data']['success_count']} 条记录")
        if result["data"].get("errors"):
            print(f"⚠️  错误: {result['data']['errors']}")
        return True
    else:
        print(f"❌ 导入失败: {result.get('msg', '未知错误')}")
        return False

def create_test_csv():
    """创建测试CSV文件 - 测试多行人工标注格式"""
    print("\n" + "=" * 60)
    print("创建测试CSV文件")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(["字段ID", "字段名", "选项值", "选项标签", "填写说明", "corrections"])
    
    # 写入测试数据 - 多行人工标注，每行以 * 开头
    writer.writerow([
        "13",
        "scene_category",
        "1",
        "预约充电故障",
        "用户反馈预约充电功能异常",
        "*这是第一个批注\n*这是第二个批注\n*这是第三个批注"
    ])
    
    # 单一批注
    writer.writerow([
        "13",
        "scene_category",
        "2",
        "动力电池故障",
        "用户反馈动力电池异常报警",
        "*这是单一批注"
    ])
    
    # 空批注
    writer.writerow([
        "13",
        "scene_category",
        "3",
        "车机系统卡顿",
        "用户反馈车机系统卡顿",
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
    
    options_csv = result["data"]["options_csv"]
    print("--- 导出的CSV内容 ---")
    print(options_csv)
    
    # 验证格式
    lines = options_csv.strip().split("\n")
    header = lines[0]
    print(f"\n--- 验证表头 ---")
    print(f"表头: {header}")
    
    # 找到 corrections 列
    corrections_col_idx = None
    for idx, col in enumerate(header.split(",")):
        if col.strip() == "corrections":
            corrections_col_idx = idx
            break
    
    if corrections_col_idx is None:
        print("❌ 未找到 corrections 列")
        return False
    
    print(f"✅ 找到 corrections 列，索引: {corrections_col_idx}")
    
    # 验证数据行
    print(f"\n--- 验证数据行 ---")
    
    # 使用csv模块正确解析
    reader = csv.reader(io.StringIO(options_csv))
    next(reader)  # 跳过表头
    
    for i, row in enumerate(reader, 1):
        if len(row) > corrections_col_idx:
            corrections_value = row[corrections_col_idx]
            print(f"行 {i}: corrections = '{corrections_value[:50]}...' " if len(corrections_value) > 50 else f"行 {i}: corrections = '{corrections_value}'")
            
            if not corrections_value:
                print(f"  ℹ️  空值，跳过")
                continue
            
            # 验证多行格式
            if "*" in corrections_value:
                lines_in_cell = corrections_value.split("\n")
                all_start_with_star = True
                for j, cell_line in enumerate(lines_in_cell, 1):
                    cell_line = cell_line.strip()
                    if cell_line and not cell_line.startswith("*"):
                        print(f"  ❌ 第 {j} 行没有以 * 开头: '{cell_line}'")
                        all_start_with_star = False
                        return False
                if all_start_with_star:
                    print(f"  ✅ 多行格式正确，共 {len(lines_in_cell)} 行")
    
    print("\n✅ 导出格式验证通过")
    return True

def main():
    """主函数"""
    print("开始测试导入导出功能...\n")
    
    # 1. 先导出查看当前状态
    print("\n" + "=" * 60)
    print("步骤1: 查看当前导出状态")
    print("=" * 60)
    original_csv = test_export()
    
    if not original_csv:
        print("❌ 导出失败，终止测试")
        return
    
    # 2. 创建测试CSV
    print("\n" + "=" * 60)
    print("步骤2: 创建测试CSV")
    print("=" * 60)
    test_csv = create_test_csv()
    
    # 3. 导入测试数据
    print("\n" + "=" * 60)
    print("步骤3: 导入测试数据")
    print("=" * 60)
    if not test_import(test_csv):
        print("❌ 导入失败，终止测试")
        return
    
    # 4. 再次导出验证
    print("\n" + "=" * 60)
    print("步骤4: 再次导出验证")
    print("=" * 60)
    new_csv = test_export()
    
    if not new_csv:
        print("❌ 导出失败")
        return
    
    # 5. 验证导出格式
    print("\n" + "=" * 60)
    print("步骤5: 验证导出格式")
    print("=" * 60)
    if verify_export_format():
        print("\n✅ 所有测试通过！")
    else:
        print("\n❌ 格式验证失败")

if __name__ == "__main__":
    main()
