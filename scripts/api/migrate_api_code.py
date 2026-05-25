#!/usr/bin/env python3
"""
API Code 迁移脚本
用于数据库结构改造和数据迁移
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tortoise import Tortoise

from app.settings.config import settings


async def init_db():
    """初始化数据库连接"""
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def migrate_api_table():
    """迁移API表结构 - 添加api_code字段"""
    from tortoise.transactions import in_transaction

    async with in_transaction() as conn:
        # 1. 检查api_code字段是否存在
        try:
            await conn.execute_query("SELECT api_code FROM api LIMIT 1")
            print("✓ api_code 字段已存在")
        except Exception:
            print("→ 添加 api_code 字段...")
            await conn.execute_query("""
                ALTER TABLE api
                ADD COLUMN api_code VARCHAR(100) NOT NULL DEFAULT ''
            """)
            print("✓ api_code 字段添加成功")

        # 2. 添加唯一索引
        try:
            await conn.execute_query("""
                CREATE UNIQUE INDEX uk_api_code ON api(api_code)
            """)
            print("✓ 唯一索引 uk_api_code 创建成功")
        except Exception as e:
            if "Duplicate" in str(e) or "already exists" in str(e):
                print("✓ 唯一索引 uk_api_code 已存在")
            else:
                raise


async def generate_api_codes():
    """为现有API生成api_code"""
    from app.models.admin import Api

    print("\n→ 生成API Code...")

    apis = await Api.all()
    if not apis:
        print("✗ 没有找到API记录")
        return

    # 用于检测重复的api_code
    code_count = {}

    for api in apis:
        # 生成基础api_code
        path = api.path.replace("/api/v1/", "").strip("/")
        parts = path.split("/")

        if len(parts) >= 2:
            resource = parts[0]
            action = parts[1]
        elif len(parts) == 1:
            resource = parts[0]
            action = "default"
        else:
            resource = "unknown"
            action = "default"

        api_code = f"{resource}:{action}"

        # 检测重复并添加后缀
        if api_code in code_count:
            code_count[api_code] += 1
            api_code = f"{api_code}_{api.method.lower()}"
        else:
            code_count[api_code] = 0

        # 再次检查是否还有重复
        original_code = api_code
        counter = 1
        while await Api.filter(api_code=api_code).exclude(id=api.id).exists():
            api_code = f"{original_code}_{counter}"
            counter += 1

        api.api_code = api_code
        await api.save()
        print(f"  {api.method} {api.path} -> {api_code}")

    print(f"✓ 共生成 {len(apis)} 个API Code")


async def truncate_role_api():
    """清空角色-API关联表"""
    from tortoise.transactions import in_transaction

    print("\n→ 清空 role_api 表...")

    async with in_transaction() as conn:
        await conn.execute_query("TRUNCATE TABLE role_api")

    print("✓ role_api 表已清空")


async def assign_all_apis_to_admin_roles():
    """为管理员角色分配所有API权限"""
    from app.models.admin import Api, Role, RoleApi

    print("\n→ 为管理员角色分配所有API权限...")

    # 查找所有管理员角色（包括"管理员"和租户管理员）
    admin_roles = await Role.filter(name__contains="管理员").all()
    if not admin_roles:
        print("✗ 未找到管理员角色")
        return

    # 获取所有API
    apis = await Api.all()

    # 为每个管理员角色创建关联
    for role in admin_roles:
        for api in apis:
            await RoleApi.get_or_create(
                role_id=role.id,
                api_id=api.id,
                defaults={"tenant_id": role.tenant_id or 0}
            )
        print(f"  ✓ 已为角色 '{role.name}' 分配 {len(apis)} 个API权限")

    print(f"✓ 共为 {len(admin_roles)} 个管理员角色分配权限")


async def main():
    """主函数"""
    print("=" * 60)
    print("API Code 迁移脚本")
    print("=" * 60)

    try:
        # 初始化数据库
        print("\n→ 初始化数据库连接...")
        await init_db()
        print("✓ 数据库连接成功")

        # 执行迁移步骤
        await migrate_api_table()
        await generate_api_codes()
        await truncate_role_api()
        await assign_all_apis_to_admin_roles()

        print("\n" + "=" * 60)
        print("✓ 迁移完成！")
        print("=" * 60)
        print("\n注意：")
        print("1. 所有角色绑定的API权限已被清空")
        print("2. 只有超级管理员角色被自动分配了所有API权限")
        print("3. 其他角色需要重新在管理界面分配权限")
        print("\n请重启后端服务以应用更改。")

    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
