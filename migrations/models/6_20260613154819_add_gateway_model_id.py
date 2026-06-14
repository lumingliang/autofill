from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `batch_test_task` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `tenant_id` BIGINT NOT NULL  COMMENT '租户ID' DEFAULT 0,
    `task_name` VARCHAR(200) NOT NULL  COMMENT '任务名称',
    `version_no` INT NOT NULL  COMMENT '版本号，从1开始，每次重新执行+1' DEFAULT 1,
    `dify_agent_id` BIGINT NOT NULL  COMMENT 'Dify Agent ID',
    `file_name` VARCHAR(500) NOT NULL  COMMENT '原始文件名',
    `file_size` INT NOT NULL  COMMENT '文件大小(字节)' DEFAULT 0,
    `row_count` INT NOT NULL  COMMENT '数据行数' DEFAULT 0,
    `collection_name` VARCHAR(200) NOT NULL  COMMENT 'SeekDB集合名称（包含版本号）',
    `status` INT NOT NULL  COMMENT '任务状态：0-待执行, 1-执行中, 2-已完成, 3-失败, 4-已停止' DEFAULT 0,
    `success_count` INT NOT NULL  COMMENT '成功数' DEFAULT 0,
    `fail_count` INT NOT NULL  COMMENT '失败数' DEFAULT 0,
    `remark` VARCHAR(1000) NOT NULL  COMMENT '备注' DEFAULT '',
    `created_by` BIGINT NOT NULL  COMMENT '创建人ID' DEFAULT 0,
    KEY `idx_batch_test__created_a5ad39` (`created_at`),
    KEY `idx_batch_test__updated_44cce0` (`updated_at`),
    KEY `idx_batch_test__tenant__19cd8c` (`tenant_id`),
    KEY `idx_batch_test__task_na_b59244` (`task_name`),
    KEY `idx_batch_test__dify_ag_834484` (`dify_agent_id`)
) CHARACTER SET utf8mb4 COMMENT='批量测试任务表';
        ALTER TABLE `llm_config` ADD `gateway_model_id` VARCHAR(64) NOT NULL  COMMENT 'LiteLLM网关中的模型ID' DEFAULT '';
        ALTER TABLE `llm_config` ADD INDEX `idx_llm_config_gateway_18cd15` (`gateway_model_id`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `llm_config` DROP INDEX `idx_llm_config_gateway_18cd15`;
        ALTER TABLE `llm_config` DROP COLUMN `gateway_model_id`;
        DROP TABLE IF EXISTS `batch_test_task`;"""
