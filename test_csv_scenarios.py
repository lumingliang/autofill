#!/usr/bin/env python3
"""
构建多样的测试CSV场景，覆盖导入导出的各种功能
"""
import csv
import io
import os

# 测试数据目录
TEST_DATA_DIR = "/Users/lu/code/code/py/autofill/test_csv_data"


def ensure_dir():
    """确保测试数据目录存在"""
    if not os.path.exists(TEST_DATA_DIR):
        os.makedirs(TEST_DATA_DIR)


def save_csv(filename, content):
    """保存CSV文件"""
    filepath = os.path.join(TEST_DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    print(f"✅ 已保存: {filepath}")
    return filepath


def scenario_1_update_existing_field():
    """场景1: 更新已有字段（通过ID匹配）"""
    print("\n" + "=" * 60)
    print("场景1: 更新已有字段（通过ID匹配）")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    writer.writerow([
        "13",  # 使用已有字段ID
        "scene_category",
        "场景分类-场景1更新",
        "select",
        "场景1更新后的填写指引",
        "*场景1更新后的批注",
        "启用",
        "",
        "",
        ""
    ])
    
    content = output.getvalue()
    save_csv("scenario_1_update_existing_field.csv", content)
    print("\n场景说明: 通过字段ID更新已有字段的标签、指引和批注")
    return content


def scenario_2_create_new_field_with_group():
    """场景2: 新增字段并关联字段组"""
    print("\n" + "=" * 60)
    print("场景2: 新增字段并关联字段组")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    writer.writerow([
        "",  # 无ID，表示新增
        "new_field_scenario2",
        "场景2-新增字段",
        "text",
        "场景2新增字段的填写指引",
        "*场景2批注1\n*场景2批注2",
        "启用",
        "",  # 租户域名留空
        "default",  # 字段组名称
        ""
    ])
    
    content = output.getvalue()
    save_csv("scenario_2_create_new_field_with_group.csv", content)
    print("\n场景说明: 新增文本类型字段，自动关联到 default 字段组")
    return content


def scenario_3_delete_field():
    """场景3: 删除字段（状态设为已删除）"""
    print("\n" + "=" * 60)
    print("场景3: 删除字段（状态设为已删除）")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    writer.writerow([
        "",  # 无ID，通过名称匹配
        "field_to_delete_scenario3",
        "场景3-待删除字段",
        "text",
        "",
        "",
        "已删除",  # 标记删除
        "",
        "default",
        ""
    ])
    
    content = output.getvalue()
    save_csv("scenario_3_delete_field.csv", content)
    print("\n场景说明: 将状态设为'已删除'来删除字段（需要先创建测试字段）")
    return content


def scenario_4_update_select_option():
    """场景4: 更新下拉选项"""
    print("\n" + "=" * 60)
    print("场景4: 更新下拉选项")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    writer.writerow([
        "13",  # 字段ID
        "scene_category",
        "1",   # 选项值
        "预约充电故障-场景4更新",
        "场景4更新后的填写说明",
        "*场景4更新后的选项批注",
        "启用",
        "",
        "",
        ""
    ])
    
    content = output.getvalue()
    save_csv("scenario_4_update_select_option.csv", content)
    print("\n场景说明: 更新下拉字段的选项标签、说明和批注")
    return content


def scenario_5_add_new_option():
    """场景5: 新增下拉选项"""
    print("\n" + "=" * 60)
    print("场景5: 新增下拉选项")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    writer.writerow([
        "13",
        "scene_category",
        "100",  # 新选项值
        "场景5-新增选项",
        "场景5新增选项的填写说明",
        "*场景5选项批注",
        "启用",
        "",
        "",
        ""
    ])
    
    content = output.getvalue()
    save_csv("scenario_5_add_new_option.csv", content)
    print("\n场景说明: 为下拉字段添加新选项")
    return content


def scenario_6_delete_option():
    """场景6: 删除下拉选项"""
    print("\n" + "=" * 60)
    print("场景6: 删除下拉选项")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    writer.writerow([
        "13",
        "scene_category",
        "3",   # 要删除的选项值
        "车机系统卡顿",
        "",
        "",
        "已删除",  # 标记删除
        "",
        "",
        ""
    ])
    
    content = output.getvalue()
    save_csv("scenario_6_delete_option.csv", content)
    print("\n场景说明: 将选项状态设为'已删除'来删除选项")
    return content


def scenario_7_batch_operations():
    """场景7: 批量操作（同时包含增删改）"""
    print("\n" + "=" * 60)
    print("场景7: 批量操作（同时包含增删改）")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    # 更新已有字段
    writer.writerow([
        "13",
        "scene_category",
        "场景分类-场景7批量更新",
        "select",
        "场景7批量更新后的指引",
        "*场景7批量更新批注",
        "启用",
        "",
        "",
        ""
    ])
    
    # 新增字段1
    writer.writerow([
        "",
        "batch_new_field_1",
        "场景7-批量新增字段1",
        "text",
        "批量新增字段1的指引",
        "*批量新增字段1批注",
        "启用",
        "",
        "default",
        ""
    ])
    
    # 新增字段2
    writer.writerow([
        "",
        "batch_new_field_2",
        "场景7-批量新增字段2",
        "select",
        "批量新增字段2的指引",
        "",
        "启用",
        "",
        "default",
        ""
    ])
    
    content = output.getvalue()
    save_csv("scenario_7_batch_operations.csv", content)
    print("\n场景说明: 一个CSV中同时包含更新和新增操作")
    return content


def scenario_8_multi_corrections():
    """场景8: 多行批注测试"""
    print("\n" + "=" * 60)
    print("场景8: 多行批注测试")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    writer.writerow([
        "13",
        "scene_category",
        "场景分类-场景8多行批注",
        "select",
        "场景8多行批注测试",
        "*第一行批注\n*第二行批注\n*第三行批注\n*第四行批注",
        "启用",
        "",
        "",
        ""
    ])
    
    content = output.getvalue()
    save_csv("scenario_8_multi_corrections.csv", content)
    print("\n场景说明: 测试多行批注格式（每行以*开头）")
    return content


def scenario_9_cross_tenant():
    """场景9: 跨租户操作（超级管理员）"""
    print("\n" + "=" * 60)
    print("场景9: 跨租户操作（超级管理员）")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    writer.writerow([
        "",
        "cross_tenant_field",
        "跨租户测试字段",
        "text",
        "跨租户字段的填写指引",
        "*跨租户批注",
        "启用",
        "tenant-a",  # 指定租户域名
        "default",
        ""
    ])
    
    content = output.getvalue()
    save_csv("scenario_9_cross_tenant.csv", content)
    print("\n场景说明: 超级管理员通过指定租户域名在特定租户下创建字段")
    return content


def scenario_10_full_export_import():
    """场景10: 完整导出后修改再导入"""
    print("\n" + "=" * 60)
    print("场景10: 完整导出后修改再导入")
    print("=" * 60)
    
    print("\n此场景需要手动操作:")
    print("1. 在页面上选择多个字段导出")
    print("2. 修改导出的CSV文件")
    print("3. 重新导入修改后的CSV")
    print("\n建议测试步骤:")
    print("- 导出包含文本和下拉两种类型的字段")
    print("- 修改字段标签、填写指引、批注")
    print("- 添加新字段")
    print("- 标记某些字段为已删除")
    print("- 重新导入并验证结果")


def create_all_scenarios():
    """创建所有测试场景"""
    print("=" * 60)
    print("构建导入导出测试CSV场景")
    print("=" * 60)
    
    ensure_dir()
    
    scenario_1_update_existing_field()
    scenario_2_create_new_field_with_group()
    scenario_3_delete_field()
    scenario_4_update_select_option()
    scenario_5_add_new_option()
    scenario_6_delete_option()
    scenario_7_batch_operations()
    scenario_8_multi_corrections()
    scenario_9_cross_tenant()
    scenario_10_full_export_import()
    
    print("\n" + "=" * 60)
    print("所有测试场景CSV文件已生成")
    print(f"目录: {TEST_DATA_DIR}")
    print("=" * 60)
    
    # 列出所有生成的文件
    print("\n生成的文件列表:")
    for filename in sorted(os.listdir(TEST_DATA_DIR)):
        if filename.endswith('.csv'):
            filepath = os.path.join(TEST_DATA_DIR, filename)
            size = os.path.getsize(filepath)
            print(f"  - {filename} ({size} bytes)")


if __name__ == "__main__":
    create_all_scenarios()
