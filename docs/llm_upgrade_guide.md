# LLM 代理功能升级指南

## 概述

本文档指导如何将 LLM 代理功能升级添加到已部署的系统中。

## 升级步骤

### 1. 数据库迁移

数据库表 `llm_config` 已通过迁移文件创建，执行数据库升级：

```bash
# 进入项目目录
cd /Users/lu/code/code/py/autofill

# 执行数据库迁移
aerich upgrade
```

### 2. 添加菜单和API权限

对于新安装的系统，菜单和API会自动初始化。对于已运行的系统，需要手动添加：

#### 方法1：通过后端管理界面

1. 登录系统，进入 "系统管理" -> "菜单管理"
2. 点击 "新建根菜单"，创建以下菜单：
   - 菜单类型：目录
   - 菜单名称：AI大模型
   - 路由路径：/ai
   - 组件：Layout
   - 图标：material-symbols:psychology-outline
   - 排序：4
   - 重定向：/ai/llm-config

3. 在 "AI大模型" 目录下创建子菜单：
   - 菜单类型：菜单
   - 菜单名称：LLM配置
   - 路由路径：llm-config
   - 组件：/ai/llm-config
   - 图标：material-symbols:model-training-outline
   - 排序：1

4. 进入 "系统管理" -> "API管理"
5. 点击 "刷新API列表" 按钮

6. 进入 "系统管理" -> "角色管理"
7. 为管理员角色分配新的菜单和API权限

#### 方法2：使用自动化脚本（推荐）

项目提供了自动化脚本来添加菜单：

```bash
# 进入项目目录
cd /Users/lu/code/code/py/autofill

# 运行菜单添加脚本
python add_ai_menu.py
```

脚本会自动：
1. 检查并创建 AI大模型 目录菜单
2. 检查并创建 LLM配置 子菜单
3. 为管理员角色分配菜单权限

#### 方法3：通过 SQL 脚本

如果自动化脚本无法运行，可以使用 SQL 脚本：

```bash
# 执行 SQL 脚本
mysql -u root -p autofill < add_ai_menu.sql
```

或者手动执行 SQL：

```sql
-- 添加 AI大模型 目录菜单
INSERT INTO menu (
    menu_type, name, path, `order`, parent_id, icon,
    is_hidden, component, keepalive, redirect, created_at, updated_at
) VALUES (
    'catalog', 'AI大模型', '/ai', 4, 0, 'material-symbols:psychology-outline',
    0, 'Layout', 0, '/ai/llm-config', NOW(), NOW()
);

-- 获取刚插入的目录菜单ID
SET @ai_menu_id = LAST_INSERT_ID();

-- 添加 LLM配置 子菜单
INSERT INTO menu (
    menu_type, name, path, `order`, parent_id, icon,
    is_hidden, component, keepalive, created_at, updated_at
) VALUES (
    'menu', 'LLM配置', 'llm-config', 1, @ai_menu_id, 'material-symbols:model-training-outline',
    0, '/ai/llm-config', 0, NOW(), NOW()
);

-- 为管理员角色分配菜单权限（假设管理员角色ID为1）
SET @llm_config_menu_id = LAST_INSERT_ID();
INSERT INTO role_menu (role_id, menu_id, created_at, updated_at) VALUES
    (1, @ai_menu_id, NOW(), NOW()),
    (1, @llm_config_menu_id, NOW(), NOW());
```

### 3. 重启服务

```bash
# 重启后端服务
python main.py

# 或如果使用 supervisor
supervisorctl restart autofill

# 前端重新编译（如有需要）
cd frontend
npm run build
```

## 验证

### 1. 检查菜单

登录系统后，应该能在左侧菜单看到：
- AI大模型
  - LLM配置

### 2. 检查 API

访问 API 文档页面：`http://localhost:8000/docs`

应该能看到以下新 API：
- `GET /api/v1/ai/llm_config/list`
- `GET /api/v1/ai/llm_config/get`
- `POST /api/v1/ai/llm_config/create`
- `POST /api/v1/ai/llm_config/update`
- `DELETE /api/v1/ai/llm_config/delete`
- `GET /api/v1/ai/llm_config/providers`
- `GET /api/v1/ai/llm_config/default`
- `POST /api/llm/proxy`
- `GET /api/llm/proxy/health`

### 3. 测试 LLM 配置页面

1. 点击 "AI大模型" -> "LLM配置"
2. 点击 "新增配置" 按钮
3. 填写配置信息：
   - 配置名称：测试配置
   - 模型提供商：openai
   - 模型名称：gpt-3.5-turbo
   - API密钥：your-api-key
4. 保存配置

### 4. 测试 LLM 代理接口

使用 curl 测试：

```bash
curl -X POST http://localhost:8000/api/llm/proxy \
  -H "Authorization: Bearer your_app_key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "客户说：我要投诉你们的服务",
    "function_schema": {
      "type": "function",
      "function": {
        "name": "classify_scene",
        "description": "识别业务场景",
        "parameters": {
          "type": "object",
          "properties": {
            "scene_name": {
              "type": "string",
              "enum": ["投诉处理", "业务咨询"]
            }
          },
          "required": ["scene_name"]
        }
      }
    }
  }'
```

## 故障排查

### 问题1：菜单不显示

**原因**：菜单未正确添加到数据库

**解决**：
1. 检查数据库中是否存在 AI大模型 菜单
2. 检查当前用户角色是否有菜单权限
3. 重新登录系统刷新权限

### 问题2：API 403 错误

**原因**：API 权限未分配

**解决**：
1. 进入 "系统管理" -> "API管理"
2. 点击 "刷新API列表"
3. 进入 "系统管理" -> "角色管理"
4. 为角色分配新的 API 权限

### 问题3：页面空白

**原因**：前端组件路径错误

**解决**：
1. 检查文件是否存在：`frontend/src/views/ai/llm-config/index.vue`
2. 检查浏览器控制台是否有错误
3. 重新编译前端

### 问题4：LLM 调用失败

**原因**：配置错误或 LiteLLM 问题

**解决**：
1. 检查 LLM 配置是否正确
2. 查看后端日志
3. 使用健康检查接口测试：
   ```bash
   curl http://localhost:8000/api/llm/proxy/health \
     -H "Authorization: Bearer your_app_key"
   ```

## 新增文件清单

### 后端文件
- `app/models/llm_config.py` - LLM配置模型
- `app/schemas/llm_config.py` - LLM配置Schema
- `app/controllers/llm_config.py` - LLM配置控制器
- `app/services/llm_proxy_service.py` - LLM代理服务
- `app/api/v1/llm_config/` - LLM配置API
- `app/api/llm_proxy.py` - LLM代理公开API

### 前端文件
- `frontend/src/views/ai/llm-config/index.vue` - LLM配置页面

### 文档文件
- `docs/llm_proxy_api.md` - API文档
- `docs/architecture.md` - 架构设计文档
- `docs/llm_upgrade_guide.md` - 本升级指南

## 配置说明

### LLM 配置字段

| 字段 | 说明 | 示例 |
|------|------|------|
| name | 配置名称 | OpenAI GPT-4 |
| model_provider | 模型提供商 | openai |
| model_name | 模型名称 | gpt-4 |
| api_key | API密钥 | sk-... |
| api_base | API基础URL | https://api.openai.com/v1 |
| temperature | 温度参数 | 0.7 |
| max_tokens | 最大Token数 | 2048 |
| top_p | Top P采样 | 1.0 |
| is_active | 是否启用 | true |
| is_default | 是否为默认配置 | true |
| tenant_id | 租户ID | null(全局) |

### 支持的模型提供商

- openai - OpenAI (GPT系列)
- azure - Azure OpenAI
- anthropic - Anthropic (Claude)
- google - Google (Gemini)
- baidu - 百度文心
- alibaba - 阿里通义
- zhipu - 智谱AI
- deepseek - DeepSeek
- moonshot - Moonshot
- qianfan - 千帆大模型
- xunfei - 讯飞星火
- minimax - MiniMax

## 注意事项

1. **API Key 安全**：API Key 只保存在后端，不会返回给前端
2. **多租户隔离**：全局配置(tenant_id=null)所有租户可见，租户配置仅该租户可见
3. **默认配置**：每个租户可以有独立的默认配置，优先使用租户默认配置
4. **Redis 缓存**：LLM 配置会缓存 1 小时，修改配置后可能需要等待缓存过期

## 新安装系统

对于新安装的系统，以下操作会自动完成：

1. **数据库表创建**：通过 aerich 迁移自动创建 `llm_config` 表
2. **菜单初始化**：`init_menus()` 函数会自动创建 AI大模型 菜单
3. **API注册**：`init_apis()` 函数会自动注册所有 API
4. **权限分配**：`init_roles()` 函数会自动为管理员角色分配权限

只需执行：
```bash
aerich upgrade
python main.py
```

然后登录系统即可使用。
