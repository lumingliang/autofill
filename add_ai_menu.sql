-- 添加 AI大模型 菜单和 LLM配置 子菜单
-- 执行方式: mysql -u root -p autofill < add_ai_menu.sql

-- 检查并添加 AI大模型 目录菜单
SET
    @ai_menu_exists = (
        SELECT COUNT(*)
        FROM menu
        WHERE
            name = 'AI大模型'
    );

SET @ai_menu_id = 0;

-- 如果不存在，则创建 AI大模型 目录菜单
INSERT IGNORE INTO
    menu (
        menu_type,
        name,
        path,
        `order`,
        parent_id,
        icon,
        is_hidden,
        component,
        keepalive,
        redirect,
        created_at,
        updated_at
    )
VALUES (
        'catalog',
        'AI大模型',
        '/ai',
        4,
        0,
        'material-symbols:psychology-outline',
        0,
        'Layout',
        0,
        '/ai/llm-config',
        NOW(),
        NOW()
    );

-- 获取 AI大模型 菜单ID
SET @ai_menu_id = LAST_INSERT_ID();

-- 如果菜单已存在，获取其ID
IF @ai_menu_id = 0 THEN
SET
    @ai_menu_id = (
        SELECT id
        FROM menu
        WHERE
            name = 'AI大模型'
        LIMIT 1
    );

END IF;

-- 检查并添加 LLM配置 子菜单
SET
    @llm_menu_exists = (
        SELECT COUNT(*)
        FROM menu
        WHERE
            name = 'LLM配置'
    );

-- 如果不存在，则创建 LLM配置 子菜单
INSERT IGNORE INTO
    menu (
        menu_type,
        name,
        path,
        `order`,
        parent_id,
        icon,
        is_hidden,
        component,
        keepalive,
        created_at,
        updated_at
    )
VALUES (
        'menu',
        'LLM配置',
        'llm-config',
        1,
        @ai_menu_id,
        'material-symbols:model-training-outline',
        0,
        '/ai/llm-config',
        0,
        NOW(),
        NOW()
    );

-- 获取 LLM配置 菜单ID
SET @llm_config_menu_id = LAST_INSERT_ID();

-- 如果菜单已存在，获取其ID
IF @llm_config_menu_id = 0 THEN
SET
    @llm_config_menu_id = (
        SELECT id
        FROM menu
        WHERE
            name = 'LLM配置'
        LIMIT 1
    );

END IF;

-- 为管理员角色分配菜单权限（如果存在角色ID为1的管理员角色）
SET @admin_role_exists = ( SELECT COUNT(*) FROM role WHERE id = 1 );

IF @admin_role_exists > 0 THEN
-- 为管理员角色分配 AI大模型 菜单权限
INSERT IGNORE INTO
    role_menu (
        role_id,
        menu_id,
        created_at,
        updated_at
    )
VALUES (1, @ai_menu_id, NOW(), NOW());

-- 为管理员角色分配 LLM配置 菜单权限
INSERT IGNORE INTO
    role_menu (
        role_id,
        menu_id,
        created_at,
        updated_at
    )
VALUES (
        1,
        @llm_config_menu_id,
        NOW(),
        NOW()
    );

END IF;

-- 输出结果
SELECT 'AI大模型菜单添加完成' AS result;

SELECT * FROM menu WHERE name IN ('AI大模型', 'LLM配置');