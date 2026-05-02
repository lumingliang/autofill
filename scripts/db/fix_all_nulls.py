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

    # 定义需要修复的表和字段 - 包含所有可能的字段
    fixes = [
        # (表名, 字段名, 默认值SQL表达式)
        # 字符串字段
        ("api", "summary", "''"),
        ("api", "tags", "''"),
        ("app_management", "description", "''"),
        ("auditlog", "tenant_domain", "''"),
        ("dept", "desc", "''"),
        ("field_group_config", "page_name", "''"),
        ("field_group_config", "group_name", "''"),
        ("field_group_config", "app_name", "''"),
        ("field_spec", "field_name", "''"),
        ("field_spec", "field_label", "''"),
        ("fill_page", "page_name", "''"),
        ("fill_page", "app_name", "''"),
        ("fill_page", "page_code", "''"),
        ("llm_provider", "icon", "''"),
        ("llm_provider", "label", "''"),
        ("menu", "menu_type", "'catalog'"),
        ("menu", "component", "''"),
        ("menu", "icon", "''"),
        ("menu", "path", "''"),
        ("menu", "redirect", "''"),
        ("role", "desc", "''"),
        ("tenant", "description", "''"),
        ("user", "alias", "''"),
        ("user", "avatar", "''"),
        ("user", "password", "''"),
        ("user", "phone", "''"),

        # 整数字段
        ("auditlog", "tenant_id", "0"),
        ("dept", "tenant_id", "0"),
        ("field_group_config", "page_id", "0"),
        ("field_spec", "field_group_id", "0"),
        ("fill_page", "app_id", "0"),
        ("role", "tenant_id", "0"),
        ("role_api", "tenant_id", "0"),
        ("role_menu", "tenant_id", "0"),
        ("user", "dept_id", "0"),
        ("user", "current_tenant_id", "0"),
        ("user_role", "tenant_id", "0"),

        # JSON 字段
        ("auditlog", "request_args", "'{}'"),
        ("auditlog", "response_body", "'{}'"),
        ("field_spec", "options", "'{}'"),
        ("field_spec", "corrections", "'[]'"),
        ("fill_data_record", "data", "'{}'"),
        ("fill_data_record", "result", "'{}'"),
        ("menu", "remark", "'{}'"),

        # TEXT/LONGTEXT 字段 - 设为空字符串
        ("dropdown_option", "description", "''"),
        ("field_group_config", "prompt_template_base", "''"),
        ("field_group_config", "description", "''"),
        ("field_spec", "fill_instruction", "''"),
        ("fill_data_record", "error_msg", "''"),
        ("fill_page", "description", "''"),
        ("llm_config", "description", "''"),
        ("llm_provider", "description", "''"),
        ("summary_template", "template_content", "''"),

        # 布尔字段
        ("field_spec", "is_active", "1"),
        ("fill_page", "is_active", "1"),
    ]

    print("开始修复 NULL 值...")

    for table, column, default_value in fixes:
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
