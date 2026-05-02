#!/usr/bin/env python3
"""
数据修复脚本：将数据库中的 NULL 值更新为默认值
"""
import asyncio
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.settings.config import settings
from tortoise import Tortoise


async def fix_null_values():
    """修复所有表的 NULL 值"""
    # 初始化数据库连接
    await Tortoise.init(config=settings.TORTOISE_ORM)
    conn = Tortoise.get_connection("mysql")

    # 定义需要修复的表和字段
    fixes = [
        # (表名, 字段名, 字段类型, 默认值)
        ("api", "summary", "varchar", "''"),
        ("api", "tags", "varchar", "''"),
        ("app_management", "description", "varchar", "''"),
        ("auditlog", "tenant_domain", "varchar", "''"),
        ("auditlog", "request_args", "json", "'{}'"),
        ("auditlog", "response_body", "json", "'{}'"),
        ("auditlog", "tenant_id", "int", "0"),
        ("dept", "tenant_id", "int", "0"),
        ("dept", "desc", "varchar", "''"),
        ("dropdown_option", "description", "text", "''"),
        ("field_group_config", "page_id", "bigint", "0"),
        ("field_group_config", "page_name", "varchar", "''"),
        ("field_group_config", "prompt_template_base", "text", "''"),
        ("field_group_config", "group_name", "varchar", "''"),
        ("field_group_config", "description", "text", "''"),
        ("field_group_config", "app_name", "varchar", "''"),
        ("field_spec", "field_name", "varchar", "''"),
        ("field_spec", "field_group_id", "bigint", "0"),
        ("field_spec", "options", "json", "'{}'"),
        ("field_spec", "corrections", "json", "'[]'"),
        ("field_spec", "fill_instruction", "text", "''"),
        ("field_spec", "field_label", "varchar", "''"),
        ("fill_data_record", "data", "json", "'{}'"),
        ("fill_data_record", "error_msg", "text", "''"),
        ("fill_data_record", "result", "json", "'{}'"),
        ("fill_page", "app_id", "bigint", "0"),
        ("fill_page", "page_name", "varchar", "''"),
        ("fill_page", "page_code", "varchar", "''"),
        ("fill_page", "description", "text", "''"),
        ("fill_page", "app_name", "varchar", "''"),
        ("llm_config", "description", "text", "''"),
        ("llm_provider", "label", "varchar", "''"),
        ("llm_provider", "icon", "varchar", "''"),
        ("llm_provider", "description", "text", "''"),
        ("menu", "path", "varchar", "''"),
        ("menu", "remark", "json", "'{}'"),
        ("menu", "menu_type", "varchar", "'catalog'"),
        ("menu", "component", "varchar", "''"),
        ("menu", "icon", "varchar", "''"),
        ("menu", "redirect", "varchar", "''"),
        ("role", "tenant_id", "int", "0"),
        ("role", "desc", "varchar", "''"),
        ("role_api", "tenant_id", "int", "0"),
        ("role_menu", "tenant_id", "int", "0"),
        ("summary_template", "template_content", "text", "''"),
        ("tenant", "description", "varchar", "''"),
        ("user", "alias", "varchar", "''"),
        ("user", "dept_id", "int", "0"),
        ("user", "avatar", "varchar", "''"),
        ("user", "current_tenant_id", "int", "0"),
        ("user", "password", "varchar", "''"),
        ("user", "phone", "varchar", "''"),
        ("user_role", "tenant_id", "int", "0"),
    ]

    print("开始修复 NULL 值...")

    for table, column, col_type, default_value in fixes:
        try:
            # 更新 NULL 值为默认值
            sql = f"UPDATE `{table}` SET `{column}` = {default_value} WHERE `{column}` IS NULL"
            await conn.execute_script(sql)
            print(f"✅ 修复 {table}.{column}")
        except Exception as e:
            print(f"⚠️  {table}.{column}: {e}")

    print("\nNULL 值修复完成！")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(fix_null_values())
