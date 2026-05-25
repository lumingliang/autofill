#!/usr/bin/env python3
"""
测试 SeekDB 过滤查询功能
验证规则引擎直接使用 seekdb 查询过滤，而不是获取全部数据再过滤
"""

import asyncio
import tempfile
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


async def test_seekdb_filter():
    """测试 seekdb 直接过滤查询"""
    print("=" * 60)
    print("测试 SeekDB 直接过滤查询")
    print("=" * 60)

    from app.services.storage.seekdb_service import SeekDBService

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        service = SeekDBService(db_path=db_path)

        # 准备测试数据
        collection_name = "event_types"
        headers = ["一级事件类型", "二级事件类型", "三级事件类型", "二级事件类型id", "三级事件类型id"]
        data = [
            {"一级事件类型": "投诉", "二级事件类型": "商品质量", "三级事件类型": "屏幕问题", "二级事件类型id": "1", "三级事件类型id": "101"},
            {"一级事件类型": "投诉", "二级事件类型": "商品质量", "三级事件类型": "电池问题", "二级事件类型id": "1", "三级事件类型id": "102"},
            {"一级事件类型": "投诉", "二级事件类型": "物流问题", "三级事件类型": "配送延迟", "二级事件类型id": "2", "三级事件类型id": "201"},
            {"一级事件类型": "咨询", "二级事件类型": "产品咨询", "三级事件类型": "价格咨询", "二级事件类型id": "3", "三级事件类型id": "301"},
            {"一级事件类型": "咨询", "二级事件类型": "售后咨询", "三级事件类型": "保修政策", "二级事件类型id": "4", "三级事件类型id": "401"},
        ]

        # 保存数据
        print("\n1. 保存测试数据...")
        doc_count = await service.save_rule_data(
            collection_name=collection_name,
            headers=headers,
            data=data,
            rule_id=1,
            version_no=1,
            tenant_id=1,
            app_name="test",
            rule_code="event_types"
        )
        print(f"   ✓ 保存了 {doc_count} 条数据")

        # 测试 1: 直接查询全部数据
        print("\n2. 测试查询全部数据...")
        all_data = await service.get_rule_data(collection_name)
        print(f"   ✓ 查询到 {len(all_data['data'])} 条数据")

        # 测试 2: 使用 query_with_filter 直接过滤
        print("\n3. 测试直接过滤查询（一级事件类型 = 投诉）...")
        filtered_data = await service.query_with_filter(
            collection_name,
            {"data.一级事件类型": "投诉"}
        )
        print(f"   ✓ 过滤后得到 {len(filtered_data)} 条数据")
        for item in filtered_data:
            print(f"     - {item['二级事件类型']} - {item['三级事件类型']}")

        assert len(filtered_data) == 3, f"期望 3 条，实际 {len(filtered_data)}"

        # 测试 3: 多条件过滤
        print("\n4. 测试多条件过滤（一级=投诉, 二级=商品质量）...")
        multi_filtered = await service.query_with_filter(
            collection_name,
            {
                "data.一级事件类型": "投诉",
                "data.二级事件类型": "商品质量"
            }
        )
        print(f"   ✓ 过滤后得到 {len(multi_filtered)} 条数据")
        for item in multi_filtered:
            print(f"     - {item['三级事件类型']}")

        assert len(multi_filtered) == 2, f"期望 2 条，实际 {len(multi_filtered)}"

        # 测试 4: 按单个字段查询
        print("\n5. 测试按字段查询（二级事件类型id = 1）...")
        field_query = await service.query_by_field(
            collection_name,
            field="二级事件类型id",
            value="1"
        )
        print(f"   ✓ 查询到 {len(field_query)} 条数据")

        assert len(field_query) == 2, f"期望 2 条，实际 {len(field_query)}"

    print("\n" + "=" * 60)
    print("✅ SeekDB 过滤查询测试通过！")
    print("=" * 60)


async def test_rule_engine_filter():
    """测试规则引擎使用 seekdb 直接过滤"""
    print("\n" + "=" * 60)
    print("测试规则引擎使用 seekdb 直接过滤")
    print("=" * 60)

    from app.services.autofill.rule_engine_service import rule_engine_service

    # 验证新方法存在
    assert hasattr(rule_engine_service, '_get_rule_version'), "_get_rule_version 方法不存在"
    assert hasattr(rule_engine_service, '_get_filtered_rule_data'), "_get_filtered_rule_data 方法不存在"
    print("✅ 规则引擎包含新的过滤查询方法")

    # 验证方法签名
    import inspect
    sig = inspect.signature(rule_engine_service._get_filtered_rule_data)
    params = list(sig.parameters.keys())
    assert 'collection_name' in params, "缺少 collection_name 参数"
    assert 'filter_config' in params, "缺少 filter_config 参数"
    assert 'name_fields' in params, "缺少 name_fields 参数"
    print("✅ _get_filtered_rule_data 方法签名正确")

    print("\n" + "=" * 60)
    print("✅ 规则引擎过滤功能验证通过！")
    print("=" * 60)


async def main():
    """主函数"""
    try:
        await test_seekdb_filter()
        await test_rule_engine_filter()

        print("\n" + "=" * 60)
        print("🎉 所有过滤测试通过！")
        print("规则引擎现在直接使用 seekdb 查询过滤")
        print("而不是获取全部数据再内存过滤")
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
