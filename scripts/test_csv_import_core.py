#!/usr/bin/env python3
"""
CSV增量导入核心功能测试脚本

测试覆盖：
1. 首次导入（全量导入）
2. 增量导入（新增/更新）
3. 联合主键
4. 选择性字段同步
5. 表头兼容（多字段/少字段）
6. 行级过滤（主键为空跳过）
7. 重复主键校验
"""

import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.services.rule_management.csv_import_core import (
    CsvImportCore,
    ImportConfig,
    execute_csv_import
)


def test_parse_csv():
    """测试CSV解析"""
    print("\n" + "="*60)
    print("测试1: CSV解析")
    print("="*60)

    csv_content = "id,name,age\n1,张三,20\n2,李四,25\n3,王五,30"
    headers, data = CsvImportCore.parse_csv(csv_content)

    print(f"表头: {headers}")
    print(f"数据行数: {len(data)}")
    print(f"第一行: {data[0]}")

    assert headers == ["id", "name", "age"]
    assert len(data) == 3
    assert data[0]["id"] == "1"
    print("✅ CSV解析测试通过")


def test_build_primary_key():
    """测试主键构建"""
    print("\n" + "="*60)
    print("测试2: 主键构建")
    print("="*60)

    # 单字段主键
    row1 = {"id": "1", "name": "张三"}
    key1 = CsvImportCore.build_primary_key(row1, ["id"])
    print(f"单字段主键: {key1}")
    assert key1 == "1"

    # 联合主键
    row2 = {"level1": "A", "level2": "B", "level3": "C"}
    key2 = CsvImportCore.build_primary_key(row2, ["level1", "level2", "level3"])
    print(f"联合主键: {key2}")
    assert key2 == "A|B|C"

    # 全部主键为空（应返回None，表示跳过）
    row3 = {"id": "", "name": "张三"}
    key3 = CsvImportCore.build_primary_key(row3, ["id"])
    print(f"主键为空: {key3}")
    assert key3 is None

    # 部分主键为空（不应跳过）
    row4 = {"level1": "A", "level2": "", "level3": "C"}
    key4 = CsvImportCore.build_primary_key(row4, ["level1", "level2", "level3"])
    print(f"部分主键为空: {key4}")
    assert key4 == "A||C"

    print("✅ 主键构建测试通过")


def test_first_import():
    """测试首次导入（全量导入）"""
    print("\n" + "="*60)
    print("测试3: 首次导入（全量导入）")
    print("="*60)

    csv_content = "id,name,age\n1,张三,20\n2,李四,25\n3,王五,30"

    merged_data, stats = execute_csv_import(
        csv_content=csv_content,
        existing_data=[],
        existing_headers=[],
        primary_keys=["id"],
        sync_fields=["name", "age"],
        is_first_import=True
    )

    print(f"新增: {stats.added_count}")
    print(f"更新: {stats.updated_count}")
    print(f"跳过: {stats.skipped_count}")
    print(f"失败: {stats.failed_count}")
    print(f"总行数: {stats.total_count}")

    assert stats.added_count == 3
    assert stats.updated_count == 0
    assert stats.total_count == 3
    assert len(merged_data) == 3

    print("✅ 首次导入测试通过")


def test_incremental_import():
    """测试增量导入（新增+更新）"""
    print("\n" + "="*60)
    print("测试4: 增量导入（新增+更新）")
    print("="*60)

    # 现有数据
    existing_data = [
        {"id": "1", "name": "张三", "age": "18"},
        {"id": "2", "name": "李四", "age": "25"}
    ]
    existing_headers = ["id", "name", "age"]

    # 新CSV数据：id=1更新name和age，id=3是新增
    csv_content = "id,name,age\n1,张三丰,28\n3,王五,30"

    merged_data, stats = execute_csv_import(
        csv_content=csv_content,
        existing_data=existing_data,
        existing_headers=existing_headers,
        primary_keys=["id"],
        sync_fields=["name", "age"],
        is_first_import=False
    )

    print(f"新增: {stats.added_count}")
    print(f"更新: {stats.updated_count}")
    print(f"跳过: {stats.skipped_count}")
    print(f"总行数: {stats.total_count}")

    # 验证统计
    assert stats.added_count == 1  # id=3是新增
    assert stats.updated_count == 1  # id=1是更新
    assert stats.total_count == 3  # 原有2条 + 新增1条

    # 验证数据
    id1_row = next(r for r in merged_data if r["id"] == "1")
    id2_row = next(r for r in merged_data if r["id"] == "2")
    id3_row = next(r for r in merged_data if r["id"] == "3")

    assert id1_row["name"] == "张三丰"  # 已更新
    assert id1_row["age"] == "28"  # 已更新
    assert id2_row["name"] == "李四"  # 未变化
    assert id2_row["age"] == "25"  # 未变化
    assert id3_row["name"] == "王五"  # 新增

    print("✅ 增量导入测试通过")


def test_selective_sync():
    """测试选择性字段同步"""
    print("\n" + "="*60)
    print("测试5: 选择性字段同步")
    print("="*60)

    existing_data = [
        {"id": "1", "name": "张三", "age": "18", "address": "北京"}
    ]
    existing_headers = ["id", "name", "age", "address"]

    # 只同步name字段，不同步age
    csv_content = "id,name,age\n1,张三丰,28"

    merged_data, stats = execute_csv_import(
        csv_content=csv_content,
        existing_data=existing_data,
        existing_headers=existing_headers,
        primary_keys=["id"],
        sync_fields=["name"],  # 只同步name
        is_first_import=False
    )

    id1_row = next(r for r in merged_data if r["id"] == "1")

    print(f"name: {id1_row['name']} (应更新为'张三丰')")
    print(f"age: {id1_row['age']} (应保持'18')")
    print(f"address: {id1_row['address']} (应保持'北京')")

    assert id1_row["name"] == "张三丰"  # 已更新
    assert id1_row["age"] == "18"  # 未更新（不在sync_fields中）
    assert id1_row["address"] == "北京"  # 未更新

    print("✅ 选择性字段同步测试通过")


def test_header_compatibility():
    """测试表头兼容性"""
    print("\n" + "="*60)
    print("测试6: 表头兼容性（多字段/少字段）")
    print("="*60)

    # 现有数据
    existing_data = [
        {"id": "1", "name": "张三", "age": "18"}
    ]
    existing_headers = ["id", "name", "age"]

    # 新CSV有额外字段email，缺少字段age
    csv_content = "id,name,email\n1,张三丰,zhangsan@example.com\n2,李四,lisi@example.com"

    merged_data, stats = execute_csv_import(
        csv_content=csv_content,
        existing_data=existing_data,
        existing_headers=existing_headers,
        primary_keys=["id"],
        sync_fields=["name", "email"],
        is_first_import=False
    )

    print(f"新增字段: email")
    print(f"总行数: {stats.total_count}")

    id1_row = next(r for r in merged_data if r["id"] == "1")
    id2_row = next(r for r in merged_data if r["id"] == "2")

    # id=1：原有字段保留，新增email字段
    assert "age" in id1_row  # 原有字段保留
    assert "email" in id1_row  # 新字段添加
    assert id1_row["email"] == "zhangsan@example.com"

    # id=2：新增行，所有字段都有
    assert id2_row["name"] == "李四"
    assert id2_row["email"] == "lisi@example.com"

    print("✅ 表头兼容性测试通过")


def test_skip_empty_primary_key():
    """测试跳过主键为空的行"""
    print("\n" + "="*60)
    print("测试7: 行级过滤（主键为空跳过）")
    print("="*60)

    csv_content = "id,name,age\n1,张三,20\n,李四,25\n3,王五,30"

    merged_data, stats = execute_csv_import(
        csv_content=csv_content,
        existing_data=[],
        existing_headers=[],
        primary_keys=["id"],
        sync_fields=["name", "age"],
        is_first_import=True
    )

    print(f"新增: {stats.added_count}")
    print(f"跳过: {stats.skipped_count}")
    print(f"总行数: {stats.total_count}")

    assert stats.added_count == 2  # id=1和id=3
    assert stats.skipped_count == 1  # id为空的行被跳过
    assert stats.total_count == 2

    print("✅ 行级过滤测试通过")


def test_composite_primary_key():
    """测试联合主键"""
    print("\n" + "="*60)
    print("测试8: 联合主键")
    print("="*60)

    existing_data = [
        {"level1": "A", "level2": "B", "value": "100"},
        {"level1": "A", "level2": "C", "value": "200"}
    ]
    existing_headers = ["level1", "level2", "value"]

    # 更新(A,B)，新增(A,D)
    csv_content = "level1,level2,value\nA,B,150\nA,D,300"

    merged_data, stats = execute_csv_import(
        csv_content=csv_content,
        existing_data=existing_data,
        existing_headers=existing_headers,
        primary_keys=["level1", "level2"],  # 联合主键
        sync_fields=["value"],
        is_first_import=False
    )

    print(f"新增: {stats.added_count}")
    print(f"更新: {stats.updated_count}")

    assert stats.added_count == 1  # (A,D)是新增
    assert stats.updated_count == 1  # (A,B)是更新

    ab_row = next(r for r in merged_data if r["level1"] == "A" and r["level2"] == "B")
    ad_row = next(r for r in merged_data if r["level1"] == "A" and r["level2"] == "D")

    assert ab_row["value"] == "150"  # 已更新
    assert ad_row["value"] == "300"  # 新增

    print("✅ 联合主键测试通过")


def test_validate_duplicate_keys():
    """测试重复主键校验"""
    print("\n" + "="*60)
    print("测试9: 重复主键校验")
    print("="*60)

    csv_content = "id,name,age\n1,张三,20\n1,李四,25\n2,王五,30"

    csv_headers, csv_data = CsvImportCore.parse_csv(csv_content)
    is_valid, errors, duplicate_keys = CsvImportCore.validate_data(csv_data, ["id"])

    print(f"校验结果: {'通过' if is_valid else '失败'}")
    print(f"错误信息: {errors}")
    print(f"重复主键: {duplicate_keys}")

    assert not is_valid
    assert len(duplicate_keys) == 1
    assert duplicate_keys[0]["key"] == "1"
    assert duplicate_keys[0]["count"] == 2

    print("✅ 重复主键校验测试通过")


def test_preserve_existing_data():
    """测试保留未匹配的旧数据"""
    print("\n" + "="*60)
    print("测试10: 保留未匹配的旧数据")
    print("="*60)

    existing_data = [
        {"id": "1", "name": "张三"},
        {"id": "2", "name": "李四"},  # 这条在CSV中不存在
        {"id": "3", "name": "王五"}
    ]
    existing_headers = ["id", "name"]

    # CSV中只有id=1和id=3
    csv_content = "id,name\n1,张三丰\n3,王五更新"

    merged_data, stats = execute_csv_import(
        csv_content=csv_content,
        existing_data=existing_data,
        existing_headers=existing_headers,
        primary_keys=["id"],
        sync_fields=["name"],
        is_first_import=False
    )

    print(f"总行数: {stats.total_count}")

    # 应该保留id=2
    assert stats.total_count == 3
    id2_row = next((r for r in merged_data if r["id"] == "2"), None)
    assert id2_row is not None
    assert id2_row["name"] == "李四"

    print("✅ 保留未匹配旧数据测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("CSV增量导入核心功能测试")
    print("="*60)

    tests = [
        test_parse_csv,
        test_build_primary_key,
        test_first_import,
        test_incremental_import,
        test_selective_sync,
        test_header_compatibility,
        test_skip_empty_primary_key,
        test_composite_primary_key,
        test_validate_duplicate_keys,
        test_preserve_existing_data,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} 失败: {e}")
            failed += 1

    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")

    if failed == 0:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️ {failed}个测试失败")
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
