from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `app_management` DROP COLUMN `dify_api_key`;
        ALTER TABLE `app_management` DROP COLUMN `dify_url`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `app_management` ADD `dify_api_key` VARCHAR(128) NOT NULL  COMMENT 'Dify API密钥' DEFAULT '';
        ALTER TABLE `app_management` ADD `dify_url` VARCHAR(255) NOT NULL  COMMENT 'Dify服务地址' DEFAULT '';"""
