#!/usr/bin/env python3
"""
数据库结构管理工具

支持多种场景：
1. 本地开发：基于模型生成迁移（已有表）
2. 测试环境：对比差异并同步
3. 生产环境：初始化空数据库

使用方法：
    # 本地：生成迁移（不提交到 Git）
    python scripts/db_schema_manager.py generate

    # 测试环境：对比差异
    python scripts/db_schema_manager.py diff --target test

    # 生产环境：初始化空数据库
    python scripts/db_schema_manager.py init --target production

    # 导出完整 SQL（用于生产初始化）
    python scripts/db_schema_manager.py export --output init.sql
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tortoise import Tortoise
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from app.settings import TORTOISE_ORM


class DatabaseSchemaManager:
    """数据库结构管理器"""

    def __init__(self):
        self.connection = None

    async def init_db(self):
        """初始化数据库连接"""
        await Tortoise.init(config=TORTOISE_ORM)
        self.connection = Tortoise.get_connection("mysql")

    async def close(self):
        """关闭数据库连接"""
        await Tortoise.close_connections()

    async def get_existing_tables(self):
        """获取数据库中已存在的表"""
        result = await self.connection.execute_query(
            "SHOW TABLES"
        )
        return [row[0] for row in result[1]]

    async def get_table_schema(self, table_name):
        """获取表结构"""
        try:
            result = await self.connection.execute_query(
                f"SHOW CREATE TABLE `{table_name}`"
            )
            return result[1][0][1] if result[1] else None
        except Exception:
            return None

    async def generate_migration(self):
        """
        生成本地迁移（不修改数据库）
        适用于：本地已有表，需要记录当前状态
        """
        print("=" * 60)
        print("生成本地迁移")
        print("=" * 60)

        await self.init_db()

        # 获取现有表
        existing_tables = await self.get_existing_tables()
        print(f"\n发现 {len(existing_tables)} 个现有表:")
        for table in existing_tables:
            print(f"  - {table}")

        # 创建迁移目录（不提交到 Git）
        migrations_dir = project_root / "migrations" / "local"
        migrations_dir.mkdir(parents=True, exist_ok=True)

        # 创建 .gitignore 确保不提交
        gitignore = migrations_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n!.gitignore\n")
            print(f"\n✓ 创建 {gitignore}（确保迁移文件不提交到 Git）")

        # 生成迁移文件
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        migration_file = migrations_dir / f"{timestamp}_local_init.py"

        # 收集所有表结构
        schemas = []
        for table in existing_tables:
            schema = await self.get_table_schema(table)
            if schema:
                schemas.append({"table": table, "sql": schema})

        # 生成迁移内容
        migration_content = self._generate_migration_content(schemas, timestamp)
        migration_file.write_text(migration_content)

        print(f"\n✓ 迁移文件已生成: {migration_file}")
        print(f"\n注意：此迁移文件位于 migrations/local/，不会被提交到 Git")
        print("如需提交到 Git，请手动移动到 migrations/models/")

        await self.close()

    def _generate_migration_content(self, schemas, timestamp):
        """生成迁移文件内容"""
        tables_info = "\n".join([
            f"# Table: {s['table']}\n# {s['sql'][:100]}..."
            for s in schemas[:5]  # 只显示前5个
        ])

        return f'''"""
本地初始迁移
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

该迁移记录了本地现有表结构状态。
"""

# 现有表结构记录（供参考）
"""
{tables_info}
...
"""

async def upgrade(conn) -> None:
    """
    升级操作
    
    注意：此迁移为记录性质，不执行实际的 DDL 操作。
    如需同步到其他环境，请手动对比差异。
    """
    pass


async def downgrade(conn) -> None:
    """
    降级操作
    
    注意：此迁移为记录性质，不执行实际的 DDL 操作。
    """
    pass
'''

    async def compare_schemas(self, target_env="test"):
        """
        对比当前环境与目标环境的表结构差异
        适用于：测试环境与本地不一致时
        """
        print("=" * 60)
        print(f"对比表结构差异 (当前 vs {target_env})")
        print("=" * 60)

        await self.init_db()

        # 获取当前环境的表
        current_tables = await self.get_existing_tables()
        print(f"\n当前环境表数量: {len(current_tables)}")

        # 获取模型定义的表（期望状态）
        expected_tables = self._get_expected_tables()
        print(f"模型定义表数量: {len(expected_tables)}")

        # 对比差异
        missing_in_db = expected_tables - set(current_tables)
        extra_in_db = set(current_tables) - expected_tables

        print("\n" + "-" * 60)
        print("差异分析:")
        print("-" * 60)

        if missing_in_db:
            print(f"\n⚠ 数据库缺少以下表（需要创建）:")
            for table in sorted(missing_in_db):
                print(f"   - {table}")

        if extra_in_db:
            print(f"\n⚠ 数据库有多余的表（可能需要清理）:")
            for table in sorted(extra_in_db):
                print(f"   - {table}")

        if not missing_in_db and not extra_in_db:
            print("\n✓ 表结构一致")

        # 对比每个表的字段
        print("\n" + "-" * 60)
        print("表字段差异（详细）:")
        print("-" * 60)

        for table in sorted(expected_tables & set(current_tables)):
            await self._compare_table_columns(table)

        await self.close()

    def _get_expected_tables(self):
        """从模型获取期望的表名"""
        tables = set()
        for app_name, app_config in TORTOISE_ORM.get("apps", {}).items():
            for model_path in app_config.get("models", []):
                if model_path == "aerich.models":
                    continue
                try:
                    model_module = __import__(model_path, fromlist=[""])
                    for attr_name in dir(model_module):
                        attr = getattr(model_module, attr_name)
                        if hasattr(attr, "_meta") and hasattr(attr._meta, "table"):
                            tables.add(attr._meta.table)
                except Exception:
                    pass
        return tables

    async def _compare_table_columns(self, table_name):
        """对比单个表的字段"""
        try:
            result = await self.connection.execute_query(
                f"DESCRIBE `{table_name}`"
            )
            db_columns = {row[0]: row[1] for row in result[1]}
            print(f"\n  Table: {table_name}")
            print(f"    字段数: {len(db_columns)}")
        except Exception as e:
            print(f"\n  Table: {table_name} (无法获取: {e})")

    async def init_production(self):
        """
        初始化生产环境（空数据库）
        适用于：生产环境全新部署
        """
        print("=" * 60)
        print("初始化生产环境数据库")
        print("=" * 60)

        await self.init_db()

        # 检查是否为空数据库
        existing_tables = await self.get_existing_tables()
        if existing_tables:
            print(f"\n⚠ 警告：数据库中已有 {len(existing_tables)} 个表")
            print("   如需重新初始化，请先手动清理数据库")
            for table in existing_tables:
                print(f"   - {table}")
            await self.close()
            return

        print("\n✓ 确认数据库为空，开始初始化...")

        # 生成建表 SQL
        from tortoise import Tortoise
        generator = MySQLSchemaGenerator(self.connection)

        # 获取所有模型
        models = []
        for app_name, app_config in TORTOISE_ORM.get("apps", {}).items():
            for model_path in app_config.get("models", []):
                if model_path == "aerich.models":
                    continue
                try:
                    model_module = __import__(model_path, fromlist=[""])
                    for attr_name in dir(model_module):
                        attr = getattr(model_module, attr_name)
                        if hasattr(attr, "_meta") and hasattr(attr._meta, "table"):
                            models.append(attr)
                except Exception:
                    pass

        # 生成并执行 SQL
        print(f"\n将创建 {len(models)} 个表:")
        for model in models:
            table_name = model._meta.table
            print(f"  - {table_name}")

        confirm = input("\n确认执行？(yes/no): ")
        if confirm.lower() != "yes":
            print("已取消")
            await self.close()
            return

        # 创建表
        for model in models:
            try:
                schema = generator._get_table_schema(model)
                await self.connection.execute_query(schema)
                print(f"  ✓ 创建表: {model._meta.table}")
            except Exception as e:
                print(f"  ✗ 创建表失败 {model._meta.table}: {e}")

        # 创建 aerich 表并记录
        try:
            await self.connection.execute_query("""
                CREATE TABLE IF NOT EXISTS aerich (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    version VARCHAR(255) NOT NULL UNIQUE,
                    app VARCHAR(100) NOT NULL,
                    content JSON NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            import json
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            version = f"{timestamp}_initial"
            content = {
                "version": version,
                "app": "models",
                "tables": [m._meta.table for m in models],
                "note": "Production initial migration"
            }
            await self.connection.execute_query(
                "INSERT INTO aerich (version, app, content) VALUES (%s, %s, %s)",
                [version, "models", json.dumps(content)]
            )
            print(f"\n✓ 迁移状态已记录: {version}")
        except Exception as e:
            print(f"\n⚠ 记录迁移状态时出错: {e}")

        print("\n✓ 生产环境初始化完成")
        await self.close()

    async def export_sql(self, output_file="init.sql"):
        """
        导出完整建表 SQL
        适用于：需要 DBA 审核或手动执行的场景
        """
        print("=" * 60)
        print("导出建表 SQL")
        print("=" * 60)

        await self.init_db()
        generator = MySQLSchemaGenerator(self.connection)

        # 收集所有 SQL
        sql_statements = []
        sql_statements.append("-- 数据库初始化 SQL")
        sql_statements.append(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sql_statements.append("")

        # 获取所有模型
        models = []
        for app_name, app_config in TORTOISE_ORM.get("apps", {}).items():
            for model_path in app_config.get("models", []):
                if model_path == "aerich.models":
                    continue
                try:
                    model_module = __import__(model_path, fromlist=[""])
                    for attr_name in dir(model_module):
                        attr = getattr(model_module, attr_name)
                        if hasattr(attr, "_meta") and hasattr(attr._meta, "table"):
                            models.append(attr)
                except Exception:
                    pass

        for model in models:
            try:
                schema = generator._get_table_schema(model)
                sql_statements.append(f"-- Table: {model._meta.table}")
                sql_statements.append(schema + ";")
                sql_statements.append("")
            except Exception as e:
                print(f"  ✗ 生成 SQL 失败 {model._meta.table}: {e}")

        # 写入文件
        output_path = project_root / output_file
        output_path.write_text("\n".join(sql_statements))

        print(f"\n✓ SQL 已导出到: {output_path}")
        print(f"  包含 {len(models)} 个表的建表语句")

        await self.close()


async def main():
    parser = argparse.ArgumentParser(
        description="数据库结构管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 本地生成迁移（不提交 Git）
  python scripts/db_schema_manager.py generate

  # 对比测试环境差异
  python scripts/db_schema_manager.py diff

  # 初始化生产环境
  python scripts/db_schema_manager.py init

  # 导出 SQL 文件
  python scripts/db_schema_manager.py export --output prod_init.sql
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # generate 命令
    gen_parser = subparsers.add_parser(
        "generate",
        help="生成本地迁移（不提交 Git）"
    )

    # diff 命令
    diff_parser = subparsers.add_parser(
        "diff",
        help="对比环境差异"
    )
    diff_parser.add_argument(
        "--target",
        default="test",
        help="目标环境名称（仅用于显示）"
    )

    # init 命令
    init_parser = subparsers.add_parser(
        "init",
        help="初始化生产环境"
    )

    # export 命令
    export_parser = subparsers.add_parser(
        "export",
        help="导出建表 SQL"
    )
    export_parser.add_argument(
        "--output",
        default="init.sql",
        help="输出文件名"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = DatabaseSchemaManager()

    if args.command == "generate":
        await manager.generate_migration()
    elif args.command == "diff":
        await manager.compare_schemas(args.target)
    elif args.command == "init":
        await manager.init_production()
    elif args.command == "export":
        await manager.export_sql(args.output)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
