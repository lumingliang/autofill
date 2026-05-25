#!/usr/bin/env python3
"""
简化版功能测试 - 验证核心功能
"""

import asyncio
import tempfile
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


async def test_seekdb_service():
    """测试 SeekDBService"""
    print("=" * 50)
    print("测试 SeekDBService")
    print("=" * 50)

    from app.services.storage.seekdb_service import SeekDBService

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        service = SeekDBService(db_path=db_path)

        # 测试保存和读取
        print("\n1. 测试保存数据...")
        collection_name = "test_collection"
        headers = ["name", "value"]
        data = [
            {"name": "item1", "value": "100"},
            {"name": "item2", "value": "200"}
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

        print(f"   ✓ 保存了 {doc_count} 条数据")

        print("\n2. 测试读取数据...")
        result = await service.get_rule_data(collection_name)
        print(f"   ✓ 读取到 {len(result['data'])} 条数据")

        print("\n3. 测试导出 CSV...")
        csv_content, export_headers, export_data = await service.export_to_csv(collection_name)
        print(f"   ✓ 导出成功，CSV 长度: {len(csv_content)}")

        print("\n✅ SeekDBService 测试通过！")
        return True


async def test_csv_import():
    """测试 CSV 导入"""
    print("\n" + "=" * 50)
    print("测试 CSV 导入功能")
    print("=" * 50)

    from app.services.rule_management.csv_import_seekdb import CsvImportSeekdbService

    print("\n1. 测试 CSV 解析...")
    csv_content = "name,value,status\nitem1,100,active\nitem2,200,inactive"
    headers, data = CsvImportSeekdbService.parse_csv(csv_content)
    print(f"   ✓ 解析到 {len(data)} 行数据")

    print("\n2. 测试表头合并...")
    existing = ["name", "value"]
    new = ["name", "status", "value"]
    merged, mapping = CsvImportSeekdbService.merge_headers(existing, new)
    print(f"   ✓ 合并结果: {merged}")

    print("\n3. 测试兼容性检测...")
    result = CsvImportSeekdbService.detect_header_compatibility(
        ["name", "value"],
        ["name", "value", "status"]
    )
    print(f"   ✓ 兼容性: {result['level']}, 安全: {result['is_safe']}")

    print("\n✅ CSV 导入测试通过！")
    return True


async def test_rule_service():
    """测试 RuleService 集成"""
    print("\n" + "=" * 50)
    print("测试 RuleService 集成")
    print("=" * 50)

    from app.services.rule_management.rule_service import rule_service

    print("\n1. 测试生成规则编码...")
    code = rule_service.generate_rule_code("测试规则")
    print(f"   ✓ 生成的编码: {code}")

    print("\n2. 测试计算 MD5...")
    content = {"headers": ["name"], "data": [["test"]]}
    md5 = rule_service.calculate_md5(content)
    print(f"   ✓ MD5: {md5}")

    print("\n3. 测试生成集合名称...")
    collection_name = rule_service._generate_collection_name(1, 1)
    print(f"   ✓ 集合名称: {collection_name}")

    print("\n✅ RuleService 测试通过！")
    return True


async def main():
    """主函数"""
    try:
        await test_seekdb_service()
        await test_csv_import()
        await test_rule_service()

        print("\n" + "=" * 50)
        print("✅ 所有测试通过！")
        print("=" * 50)
        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
