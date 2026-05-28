from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- 删除旧的 JSON 字段
        ALTER TABLE `llm_config` DROP COLUMN `litellm_params`;
        ALTER TABLE `llm_config` DROP COLUMN `model_info`;
        
        -- 添加新的独立字段
        ALTER TABLE `llm_config` ADD `model` VARCHAR(128) NOT NULL  COMMENT '模型名称' DEFAULT '';
        ALTER TABLE `llm_config` ADD `api_key` VARCHAR(255) NOT NULL  COMMENT 'API Key' DEFAULT '';
        ALTER TABLE `llm_config` ADD `api_base` VARCHAR(255) NOT NULL  COMMENT 'API Base URL' DEFAULT '';
        ALTER TABLE `llm_config` ADD `timeout` INT NOT NULL  COMMENT '超时时间(秒)' DEFAULT 60;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- 删除新的独立字段
        ALTER TABLE `llm_config` DROP COLUMN `model`;
        ALTER TABLE `llm_config` DROP COLUMN `api_key`;
        ALTER TABLE `llm_config` DROP COLUMN `api_base`;
        ALTER TABLE `llm_config` DROP COLUMN `timeout`;
        
        -- 恢复旧的 JSON 字段
        ALTER TABLE `llm_config` ADD `litellm_params` JSON NOT NULL  COMMENT 'LiteLLM 参数配置' DEFAULT '{}';
        ALTER TABLE `llm_config` ADD `model_info` JSON NOT NULL  COMMENT '模型元信息' DEFAULT '{}';"""
