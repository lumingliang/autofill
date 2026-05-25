#!/usr/bin/env python3
"""
基础功能测试脚本 - 验证 seekdb 核心功能
"""

import asyncio
import tempfile
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.storage.seekdb_service import SeekDBService


async def test_basic_operations():
    """测试基本操作"""
    print("=" * 50)
    print("开始测试 seekdb 基本功能")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        service = SeekDBService(db_path=db_path)

        # 1. 测试保存数据
        print("\n1. 测试保存规则数据...")
        collection_name = "test_rule_1_v1"
        headers = ["name", "value", "status"]
        data = [
            {"name": "item1", "value": "100", "status": "active"},
            {"name": "item2", "value": "200", "status": "inactive"},
            {"name": "item3", "value": "300", "status": "active"}
        ]

        doc_count = await service.save_rule_data(
            collection_name=collection_name,
            headers=headers,
            data=data,
            rule_id=1,
            version_no=1,
            tenant_id=1,
            app_name="test",
            rule_code="test_rule"
        )

        print(f"   ✓ 保存成功，文档数量: {doc_count}")
        assert doc_count == 3, f"期望 3 条数据，实际 {doc_count}"

        # 2. 测试读取数据
        print("\n2. 测试读取规则数据...")
        result = await service.get_rule_data(collection_name)
        print(f"   ✓ 读取成功")
        print(f"   - 表头: {result['headers']}")
        print(f"   - 数据行数: {len(result['data'])}")
        assert result["headers"] == headers
        assert len(result["data"]) == 3

        # 3. 测试按字段查询
        print("\n3. 测试按字段查询...")
        query_results = await service.query_by_field(
            collection_name=collection_name,
            field="status",
            value="active"
        )
        print(f"   ✓ 查询成功，找到 {len(query_results)} 条记录")
        assert len(query_results) == 2

        # 4. 测试导出 CSV
        print("\n4. 测试导出 CSV...")
        csv_content, export_headers, export_data = await service.export_to_csv(collection_name)
        print(f"   ✓ 导出成功")
        print(f"   - CSV 长度: {len(csv_content)} 字符")
        print(f"   - 表头: {export_headers}")
        assert len(csv_content) > 0
        assert export_headers == headers

        # 5. 测试获取文档数量
        print("\n5. 测试获取文档数量...")
        count = await service.get_doc_count(collection_name)
        print(f"   ✓ 文档数量: {count}")
        assert count == 3

        # 6. 测试删除集合
        print("\n6. 测试删除集合...")
        delete_result = service.delete_collection(collection_name)
        print(f"   ✓ 删除成功: {delete_result}")
        assert delete_result is True

    print("\n" + "=" * 50)
    print("所有测试通过！")
    print("=" * 50)


async def test_csv_import():
    """测试 CSV 导入功能"""
    print("\n" + "=" * 50)
    print("开始测试 CSV 导入功能")
    print("=" * 50)

    from app.services.rule_management.csv_import_seekdb import CsvImportSeekdbService

    # 1. 测试 CSV 解析
    print("\n1. 测试 CSV 解析...")
    csv_content = "name,value,status\nitem1,100,active\nitem2,200,inactive"
    headers, data = CsvImportSeekdbService.parse_csv(csv_content)
    print(f"   ✓ 解析成功")
    print(f"   - 表头: {headers}")
    print(f"   - 数据行数: {len(data)}")
    assert headers == ["name", "value", "status"]
    assert len(data) == 2

    # 2. 测试表头合并
    print("\n2. 测试表头合并...")
    existing = ["name", "value"]
    new = ["name", "status", "value"]
    merged, mapping = CsvImportSeekdbService.merge_headers(existing, new)
    print(f"   ✓ 合并成功: {merged}")
    assert merged == ["name", "value", "status"]

    # 3. 测试兼容性检测
    print("\n3. 测试兼容性检测...")
    result = CsvImportSeekdbService.detect_header_compatibility(
        ["name", "value"],
        ["name", "value", "status"]
    )
    print(f"   ✓ 兼容性级别: {result['level']}")
    print(f"   - 是否安全: {result['is_safe']}")
    assert result["level"] == "additive"
    assert result["is_safe"] is True

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        service = SeekDBService(db_path=db_path)

        # 4. 测试全量导入
        print("\n4. 测试全量导入...")
        result = await CsvImportSeekdbService.full_import(
            collection_name="test_import",
            csv_content=csv_content,
            rule_id=1,
            version_no=1,
            tenant_id=1,
            app_name="test",
            rule_code="test_rule"
        )
        print(f"   ✓ 导入成功")
        print(f"   - 新增: {result['added_count']}")
        print(f"   - 总计: {result['total_count']}")
        assert result["added_count"] == 2
        assert result["total_count"] == 2

    print("\n" + "=" * 50)
    print("CSV 导入测试通过！")
    print("=" * 50)


async def main():
    """主函数"""
    try:
        await test_basic_operations()
        await test_csv_import()
        print("\n✅ 所有测试通过！")
        return 0
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
