#!/usr/bin/env python3
"""
检查字段配置
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.services.autofill.field_group_query_service import field_group_query_service


async def check_field_config():
    """检查字段配置"""
    tenant_id = 1  # 测试租户A
    app_name = "test_app"
    group_names = ["事件类型"]
    field_names = ["一级事件类型"]

    print("=" * 80)
    print("检查字段配置")
    print("=" * 80)
    print(f"tenant_id: {tenant_id}")
    print(f"app_name: {app_name}")
    print(f"group_names: {group_names}")
    print(f"field_names: {field_names}")

    try:
        result = await field_group_query_service.fetch_field_groups(
            tenant_id=tenant_id,
            app_name=app_name,
            group_names=group_names,
            field_names=field_names
        )

        print("\n" + "=" * 80)
        print("查询结果:")
        print("=" * 80)

        print(f"\n字段组数量: {len(result.get('field_groups', []))}")
        for fg in result.get('field_groups', []):
            print(f"\n  字段组: {fg.get('group_name')}")
            print(f"    字段数量: {len(fg.get('field_specs', []))}")
            for f in fg.get('field_specs', []):
                print(f"    - {f.get('field_name')} ({f.get('field_label')}) - {f.get('field_type')}")
                print(f"      options: {f.get('options')}")

        schema = result.get('unified_function_schema')
        if schema:
            print("\n" + "=" * 80)
            print("FC Schema:")
            print("=" * 80)
            import json
            print(json.dumps(schema, ensure_ascii=False, indent=2))
        else:
            print("\n✗ unified_function_schema 为空")

    except Exception as e:
        print(f"\n✗ 异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_field_config())
