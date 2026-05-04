#!/usr/bin/env python3
"""
字段组与字段多对多关联迁移脚本
将原来的一对多关系（FieldSpec.field_group_id）迁移为多对多关系（通过FieldGroupFieldSpec中间表）
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tortoise import Tortoise
from app.settings.config import settings
from app.log import logger


async def migrate():
    """执行迁移"""
    # 初始化数据库连接
    db_url = f"mysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models']}
    )

    logger.info("开始迁移字段组与字段关联关系...")

    # 获取数据库连接
    conn = Tortoise.get_connection('default')

    # 1. 检查中间表是否存在，不存在则创建
    logger.info("检查中间表 field_group_field_spec...")
    try:
        await conn.execute_query(
            """CREATE TABLE IF NOT EXISTS field_group_field_spec (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                field_group_id BIGINT NOT NULL,
                field_spec_id BIGINT NOT NULL,
                tenant_id BIGINT NOT NULL DEFAULT 0,
                app_name VARCHAR(64) NOT NULL DEFAULT '',
                created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
                updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                INDEX idx_field_group_id (field_group_id),
                INDEX idx_field_spec_id (field_spec_id),
                INDEX idx_tenant_id (tenant_id),
                INDEX idx_app_name (app_name),
                UNIQUE KEY uk_group_spec (field_group_id, field_spec_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
        )
        logger.info("中间表创建成功或已存在")
    except Exception as e:
        logger.error(f"创建中间表失败: {e}")
        raise

    # 2. 迁移现有数据（从旧的一对多关系到新的多对多关系）
    logger.info("迁移现有字段关联数据...")
    try:
        # 检查 field_spec 表是否有 field_group_id 字段
        result = await conn.execute_query(
            """SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_NAME = 'field_spec' AND COLUMN_NAME = 'field_group_id'"""
        )

        if result[1]:
            # 查询所有有 field_group_id 的字段
            result = await conn.execute_query(
                """SELECT id, tenant_id, app_name, field_group_id FROM field_spec
                   WHERE field_group_id > 0"""
            )

            migrated_count = 0
            for row in result[1]:  # result[1] 是数据行
                field_spec_id = row[0]
                tenant_id = row[1] or 0
                app_name = row[2] or ""
                field_group_id = row[3]

                # 检查是否已存在
                exists = await conn.execute_query(
                    """SELECT 1 FROM field_group_field_spec
                       WHERE field_group_id = %s AND field_spec_id = %s""",
                    [field_group_id, field_spec_id]
                )

                if not exists[1]:  # 不存在则插入
                    await conn.execute_query(
                        """INSERT INTO field_group_field_spec
                           (field_group_id, field_spec_id, tenant_id, app_name)
                           VALUES (%s, %s, %s, %s)""",
                        [field_group_id, field_spec_id, tenant_id, app_name]
                    )
                    migrated_count += 1

            logger.info(f"成功迁移 {migrated_count} 条关联数据")
        else:
            logger.info("field_spec 表没有 field_group_id 字段，跳过数据迁移")
    except Exception as e:
        logger.error(f"迁移数据失败: {e}")
        raise

    # 3. 为 FieldSpec 表添加 app_name 字段（如果不存在）
    logger.info("检查 field_spec 表结构...")
    try:
        # 检查 app_name 字段是否存在
        result = await conn.execute_query(
            """SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_NAME = 'field_spec' AND COLUMN_NAME = 'app_name'"""
        )

        if not result[1]:
            # 添加 app_name 字段
            await conn.execute_query(
                """ALTER TABLE field_spec
                   ADD COLUMN app_name VARCHAR(64) NOT NULL DEFAULT '' AFTER tenant_id"""
            )
            logger.info("添加 app_name 字段成功")

            # 从字段组更新 app_name
            await conn.execute_query(
                """UPDATE field_spec fs
                   JOIN field_group_config fgc ON fs.field_group_id = fgc.id
                   SET fs.app_name = fgc.app_name
                   WHERE fs.field_group_id > 0"""
            )
            logger.info("更新 app_name 字段数据成功")
        else:
            logger.info("app_name 字段已存在")
    except Exception as e:
        logger.error(f"修改 field_spec 表结构失败: {e}")
        raise

    # 4. 可选：删除旧的 field_group_id 字段（如果需要保留历史数据，可以跳过）
    # logger.info("删除旧的 field_group_id 字段...")
    # try:
    #     await conn.execute_query(
    #         """ALTER TABLE field_spec DROP COLUMN field_group_id"""
    #     )
    #     logger.info("删除 field_group_id 字段成功")
    # except Exception as e:
    #     logger.error(f"删除 field_group_id 字段失败: {e}")
    #     # 不抛出异常，因为这不是关键步骤

    logger.info("迁移完成！")

    # 关闭连接
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(migrate())
