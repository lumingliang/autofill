-- ============================================
-- 数据库清理脚本
-- 保留：大模型配置、菜单、超管用户(admin)
-- 备份文件：backup_autofill_20260529_082614.sql
-- ============================================

-- 关闭外键检查（如果有）
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- 1. 清理审计日志 (auditlog) - 全部删除
-- ============================================
DELETE FROM auditlog;

-- ============================================
-- 2. 清理填单数据记录 (fill_data_record) - 全部删除
-- ============================================
DELETE FROM fill_data_record;

-- ============================================
-- 3. 清理应用管理 (app_management) - 全部删除
-- ============================================
DELETE FROM app_management;

-- ============================================
-- 4. 清理规则相关数据 (rule_version, rule_info) - 全部删除
-- ============================================
DELETE FROM rule_version;

DELETE FROM rule_info;

-- ============================================
-- 5. 清理系统提示词 (system_prompt) - 全部删除
-- ============================================
DELETE FROM system_prompt;

-- ============================================
-- 6. 清理部门相关数据
-- ============================================
DELETE FROM deptclosure;

DELETE FROM dept;

-- ============================================
-- 7. 清理租户关联数据 (保留租户表本身)
-- ============================================
DELETE FROM user_tenant WHERE user_id != 1;

-- ============================================
-- 8. 清理角色关联数据
-- ============================================
-- 先删除所有角色关联
DELETE FROM user_role;

DELETE FROM role_menu;

DELETE FROM role_api;

-- 删除所有非系统角色，保留系统角色（id=3 测试租户A管理员 是系统角色）
DELETE FROM role WHERE is_system = 0;

-- 为超管用户关联系统角色（id=3 测试租户A管理员）
INSERT INTO user_role (user_id, role_id, tenant_id) VALUES (1, 3, 1);

-- ============================================
-- 9. 清理用户数据 - 只保留超管用户(admin, id=1)
-- ============================================
DELETE FROM user WHERE id != 1;

-- ============================================
-- 10. 清理租户数据 - 只保留默认租户(id=1)
-- ============================================
DELETE FROM tenant WHERE id != 1;

-- ============================================
-- 11. 清理API数据 - 全部删除（菜单保留）
-- ============================================
DELETE FROM api;

-- ============================================
-- 12. 为系统角色关联所有菜单
-- ============================================
INSERT INTO
    role_menu (role_id, menu_id, tenant_id)
SELECT 3, id, 1
FROM menu;

-- ============================================
-- 13. 为用户关联默认租户
-- ============================================
INSERT INTO
    user_tenant (user_id, tenant_id)
VALUES (1, 1)
ON DUPLICATE KEY UPDATE
    tenant_id = 1;

-- 更新用户的当前租户
UPDATE user SET current_tenant_id = 1, dept_id = 0 WHERE id = 1;

-- 开启外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- 验证清理结果
-- ============================================
SELECT 'user' as table_name, COUNT(*) as count
FROM user
UNION ALL
SELECT 'tenant', COUNT(*)
FROM tenant
UNION ALL
SELECT 'role', COUNT(*)
FROM role
UNION ALL
SELECT 'menu', COUNT(*)
FROM menu
UNION ALL
SELECT 'api', COUNT(*)
FROM api
UNION ALL
SELECT 'dept', COUNT(*)
FROM dept
UNION ALL
SELECT 'user_role', COUNT(*)
FROM user_role
UNION ALL
SELECT 'role_menu', COUNT(*)
FROM role_menu
UNION ALL
SELECT 'role_api', COUNT(*)
FROM role_api
UNION ALL
SELECT 'user_tenant', COUNT(*)
FROM user_tenant
UNION ALL
SELECT 'deptclosure', COUNT(*)
FROM deptclosure
UNION ALL
SELECT 'auditlog', COUNT(*)
FROM auditlog
UNION ALL
SELECT 'app_management', COUNT(*)
FROM app_management
UNION ALL
SELECT 'fill_data_record', COUNT(*)
FROM fill_data_record
UNION ALL
SELECT 'rule_info', COUNT(*)
FROM rule_info
UNION ALL
SELECT 'rule_version', COUNT(*)
FROM rule_version
UNION ALL
SELECT 'system_prompt', COUNT(*)
FROM system_prompt
UNION ALL
SELECT 'llm_config', COUNT(*)
FROM llm_config
UNION ALL
SELECT 'llm_provider', COUNT(*)
FROM llm_provider
UNION ALL
SELECT 'aerich', COUNT(*)
FROM aerich;