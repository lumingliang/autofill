#!/usr/bin/env python3
"""
测试继承关系的脚本
创建页面、字段组、字段，并验证数据库中的继承关系
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

async def check_existing_data():
    """检查现有数据"""
    print("=" * 60)
    print("1. 检查现有应用数据")
    print("=" * 60)
    apps = await AppManagement.all()
    for app in apps:
        print(f"  应用ID: {app.id}, 应用名称: {app.app_name}, 租户ID: {app.tenant_id}")

    print("\n" + "=" * 60)
    print("2. 检查现有页面数据")
    print("=" * 60)
    pages = await FillPage.all()
    for page in pages:
        print(f"  页面ID: {page.id}, 页面名称: {page.page_name}, 应用名称: {page.app_name}, 租户ID: {page.tenant_id}")

    print("\n" + "=" * 60)
    print("3. 检查现有字段组数据")
    print("=" * 60)
    groups = await FieldGroupConfig.all()
    for group in groups:
        print(f"  字段组ID: {group.id}, 字段组名称: {group.group_name}, 页面ID: {group.page_id}, 应用名称: {group.app_name}, 租户ID: {group.tenant_id}")

    print("\n" + "=" * 60)
    print("4. 检查现有字段数据")
    print("=" * 60)
    fields = await FieldSpec.all()
    for field in fields:
        print(f"  字段ID: {field.id}, 字段名: {field.field_name}, 应用名称: {field.app_name}, 租户ID: {field.tenant_id}")

    return apps, pages, groups, fields

async def create_test_data():
    """创建测试数据"""
    print("\n" + "=" * 60)
    print("5. 创建测试数据")
    print("=" * 60)

    # 获取第一个应用
    app = await AppManagement.first()
    if not app:
        print("  错误: 没有可用的应用")
        return

    print(f"\n  使用应用: ID={app.id}, app_name={app.app_name}, tenant_id={app.tenant_id}")

    # 创建页面
    page = await FillPage.create(
        page_name="继承测试页面",
        page_code="inherit_test_page",
        app_id=app.id,
        app_name=app.app_name,  # 从应用继承
        tenant_id=app.tenant_id,  # 从应用继承
        description="用于测试继承关系的页面",
        is_active=True
    )
    print(f"\n  ✓ 创建页面成功: ID={page.id}, page_name={page.page_name}")
    print(f"    - app_name: {page.app_name} (从应用继承)")
    print(f"    - tenant_id: {page.tenant_id} (从应用继承)")

    # 创建字段组
    group = await FieldGroupConfig.create(
        group_name="继承测试字段组",
        group_code="inherit_test_group",
        page_id=page.id,
        app_name=page.app_name,  # 从页面继承
        tenant_id=page.tenant_id,  # 从页面继承
        prompt_template="测试Prompt模板",
        description="用于测试继承关系的字段组",
        is_active=True
    )
    print(f"\n  ✓ 创建字段组成功: ID={group.id}, group_name={group.group_name}")
    print(f"    - page_id: {group.page_id}")
    print(f"    - app_name: {group.app_name} (从页面继承)")
    print(f"    - tenant_id: {group.tenant_id} (从页面继承)")

    # 创建字段
    field = await FieldSpec.create(
        field_name="inherit_test_field",
        field_label="继承测试字段",
        field_type="text",
        app_name=group.app_name,  # 从字段组继承
        tenant_id=group.tenant_id,  # 从字段组继承
        fill_instruction="测试填写指引",
        is_active=True
    )
    print(f"\n  ✓ 创建字段成功: ID={field.id}, field_name={field.field_name}")
    print(f"    - app_name: {field.app_name} (从字段组继承)")
    print(f"    - tenant_id: {field.tenant_id} (从字段组继承)")

    # 创建字段组与字段的关联
    relation = await FieldGroupFieldSpec.create(
        field_group_id=group.id,
        field_spec_id=field.id,
        app_name=group.app_name,  # 从字段组继承
        tenant_id=group.tenant_id,  # 从字段组继承
        sort_order=1,
        is_active=True
    )
    print(f"\n  ✓ 创建字段关联成功: ID={relation.id}")
    print(f"    - field_group_id: {relation.field_group_id}")
    print(f"    - field_spec_id: {relation.field_spec_id}")
    print(f"    - app_name: {relation.app_name} (从字段组继承)")
    print(f"    - tenant_id: {relation.tenant_id} (从字段组继承)")

    return page, group, field, relation

async def verify_inheritance():
    """验证继承关系"""
    print("\n" + "=" * 60)
    print("6. 验证继承关系链")
    print("=" * 60)

    # 查询刚创建的页面
    page = await FillPage.filter(page_code="inherit_test_page").first()
    if not page:
        print("  错误: 未找到测试页面")
        return

    # 查询应用
    app = await AppManagement.filter(id=page.app_id).first()

    # 查询字段组
    group = await FieldGroupConfig.filter(group_code="inherit_test_group").first()

    # 查询字段
    field = await FieldSpec.filter(field_name="inherit_test_field").first()

    # 查询关联
    relation = await FieldGroupFieldSpec.filter(field_group_id=group.id).first()

    print(f"\n  继承链验证:")
    print(f"  应用(App) -> 页面(Page) -> 字段组(FieldGroup) -> 字段(Field)")
    print(f"  " + "-" * 50)

    # 验证应用 -> 页面
    app_to_page_ok = (page.app_name == app.app_name and page.tenant_id == app.tenant_id)
    print(f"  应用 -> 页面: {'✓' if app_to_page_ok else '✗'}")
    print(f"    应用: app_name={app.app_name}, tenant_id={app.tenant_id}")
    print(f"    页面: app_name={page.app_name}, tenant_id={page.tenant_id}")

    # 验证页面 -> 字段组
    page_to_group_ok = (group.app_name == page.app_name and group.tenant_id == page.tenant_id)
    print(f"\n  页面 -> 字段组: {'✓' if page_to_group_ok else '✗'}")
    print(f"    页面: app_name={page.app_name}, tenant_id={page.tenant_id}")
    print(f"    字段组: app_name={group.app_name}, tenant_id={group.tenant_id}")

    # 验证字段组 -> 字段
    group_to_field_ok = (field.app_name == group.app_name and field.tenant_id == group.tenant_id)
    print(f"\n  字段组 -> 字段: {'✓' if group_to_field_ok else '✗'}")
    print(f"    字段组: app_name={group.app_name}, tenant_id={group.tenant_id}")
    print(f"    字段: app_name={field.app_name}, tenant_id={field.tenant_id}")

    # 验证字段组 -> 关联
    group_to_relation_ok = (relation.app_name == group.app_name and relation.tenant_id == group.tenant_id)
    print(f"\n  字段组 -> 关联: {'✓' if group_to_relation_ok else '✗'}")
    print(f"    字段组: app_name={group.app_name}, tenant_id={group.tenant_id}")
    print(f"    关联: app_name={relation.app_name}, tenant_id={relation.tenant_id}")

    all_ok = app_to_page_ok and page_to_group_ok and group_to_field_ok and group_to_relation_ok
    print(f"\n  {'=' * 50}")
    print(f"  继承关系验证结果: {'全部通过 ✓' if all_ok else '存在错误 ✗'}")

async def main():
    await init_db()

    try:
        # 检查现有数据
        await check_existing_data()

        # 创建测试数据
        await create_test_data()

        # 验证继承关系
        await verify_inheritance()

    finally:
        await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
