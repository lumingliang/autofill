#!/usr/bin/env python3
"""
端到端测试 - 验证完整的规则管理流程

测试场景:
1. 创建规则
2. 保存 CSV 版本到 seekdb
3. 读取版本数据
4. 查询数据
5. 导出 CSV
6. 删除规则
"""

import asyncio
import tempfile
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


async def test_complete_workflow():
    """测试完整工作流程"""
    print("=" * 60)
    print("端到端测试 - 完整规则管理流程")
    print("=" * 60)

    from app.services.storage.seekdb_service import SeekDBService
    from app.services.rule_management.csv_import_seekdb import CsvImportSeekdbService

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        service = SeekDBService(db_path=db_path)

        # 场景 1: 全量导入 CSV
        print("\n📋 场景 1: 全量导入 CSV")
        print("-" * 40)

        csv_content = """product_name,category,price,stock
iPhone 15,Electronics,999,50
Samsung S24,Electronics,899,30
MacBook Pro,Computers,1999,20
Dell XPS,Computers,1499,15"""

        result = await CsvImportSeekdbService.full_import(
            collection_name="product_rule_v1",
            csv_content=csv_content,
            rule_id=100,
            version_no=1,
            tenant_id=1,
            app_name="ecommerce",
            rule_code="product_pricing"
        )

        print(f"✅ 导入成功")
        print(f"   - 新增数据: {result['added_count']} 条")
        print(f"   - 表头: {result['headers']}")
        print(f"   - 集合名称: {result['collection_name']}")

        # 场景 2: 读取数据
        print("\n📋 场景 2: 读取规则数据")
        print("-" * 40)

        data = await service.get_rule_data("product_rule_v1")
        print(f"✅ 读取成功")
        print(f"   - 表头: {data['headers']}")
        print(f"   - 数据行数: {len(data['data'])}")

        # 场景 3: 按字段查询
        print("\n📋 场景 3: 按类别查询")
        print("-" * 40)

        electronics = await service.query_by_field(
            "product_rule_v1",
            field="category",
            value="Electronics"
        )
        print(f"✅ 查询成功")
        print(f"   - Electronics 类别产品: {len(electronics)} 个")
        for item in electronics:
            print(f"     • {item['product_name']}: ${item['price']}")

        # 场景 4: 导出 CSV
        print("\n📋 场景 4: 导出 CSV")
        print("-" * 40)

        csv_output, headers, export_data = await service.export_to_csv("product_rule_v1")
        print(f"✅ 导出成功")
        print(f"   - CSV 长度: {len(csv_output)} 字符")
        print(f"   - 预览:")
        for line in csv_output.split('\n')[:3]:
            print(f"     {line}")

        # 场景 5: 增量导入（模拟表头变更）
        print("\n📋 场景 5: 增量导入（新增字段）")
        print("-" * 40)

        new_csv = """product_name,category,price,stock,discount
iPhone 15,Electronics,999,50,10
Samsung S24,Electronics,899,30,5
MacBook Pro,Computers,1999,20,15
Dell XPS,Computers,1499,15,10
iPad Pro,Electronics,799,25,8"""

        result = await CsvImportSeekdbService.full_import(
            collection_name="product_rule_v2",
            csv_content=new_csv,
            rule_id=100,
            version_no=2,
            tenant_id=1,
            app_name="ecommerce",
            rule_code="product_pricing"
        )

        print(f"✅ 新版本导入成功")
        print(f"   - 新增字段: discount")
        print(f"   - 总数据: {result['total_count']} 条")

        # 场景 6: 兼容性检测
        print("\n📋 场景 6: 表头兼容性检测")
        print("-" * 40)

        old_headers = ["name", "value", "status"]
        new_headers = ["name", "value", "status", "category"]

        compat = CsvImportSeekdbService.detect_header_compatibility(old_headers, new_headers)
        print(f"✅ 兼容性检测")
        print(f"   - 级别: {compat['level']}")
        print(f"   - 是否安全: {compat['is_safe']}")
        print(f"   - 新增字段: {compat['added_fields']}")

        # 场景 7: 删除集合
        print("\n📋 场景 7: 删除集合")
        print("-" * 40)

        deleted = service.delete_collection("product_rule_v1")
        print(f"✅ 删除 v1 集合: {deleted}")

        deleted = service.delete_collection("product_rule_v2")
        print(f"✅ 删除 v2 集合: {deleted}")

    print("\n" + "=" * 60)
    print("✅ 所有端到端测试通过！")
    print("=" * 60)


async def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("错误处理测试")
    print("=" * 60)

    from app.services.storage.seekdb_service import SeekDBService
    from app.services.rule_management.csv_import_seekdb import CsvImportSeekdbService

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        service = SeekDBService(db_path=db_path)

        # 测试 1: 空 CSV
        print("\n📋 测试 1: 空 CSV 处理")
        result = await CsvImportSeekdbService.full_import(
            collection_name="empty_test",
            csv_content="",
            rule_id=1,
            version_no=1,
            tenant_id=1,
            app_name="test",
            rule_code="test"
        )
        assert "error" in result, "应该返回错误"
        print("✅ 正确处理空 CSV")

        # 测试 2: 只有表头的 CSV
        print("\n📋 测试 2: 只有表头的 CSV")
        result = await CsvImportSeekdbService.full_import(
            collection_name="header_only",
            csv_content="name,value",
            rule_id=1,
            version_no=1,
            tenant_id=1,
            app_name="test",
            rule_code="test"
        )
        print(f"✅ 处理只有表头的 CSV，数据行数: {result['total_count']}")

        # 测试 3: 查询不存在的集合
        print("\n📋 测试 3: 查询不存在的集合")
        data = await service.get_rule_data("non_existent")
        assert data is None, "不存在的集合应返回 None"
        print("✅ 正确处理不存在的集合")

        # 测试 4: 删除不存在的集合
        print("\n📋 测试 4: 删除不存在的集合")
        result = service.delete_collection("non_existent")
        print(f"✅ 删除不存在的集合返回: {result}")

    print("\n" + "=" * 60)
    print("✅ 所有错误处理测试通过！")
    print("=" * 60)


async def main():
    """主函数"""
    try:
        await test_complete_workflow()
        await test_error_handling()

        print("\n" + "=" * 60)
        print("🎉 所有端到端测试完成！")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
