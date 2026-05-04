#!/usr/bin/env python3
"""
修复历史数据的继承问题
- 字段组：从关联的页面继承 tenant_id 和 app_name
- 字段：从关联的字段组继承 tenant_id 和 app_name
- 字段组-字段关联：从字段组继承 tenant_id 和 app_name
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from tortoise import Tortoise
from app.settings.config import settings
from app.models.autofill import AppManagement, FillPage, FieldGroupConfig, FieldSpec, FieldGroupFieldSpec

async def init_db():
    """初始化数据库连接"""
    db_url = f"mysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models.autofill', 'app.models.base']}
    )

async def fix_field_group_inheritance():
    """修复字段组的继承数据"""
    print("=" * 60)
    print("1. 修复字段组继承数据")
    print("=" * 60)

    # 获取 test_app 的信息
    app = await AppManagement.filter(app_name="test_app").first()
    if not app:
        print("  错误: 未找到 test_app 应用")
        return

    print(f"  应用信息: ID={app.id}, app_name={app.app_name}, tenant_id={app.tenant_id}")

    # 获取所有字段组
    groups = await FieldGroupConfig.all()
    fixed_count = 0

    for group in groups:
        # 获取关联的页面
        page = await FillPage.filter(id=group.page_id).first()
        if not page:
            print(f"  ⚠️  字段组 ID={group.id} 未找到关联页面 (page_id={group.page_id})")
            continue

        # 检查是否需要修复
        needs_fix = False
        if group.tenant_id == 0 or group.tenant_id != page.tenant_id:
            needs_fix = True
        if not group.app_name or group.app_name != page.app_name:
            needs_fix = True

        if needs_fix:
            old_tenant_id = group.tenant_id
            old_app_name = group.app_name

            # 从页面继承
            group.tenant_id = page.tenant_id
            group.app_name = page.app_name
            await group.save()

            print(f"  ✓ 修复字段组 ID={group.id} ({group.group_name})")
            print(f"    tenant_id: {old_tenant_id} -> {group.tenant_id}")
            print(f"    app_name: '{old_app_name}' -> '{group.app_name}'")
            fixed_count += 1
        else:
            print(f"  ✓ 字段组 ID={group.id} ({group.group_name}) 数据正确，无需修复")

    print(f"\n  共修复 {fixed_count} 个字段组")

async def fix_field_spec_inheritance():
    """修复字段的继承数据"""
    print("\n" + "=" * 60)
    print("2. 修复字段继承数据")
    print("=" * 60)

    # 获取所有字段
    fields_list = await FieldSpec.all()
    fixed_count = 0

    for field in fields_list:
        # 获取字段关联的字段组
        relations = await FieldGroupFieldSpec.filter(field_spec_id=field.id).all()

        if not relations:
            print(f"  ⚠️  字段 ID={field.id} ({field.field_name}) 未关联任何字段组")
            continue

        # 获取第一个关联的字段组
        relation = relations[0]
        group = await FieldGroupConfig.filter(id=relation.field_group_id).first()

        if not group:
            print(f"  ⚠️  字段 ID={field.id} 关联的字段组不存在 (group_id={relation.field_group_id})")
            continue

        # 检查是否需要修复
        needs_fix = False
        if field.tenant_id == 0 or field.tenant_id != group.tenant_id:
            needs_fix = True
        if not field.app_name or field.app_name != group.app_name:
            needs_fix = True

        if needs_fix:
            old_tenant_id = field.tenant_id
            old_app_name = field.app_name

            # 从字段组继承
            field.tenant_id = group.tenant_id
            field.app_name = group.app_name
            await field.save()

            print(f"  ✓ 修复字段 ID={field.id} ({field.field_name})")
            print(f"    tenant_id: {old_tenant_id} -> {field.tenant_id}")
            print(f"    app_name: '{old_app_name}' -> '{field.app_name}'")
            fixed_count += 1
        else:
            print(f"  ✓ 字段 ID={field.id} ({field.field_name}) 数据正确，无需修复")

    print(f"\n  共修复 {fixed_count} 个字段")

async def fix_field_group_field_spec_inheritance():
    """修复字段组-字段关联的继承数据"""
    print("\n" + "=" * 60)
    print("3. 修复字段组-字段关联继承数据")
    print("=" * 60)

    # 获取所有关联
    relations = await FieldGroupFieldSpec.all()
    fixed_count = 0

    for relation in relations:
        # 获取关联的字段组
        group = await FieldGroupConfig.filter(id=relation.field_group_id).first()

        if not group:
            print(f"  ⚠️  关联 ID={relation.id} 关联的字段组不存在 (group_id={relation.field_group_id})")
            continue

        # 检查是否需要修复
        needs_fix = False
        if relation.tenant_id == 0 or relation.tenant_id != group.tenant_id:
            needs_fix = True
        if not relation.app_name or relation.app_name != group.app_name:
            needs_fix = True

        if needs_fix:
            old_tenant_id = relation.tenant_id
            old_app_name = relation.app_name

            # 从字段组继承
            relation.tenant_id = group.tenant_id
            relation.app_name = group.app_name
            await relation.save()

            print(f"  ✓ 修复关联 ID={relation.id} (group_id={relation.field_group_id}, field_id={relation.field_spec_id})")
            print(f"    tenant_id: {old_tenant_id} -> {relation.tenant_id}")
            print(f"    app_name: '{old_app_name}' -> '{relation.app_name}'")
            fixed_count += 1

    print(f"\n  共修复 {fixed_count} 个关联")

async def verify_fix():
    """验证修复结果"""
    print("\n" + "=" * 60)
    print("4. 验证修复结果")
    print("=" * 60)

    # 检查字段组
    print("\n  字段组数据:")
    groups = await FieldGroupConfig.all()
    all_ok = True
    for group in groups:
        page = await FillPage.filter(id=group.page_id).first()
        if page:
            ok = (group.tenant_id == page.tenant_id and group.app_name == page.app_name)
            status = "✓" if ok else "✗"
            if not ok:
                all_ok = False
            print(f"    {status} ID={group.id}: tenant_id={group.tenant_id}, app_name='{group.app_name}'")

    # 检查字段
    print("\n  字段数据:")
    fields_list = await FieldSpec.all()
    for field in fields_list:
        relations = await FieldGroupFieldSpec.filter(field_spec_id=field.id).all()
        if relations:
            group = await FieldGroupConfig.filter(id=relations[0].field_group_id).first()
            if group:
                ok = (field.tenant_id == group.tenant_id and field.app_name == group.app_name)
                status = "✓" if ok else "✗"
                if not ok:
                    all_ok = False
                print(f"    {status} ID={field.id}: tenant_id={field.tenant_id}, app_name='{field.app_name}'")

    # 检查关联
    print("\n  字段组-字段关联数据:")
    relations = await FieldGroupFieldSpec.all()
    for relation in relations:
        group = await FieldGroupConfig.filter(id=relation.field_group_id).first()
        if group:
            ok = (relation.tenant_id == group.tenant_id and relation.app_name == group.app_name)
            status = "✓" if ok else "✗"
            if not ok:
                all_ok = False
            print(f"    {status} ID={relation.id}: tenant_id={relation.tenant_id}, app_name='{relation.app_name}'")

    print(f"\n  {'=' * 50}")
    print(f"  验证结果: {'全部通过 ✓' if all_ok else '存在错误 ✗'}")

async def main():
    await init_db()

    try:
        # 修复字段组继承
        await fix_field_group_inheritance()

        # 修复字段继承
        await fix_field_spec_inheritance()

        # 修复关联继承
        await fix_field_group_field_spec_inheritance()

        # 验证修复结果
        await verify_fix()

    finally:
        await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
