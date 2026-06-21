from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- 重命名 name 字段为 model_id
        ALTER TABLE `llm_config` CHANGE `name` `model_id` VARCHAR(128) NOT NULL COMMENT 'Model ID' DEFAULT '';
        -- 删除 model 字段
        ALTER TABLE `llm_config` DROP COLUMN `model`;
        -- 更新索引
        ALTER TABLE `llm_config` DROP INDEX `idx_llm_config_name_2543c4`;
        ALTER TABLE `llm_config` ADD INDEX `idx_llm_config_model_id_2543c4` (`model_id`);
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- 恢复 model 字段
        ALTER TABLE `llm_config` ADD `model` VARCHAR(128) NOT NULL COMMENT '模型名称' DEFAULT '';
        -- 恢复 name 字段
        ALTER TABLE `llm_config` CHANGE `model_id` `name` VARCHAR(128) NOT NULL COMMENT '配置名称' DEFAULT '';
        -- 恢复索引
        ALTER TABLE `llm_config` DROP INDEX `idx_llm_config_model_id_2543c4`;
        ALTER TABLE `llm_config` ADD INDEX `idx_llm_config_name_2543c4` (`name`);
    """
