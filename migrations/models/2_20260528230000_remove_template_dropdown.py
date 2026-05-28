from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `summary_template`;
        DROP TABLE IF EXISTS `dropdown_option`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `summary_template` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `name` VARCHAR(128) NOT NULL  COMMENT '模板名称',
            `app_name` VARCHAR(64) NOT NULL  COMMENT '应用名称(英文)',
            `tenant_id` BIGINT NOT NULL  COMMENT '租户ID' DEFAULT 0,
            `class_name` VARCHAR(64) NOT NULL  COMMENT '模板分类',
            `summary` VARCHAR(500) NOT NULL  COMMENT '模板摘要' DEFAULT '',
            `template_content` LONGTEXT NOT NULL  COMMENT '模板内容',
            KEY `idx_summary_temp_name_c5b0f5` (`name`),
            KEY `idx_summary_temp_app_n_6f6c0c` (`app_name`),
            KEY `idx_summary_temp_tenant_3e42f1` (`tenant_id`),
            KEY `idx_summary_temp_class__5d0f6b` (`class_name`)
        ) CHARACTER SET utf8mb4 COMMENT='总结类填单模板表';
        CREATE TABLE IF NOT EXISTS `dropdown_option` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `summary` VARCHAR(500) NOT NULL  COMMENT '显示标签（下拉框中显示的文本）' DEFAULT '',
            `description` LONGTEXT NOT NULL  COMMENT '选项说明（帮助提示信息）',
            `class_name` VARCHAR(64) NOT NULL  COMMENT '模板分类',
            `tenant_id` BIGINT NOT NULL  COMMENT '租户ID' DEFAULT 0,
            `app_name` VARCHAR(64) NOT NULL  COMMENT '应用名称(英文)',
            `parent_id` BIGINT NOT NULL  COMMENT '父选项ID，0表示顶级选项' DEFAULT 0,
            `option_value` VARCHAR(128) NOT NULL  COMMENT '选项编码（唯一标识，如 EVT001）',
            KEY `idx_dropdown_opt_class__9b5e4c` (`class_name`),
            KEY `idx_dropdown_opt_tenant_8c2a3d` (`tenant_id`),
            KEY `idx_dropdown_opt_app_nam_7d4e5f` (`app_name`),
            KEY `idx_dropdown_opt_parent__1a2b3c` (`parent_id`),
            KEY `idx_dropdown_opt_option__4f5g6h` (`option_value`)
        ) CHARACTER SET utf8mb4 COMMENT='下拉选项类填单模板表';"""
