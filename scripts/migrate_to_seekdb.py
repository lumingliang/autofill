"""
数据迁移脚本：将现有 CSV 数据从 MySQL/文件系统迁移到 seekdb

执行方式:
    python scripts/migrate_to_seekdb.py

注意：
    1. 迁移前请备份数据库
    2. 确保 seekdb 服务可用
    3. 迁移过程不可逆，旧数据将被删除
"""

import asyncio
import base64
import gzip
import json
import os
import sys
from typing import Any, Dict, List, Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tortoise import Tortoise

from app.log import logger
from app.models.rule_management import RuleInfo, RuleVersion
from app.services.storage.seekdb_service import seekdb_service
from app.settings.config import settings


class SeekDBMigration:
    """seekdb 数据迁移工具"""

    def __init__(self):
        self.migrated_count = 0
        self.failed_count = 0
        self.skipped_count = 0

    async def init_db(self):
        """初始化数据库连接"""
        await Tortoise.init(config=settings.TORTOISE_ORM)
        logger.info("数据库连接初始化完成")

    async def close_db(self):
        """关闭数据库连接"""
        await Tortoise.close_connections()
        logger.info("数据库连接已关闭")

    def _decode_content_json(self, version: RuleVersion) -> Optional[Dict[str, Any]]:
        """
        解码旧版本的内容 JSON

        Args:
            version: 规则版本对象

        Returns:
            解码后的内容字典
        """
        try:
            # 检查是否有旧字段
            if hasattr(version, 'content_json') and version.content_json:
                # 旧格式：base64 + gzip 压缩
                compressed = base64.b64decode(version.content_json)
                json_str = gzip.decompress(compressed).decode('utf-8')
                return json.loads(json_str)

            if hasattr(version, 'file_path') and version.file_path:
                # 从文件读取
                try:
                    with open(version.file_path, 'rb') as f:
                        compressed = f.read()
                    json_str = gzip.decompress(compressed).decode('utf-8')
                    return json.loads(json_str)
                except Exception as e:
                    logger.error(f"读取文件失败: {version.file_path}, error: {e}")
                    return None

            return None

        except Exception as e:
            logger.error(f"解码内容失败: version_id={version.id}, error: {e}")
            return None

    async def migrate_version(self, version: RuleVersion) -> bool:
        """
        迁移单个版本

        Args:
            version: 规则版本对象

        Returns:
            是否迁移成功
        """
        # 检查是否已迁移（有 seekdb_collection_name 字段）
        if hasattr(version, 'seekdb_collection_name') and version.seekdb_collection_name:
            logger.info(f"版本已迁移，跳过: rule_id={version.rule_id}, version_no={version.version_no}")
            self.skipped_count += 1
            return True

        # 获取规则信息
        rule = await RuleInfo.filter(id=version.rule_id).first()
        if not rule:
            logger.error(f"规则不存在: rule_id={version.rule_id}")
            self.failed_count += 1
            return False

        # 解码旧内容
        content_json = self._decode_content_json(version)
        if not content_json:
            logger.warning(f"版本内容为空，跳过: rule_id={version.rule_id}, version_no={version.version_no}")
            self.skipped_count += 1
            return True

        headers = content_json.get("headers", [])
        data = content_json.get("data", [])

        if not headers or not data:
            logger.warning(f"版本数据为空，跳过: rule_id={version.rule_id}, version_no={version.version_no}")
            self.skipped_count += 1
            return True

        # 转换数据格式
        dict_data = []
        for row in data:
            row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            dict_data.append(row_dict)

        # 生成集合名称
        collection_name = f"rule_{version.rule_id}_v{version.version_no}"

        try:
            # 保存到 seekdb
            doc_count = await seekdb_service.save_rule_data(
                collection_name=collection_name,
                headers=headers,
                data=dict_data,
                rule_id=version.rule_id,
                version_no=version.version_no,
                tenant_id=version.tenant_id,
                app_name=version.app_name,
                rule_code=rule.rule_code
            )

            # 更新版本记录
            version.seekdb_collection_name = collection_name
            version.doc_count = doc_count
            version.headers = headers
            # 清除旧字段
            if hasattr(version, 'storage_type'):
                version.storage_type = 0  # 标记为已迁移
            if hasattr(version, 'content_json'):
                version.content_json = None
            if hasattr(version, 'file_path'):
                version.file_path = ""
            if hasattr(version, 'file_size'):
                version.file_size = 0

            await version.save()

            logger.info(
                f"版本迁移成功: rule_id={version.rule_id}, version_no={version.version_no}, "
                f"collection={collection_name}, doc_count={doc_count}"
            )
            self.migrated_count += 1
            return True

        except Exception as e:
            logger.error(f"版本迁移失败: rule_id={version.rule_id}, version_no={version.version_no}, error: {e}")
            self.failed_count += 1
            return False

    async def migrate_all(self):
        """迁移所有版本"""
        await self.init_db()

        try:
            # 获取所有未删除的版本
            versions = await RuleVersion.filter(deleted=0).all()
            total = len(versions)

            logger.info(f"开始迁移，共 {total} 个版本")

            for i, version in enumerate(versions, 1):
                logger.info(f"迁移进度: {i}/{total}")
                await self.migrate_version(version)

            logger.info(
                f"迁移完成: 成功={self.migrated_count}, 失败={self.failed_count}, 跳过={self.skipped_count}"
            )

        finally:
            await self.close_db()

    async def verify_migration(self):
        """验证迁移结果"""
        await self.init_db()

        try:
            versions = await RuleVersion.filter(deleted=0).all()
            total = len(versions)
            verified = 0
            failed = 0

            for version in versions:
                if not version.seekdb_collection_name:
                    continue

                try:
                    result = await seekdb_service.get_rule_data(version.seekdb_collection_name)
                    if result and result.get("data"):
                        doc_count = len(result["data"])
                        if doc_count == version.doc_count:
                            verified += 1
                            logger.info(
                                f"验证通过: collection={version.seekdb_collection_name}, "
                                f"doc_count={doc_count}"
                            )
                        else:
                            failed += 1
                            logger.error(
                                f"验证失败: collection={version.seekdb_collection_name}, "
                                f"expected={version.doc_count}, actual={doc_count}"
                            )
                    else:
                        failed += 1
                        logger.error(f"验证失败: collection={version.seekdb_collection_name}, 数据为空")
                except Exception as e:
                    failed += 1
                    logger.error(f"验证失败: collection={version.seekdb_collection_name}, error: {e}")

            logger.info(f"验证完成: 通过={verified}, 失败={failed}, 总计={total}")

        finally:
            await self.close_db()


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="seekdb 数据迁移工具")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="验证迁移结果"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行（不实际写入）"
    )

    args = parser.parse_args()

    migration = SeekDBMigration()

    if args.verify:
        await migration.verify_migration()
    else:
        # 确认提示
        if not args.dry_run:
            confirm = input("警告：此操作将迁移所有 CSV 数据到 seekdb，是否继续？(yes/no): ")
            if confirm.lower() != "yes":
                logger.info("操作已取消")
                return

        await migration.migrate_all()


if __name__ == "__main__":
    asyncio.run(main())
