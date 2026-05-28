#!/usr/bin/env python3
"""
Aerich 伪初始化脚本

用于本地开发环境已有表结构的情况。
该脚本会创建 aerich 迁移记录，标记所有现有表为已迁移状态，
而不会实际修改任何表结构。

使用场景：
- 本地开发环境数据库已有表结构
- 需要将现有项目接入 Aerich 迁移管理
- 避免重复创建已存在的表

使用方法：
    python scripts/aerich_fake_init.py
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tortoise import Tortoise
from app.settings import TORTOISE_ORM


async def fake_init():
    """
    执行伪初始化：
    1. 初始化 Tortoise ORM 连接
    2. 获取所有模型对应的表名
    3. 创建 aerich 迁移目录结构
    4. 生成初始迁移文件（标记为已执行）
    5. 在数据库中记录迁移状态
    """
    print("=" * 60)
    print("Aerich 伪初始化工具")
    print("=" * 60)
    print()

    # 1. 初始化数据库连接
    print("[1/5] 初始化数据库连接...")
    await Tortoise.init(config=TORTOISE_ORM)
    print("    ✓ 数据库连接成功")
    print()

    # 2. 获取所有模型表名
    print("[2/5] 扫描模型定义...")
    connection = Tortoise.get_connection("mysql")

    # 获取所有注册的模型
    models = []
    for app_name, app_config in TORTOISE_ORM.get("apps", {}).items():
        for model_path in app_config.get("models", []):
            if model_path == "aerich.models":
                continue
            # 获取模型类
            model_module = __import__(model_path, fromlist=[""])
            for attr_name in dir(model_module):
                attr = getattr(model_module, attr_name)
                if hasattr(attr, "_meta") and hasattr(attr._meta, "table"):
                    table_name = attr._meta.table
                    if table_name and table_name not in [m["table"] for m in models]:
                        models.append({
                            "name": attr_name,
                            "table": table_name,
                            "module": model_path
                        })
                        print(f"    - {attr_name} -> {table_name}")

    print(f"    ✓ 发现 {len(models)} 个模型")
    print()

    # 3. 创建迁移目录结构
    print("[3/5] 创建迁移目录结构...")
    migrations_dir = project_root / "migrations" / "models"
    migrations_dir.mkdir(parents=True, exist_ok=True)

    # 创建 __init__.py
    init_file = migrations_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")
        print(f"    ✓ 创建 {init_file.relative_to(project_root)}")

    # 创建 aerich 系统表（如果不存在）
    print("[4/5] 检查 aerich 系统表...")
    try:
        # 检查 aerich 表是否存在
        result = await connection.execute_query(
            "SHOW TABLES LIKE 'aerich'"
        )
        if not result[1]:
            # 创建 aerich 表
            await connection.execute_query("""
                CREATE TABLE aerich (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    version VARCHAR(255) NOT NULL UNIQUE,
                    app VARCHAR(100) NOT NULL,
                    content JSON NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("    ✓ 创建 aerich 系统表")
        else:
            print("    ✓ aerich 系统表已存在")
    except Exception as e:
        print(f"    ⚠ 检查 aerich 表时出错: {e}")
        print("    尝试继续...")

    print()

    # 4. 生成初始迁移文件
    print("[5/5] 生成初始迁移文件...")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    version = f"{timestamp}_initial"
    migration_file = migrations_dir / f"{version}.py"

    # 生成迁移文件内容
    tables_info = []
    for model in models:
        try:
            # 获取表结构信息
            result = await connection.execute_query(
                f"SHOW CREATE TABLE `{model['table']}`"
            )
            if result[1]:
                create_sql = result[1][0][1]
                tables_info.append({
                    "table": model["table"],
                    "sql": create_sql
                })
        except Exception as e:
            print(f"    ⚠ 无法获取 {model['table']} 的表结构: {e}")

    migration_content = f'''"""
初始迁移
由 aerich_fake_init.py 自动生成
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

该迁移标记所有现有表为已迁移状态。
"""

from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator


async def upgrade(conn) -> None:
    # 表已存在，无需执行任何操作
    pass


async def downgrade(conn) -> None:
    # 注意：降级操作不会删除已有表，需要手动处理
    pass
'''

    migration_file.write_text(migration_content)
    print(f"    ✓ 创建迁移文件: {migration_file.relative_to(project_root)}")

    # 5. 记录迁移状态到数据库
    print()
    print("[6/5] 记录迁移状态...")
    try:
        import json
        content = {
            "version": version,
            "app": "models",
            "tables": [m["table"] for m in models],
            "upgrade": "pass",
            "downgrade": "pass"
        }

        # 检查是否已有记录
        result = await connection.execute_query(
            "SELECT id FROM aerich WHERE version = %s",
            [version]
        )

        if not result[1]:
            await connection.execute_query(
                "INSERT INTO aerich (version, app, content) VALUES (%s, %s, %s)",
                [version, "models", json.dumps(content)]
            )
            print(f"    ✓ 迁移状态已记录: {version}")
        else:
            print(f"    ✓ 迁移状态已存在: {version}")

    except Exception as e:
        print(f"    ⚠ 记录迁移状态时出错: {e}")
        print("    请手动执行以下 SQL:")
        print(f"    INSERT INTO aerich (version, app, content) VALUES ('{version}', 'models', '<content>');")

    print()
    print("=" * 60)
    print("伪初始化完成！")
    print("=" * 60)
    print()
    print("后续操作:")
    print("  1. 提交迁移文件到 Git:")
    print(f"     git add migrations/")
    print(f"     git commit -m 'chore: initialize aerich migrations'")
    print()
    print("  2. 验证迁移状态:")
    print("     aerich history")
    print()
    print("  3. 修改模型后生成新迁移:")
    print("     aerich migrate --name <描述>")
    print()

    await Tortoise.close_connections()


if __name__ == "__main__":
    try:
        asyncio.run(fake_init())
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
