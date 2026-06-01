from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `dify_agent` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(100) NOT NULL  COMMENT 'Agent名称',
    `tenant_id` BIGINT NOT NULL  COMMENT '租户ID' DEFAULT 0,
    `api_key` VARCHAR(255) NOT NULL  COMMENT 'Dify API Key',
    `agent_url` VARCHAR(500) NOT NULL  COMMENT 'Dify Agent URL',
    `description` VARCHAR(500) NOT NULL  COMMENT '描述' DEFAULT '',
    `is_active` BOOL NOT NULL  COMMENT '是否启用' DEFAULT 1,
    KEY `idx_dify_agent_created_60ea34` (`created_at`),
    KEY `idx_dify_agent_updated_cefa69` (`updated_at`),
    KEY `idx_dify_agent_name_29b82e` (`name`),
    KEY `idx_dify_agent_tenant__4368da` (`tenant_id`),
    KEY `idx_dify_agent_api_ke_8c8fa0` (`api_key`),
    KEY `idx_dify_agent_is_act_9d2f1a` (`is_active`)
) CHARACTER SET utf8mb4 COMMENT='Dify Agent 配置表';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `dify_agent`;
    """
