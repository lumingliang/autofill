#!/usr/bin/env python3
"""
下拉类型字段导入导出测试场景
覆盖：新增字段、修改字段、删除字段、新增选项、修改选项、删除选项
"""
import csv
import io
import os

TEST_DATA_DIR = "/Users/lu/code/code/py/autofill/test_csv_data"


def ensure_dir():
    if not os.path.exists(TEST_DATA_DIR):
        os.makedirs(TEST_DATA_DIR)


def save_csv(filename, content):
    filepath = os.path.join(TEST_DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    print(f"✅ 已保存: {filepath}")
    return filepath


def scenario_1_create_new_select_field():
    """场景1: 新增下拉类型字段并关联字段组"""
    print("\n" + "=" * 60)
    print("场景1: 新增下拉类型字段")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 字段信息表头
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    writer.writerow([
        "",  # 无ID，新增
        "test_select_field_new",
        "测试下拉字段-新增",
        "select",
        "请选择适合的选项",
        "*下拉字段批注1\n*下拉字段批注2",
        "启用",
        "",
        "default",
        ""
    ])
    
    content = output.getvalue()
    save_csv("select_scenario_1_create_field.csv", content)
    print("说明: 新增下拉类型字段，关联到default字段组")
    return content


def scenario_2_add_options_to_field():
    """场景2: 为下拉字段添加选项"""
    print("\n" + "=" * 60)
    print("场景2: 为下拉字段添加选项")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 选项信息表头
    writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    # 添加3个选项
    writer.writerow(["", "test_select_field_new", "1", "选项A", "选项A的填写说明", "*选项A批注", "启用", "", "", ""])
    writer.writerow(["", "test_select_field_new", "2", "选项B", "选项B的填写说明", "*选项B批注", "启用", "", "", ""])
    writer.writerow(["", "test_select_field_new", "3", "选项C", "选项C的填写说明", "", "启用", "", "", ""])
    
    content = output.getvalue()
    save_csv("select_scenario_2_add_options.csv", content)
    print("说明: 为test_select_field_new字段添加3个选项")
    return content


def scenario_3_update_field_and_options():
    """场景3: 修改下拉字段和选项"""
    print("\n" + "=" * 60)
    print("场景3: 修改下拉字段和选项")
    print("=" * 60)
    
    # 修改字段信息
    output1 = io.StringIO()
    writer1 = csv.writer(output1)
    writer1.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    writer1.writerow([
        "",  # 通过字段名匹配
        "test_select_field_new",
        "测试下拉字段-已修改",
        "select",
        "修改后的填写指引",
        "*修改后的批注",
        "启用",
        "",
        "default",
        ""
    ])
    save_csv("select_scenario_3a_update_field.csv", output1.getvalue())
    
    # 修改选项信息
    output2 = io.StringIO()
    writer2 = csv.writer(output2)
    writer2.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    writer2.writerow(["", "test_select_field_new", "1", "选项A-已修改", "修改后的选项A说明", "*修改后的选项A批注", "启用", "", "", ""])
    writer2.writerow(["", "test_select_field_new", "2", "选项B-已修改", "修改后的选项B说明", "", "启用", "", "", ""])
    
    save_csv("select_scenario_3b_update_options.csv", output2.getvalue())
    print("说明: 修改字段标签、指引、批注；修改选项1和2的标签、说明、批注")
    return output1.getvalue(), output2.getvalue()


def scenario_4_delete_option():
    """场景4: 删除下拉选项"""
    print("\n" + "=" * 60)
    print("场景4: 删除下拉选项")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    # 删除选项3（状态设为已删除）
    writer.writerow(["", "test_select_field_new", "3", "选项C", "", "", "已删除", "", "", ""])
    
    content = output.getvalue()
    save_csv("select_scenario_4_delete_option.csv", content)
    print("说明: 删除选项3（通过状态设为'已删除'）")
    return content


def scenario_5_delete_select_field():
    """场景5: 删除下拉字段"""
    print("\n" + "=" * 60)
    print("场景5: 删除下拉字段")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    writer.writerow([
        "",
        "test_select_field_new",
        "",
        "",
        "",
        "",
        "已删除",  # 标记删除
        "",
        "",
        ""
    ])
    
    content = output.getvalue()
    save_csv("select_scenario_5_delete_field.csv", content)
    print("说明: 删除整个下拉字段（通过状态设为'已删除'）")
    return content


def scenario_6_complete_workflow():
    """场景6: 完整工作流程（字段+选项一起导入）"""
    print("\n" + "=" * 60)
    print("场景6: 完整工作流程（字段+选项一起导入）")
    print("=" * 60)
    
    # 字段CSV
    output1 = io.StringIO()
    writer1 = csv.writer(output1)
    writer1.writerow(['ID', '字段名', '字段标签', '字段类型', '填写指引', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    writer1.writerow([
        "",
        "complete_select_field",
        "完整流程测试字段",
        "select",
        "完整流程测试的填写指引",
        "*完整流程批注",
        "启用",
        "",
        "default",
        ""
    ])
    save_csv("select_scenario_6a_field.csv", output1.getvalue())
    
    # 选项CSV
    output2 = io.StringIO()
    writer2 = csv.writer(output2)
    writer2.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    writer2.writerow(["", "complete_select_field", "10", "选项十", "选项十的说明", "*选项十批注", "启用", "", "", ""])
    writer2.writerow(["", "complete_select_field", "20", "选项二十", "选项二十的说明", "", "启用", "", "", ""])
    writer2.writerow(["", "complete_select_field", "30", "选项三十", "选项三十的说明", "*选项三十批注1\n*选项三十批注2", "启用", "", "", ""])
    
    save_csv("select_scenario_6b_options.csv", output2.getvalue())
    print("说明: 先导入字段，再导入选项，测试完整流程")
    return output1.getvalue(), output2.getvalue()


def scenario_7_batch_operations():
    """场景7: 批量操作（同时增删改）"""
    print("\n" + "=" * 60)
    print("场景7: 批量操作（同时增删改）")
    print("=" * 60)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['字段ID', '字段名', '选项值', '选项标签', '填写说明', 'corrections', '状态', '租户域名', '字段组名称', '页面名称'])
    
    # 修改选项10
    writer.writerow(["", "complete_select_field", "10", "选项十-批量修改", "批量修改后的说明", "*批量修改批注", "启用", "", "", ""])
    
    # 新增选项40
    writer.writerow(["", "complete_select_field", "40", "选项四十", "选项四十的说明", "*选项四十批注", "启用", "", "", ""])
    
    # 删除选项20
    writer.writerow(["", "complete_select_field", "20", "选项二十", "", "", "已删除", "", "", ""])
    
    content = output.getvalue()
    save_csv("select_scenario_7_batch_options.csv", content)
    print("说明: 同时修改选项10、新增选项40、删除选项20")
    return content


def create_all_scenarios():
    print("=" * 60)
    print("下拉类型字段导入导出测试场景")
    print("=" * 60)
    
    ensure_dir()
    
    scenario_1_create_new_select_field()
    scenario_2_add_options_to_field()
    scenario_3_update_field_and_options()
    scenario_4_delete_option()
    scenario_5_delete_select_field()
    scenario_6_complete_workflow()
    scenario_7_batch_operations()
    
    print("\n" + "=" * 60)
    print("所有下拉类型测试场景CSV文件已生成")
    print(f"目录: {TEST_DATA_DIR}")
    print("=" * 60)
    
    print("\n生成的文件列表:")
    for filename in sorted(os.listdir(TEST_DATA_DIR)):
        if filename.startswith('select_') and filename.endswith('.csv'):
            filepath = os.path.join(TEST_DATA_DIR, filename)
            size = os.path.getsize(filepath)
            print(f"  - {filename} ({size} bytes)")


if __name__ == "__main__":
    create_all_scenarios()
