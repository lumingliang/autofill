# 菜单注册中心使用指南

## 概述

菜单注册中心是一个优雅的菜单自动初始化机制，解决了传统方式中新增菜单需要手动执行 SQL 或脚本的问题。

**核心特性：**
- ✅ **配置化定义** - 菜单以配置形式定义，代码清晰易维护
- ✅ **增量同步** - 自动检测新增、修改，无需手动干预
- ✅ **幂等性** - 多次执行不会重复创建菜单
- ✅ **自动权限分配** - 新菜单自动分配给管理员角色

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    菜单配置层 (menu_config.py)                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │ 系统管理菜单  │ │ 智能填单菜单  │ │ AI大模型菜单  │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   菜单注册中心 (menu_registry.py)               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │   注册菜单    │ │   增量同步    │ │   权限分配    │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据库层 (Menu Model)                     │
└─────────────────────────────────────────────────────────────┘
```

## 使用方法

### 1. 新增菜单

只需在 [app/core/menu_config.py](file:///Users/lu/code/code/py/autofill/app/core/menu_config.py) 中添加配置：

```python
from app.core.menu_registry import MenuConfig
from app.schemas.menus import MenuType

# 定义新菜单
my_new_menus = [
    MenuConfig(
        name="我的新模块",           # 菜单显示名称
        path="/my-module",          # 路由路径
        menu_type=MenuType.CATALOG, # 菜单类型：catalog(目录) / menu(菜单)
        icon="material-symbols:icon-name",  # 图标
        order=5,                    # 排序（数字越小越靠前）
        redirect="/my-module/page", # 重定向路径（目录类型需要）
        children=[                  # 子菜单列表
            MenuConfig(
                name="功能页面",
                path="page",
                menu_type=MenuType.MENU,
                icon="material-symbols:page",
                order=1,
                component="/my-module/page",  # 前端组件路径
                keepalive=False,
            ),
        ],
    ),
]

# 在 register_all_menus() 函数中注册
def register_all_menus():
    menu_registry.register(system_menus)
    menu_registry.register(top_menu)
    menu_registry.register(autofill_menus)
    menu_registry.register(ai_menus)
    menu_registry.register(my_new_menus)  # <-- 添加这一行
```

### 2. 重启服务

```bash
# 重启后端服务
python main.py

# 或者使用其他方式重启
supervisorctl restart autofill
```

重启后，系统会自动：
1. 读取菜单配置
2. 对比数据库中的现有菜单
3. 创建新菜单
4. 更新有变化的菜单
5. 为管理员角色分配权限

### 3. 查看日志确认

```
[INFO] [MenuRegistry] 注册了 1 个根菜单
[INFO] [MenuRegistry] 开始同步菜单到数据库...
[INFO] [MenuRegistry] 创建菜单: 我的新模块 (ID: 25)
[INFO] [MenuRegistry] 创建菜单: 功能页面 (ID: 26)
[INFO] [MenuRegistry] 为管理员角色分配了 2 个菜单权限
[INFO] [MenuRegistry] 菜单同步完成: 创建 2, 更新 0, 跳过 16
```

## MenuConfig 配置说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | str | ✅ | 菜单显示名称 |
| `path` | str | ✅ | 路由路径 |
| `menu_type` | MenuType | ✅ | `catalog`(目录) 或 `menu`(菜单) |
| `icon` | str | ❌ | 图标名称，如 `material-symbols:xxx` |
| `order` | int | ❌ | 排序，默认 0 |
| `parent_id` | int | ❌ | 父菜单ID，根菜单为 0 |
| `is_hidden` | bool | ❌ | 是否隐藏，默认 False |
| `component` | str | ✅ | 前端组件路径 |
| `keepalive` | bool | ❌ | 是否缓存，默认 False |
| `redirect` | str | ❌ | 重定向路径，目录类型建议设置 |
| `children` | List | ❌ | 子菜单列表 |

## 高级用法

### 模块化注册

如果某个功能模块需要独立管理自己的菜单，可以在模块内注册：

```python
# app/modules/my_module/menu.py
from app.core.menu_registry import menu_registry, MenuConfig

my_module_menus = [
    MenuConfig(
        name="模块菜单",
        path="/my-module",
        # ...
    ),
]

def register_my_module_menus():
    """在模块初始化时调用"""
    menu_registry.register(my_module_menus)
```

然后在应用启动时调用：

```python
# app/core/menu_config.py
from app.modules.my_module.menu import register_my_module_menus

def register_all_menus():
    # ... 其他菜单
    register_my_module_menus()  # 注册模块菜单
```

### 动态菜单

某些场景下需要动态生成菜单：

```python
async def register_dynamic_menus():
    """根据数据库配置动态生成菜单"""
    from app.models.some_model import SomeConfig

    configs = await SomeConfig.all()

    dynamic_menus = []
    for config in configs:
        dynamic_menus.append(
            MenuConfig(
                name=config.name,
                path=f"/dynamic/{config.code}",
                menu_type=MenuType.MENU,
                component=f"/dynamic/{config.code}",
            )
        )

    menu_registry.register(dynamic_menus)
```

### 条件性菜单

根据配置决定是否注册某些菜单：

```python
def register_all_menus():
    # 基础菜单
    menu_registry.register(system_menus)

    # 根据功能开关决定是否注册
    if settings.ENABLE_AUTOFILL_FEATURE:
        menu_registry.register(autofill_menus)

    if settings.ENABLE_AI_FEATURE:
        menu_registry.register(ai_menus)
```

## 工作原理

### 唯一标识

系统使用 `path:name` 作为菜单的唯一标识：

```python
@property
def unique_key(self) -> str:
    return f"{self.path}:{self.name}"
```

这意味着：
- 相同路径和名称的菜单被视为同一个菜单
- 修改其他属性（如图标、排序）会触发更新
- 修改路径或名称会创建新菜单

### 同步策略

```
配置菜单 ──┬──► 数据库中不存在 ──► 创建新菜单
           │
           └──► 数据库中已存在 ──┬──► 属性变化 ──► 更新菜单
                               │
                               └──► 无变化 ──► 跳过
```

### 权限分配

新创建的菜单会自动分配给：
- 管理员角色（ID=1）

不会重复分配已存在的权限。

## 迁移指南

### 从旧系统迁移

1. **备份现有菜单数据**
   ```bash
   mysqldump -u root -p autofill menu role_menu > menu_backup.sql
   ```

2. **将现有菜单转换为配置**
   参考 [app/core/menu_config.py](file:///Users/lu/code/code/py/autofill/app/core/menu_config.py) 的格式，将现有菜单转换为 `MenuConfig` 配置。

3. **测试同步**
   ```bash
   python test_menu_registry.py
   ```

4. **部署上线**
   确认测试通过后，部署新版本代码。

### 回滚方案

如果出现问题，可以恢复备份：

```bash
mysql -u root -p autofill < menu_backup.sql
```

## 最佳实践

1. **版本控制**
   - 菜单配置应该纳入版本控制
   - 每次新增菜单作为一个独立的 commit

2. **命名规范**
   - 菜单名称简洁明了
   - 路径使用小写和连字符，如 `/system/user-management`
   - 图标使用统一的图标库

3. **排序策略**
   - 根菜单使用 10 的倍数排序（10, 20, 30...）
   - 子菜单使用 1, 2, 3... 排序
   - 预留空间方便后续插入

4. **测试验证**
   - 新增菜单后运行测试脚本验证
   - 检查日志确认同步结果

## 故障排查

### 菜单未显示

1. 检查日志确认同步是否成功
2. 检查数据库中菜单是否存在
3. 检查管理员角色是否有权限
4. 刷新页面或重新登录

### 重复菜单

如果出现了重复菜单，可能是因为：
- 修改了菜单的 `path` 或 `name` 字段
- 手动在数据库中创建了菜单

**解决方案：**
```sql
-- 删除重复菜单（谨慎操作）
DELETE FROM menu WHERE name = '重复的菜单';
DELETE FROM role_menu WHERE menu_id NOT IN (SELECT id FROM menu);
```

### 权限未分配

检查管理员角色ID是否为1，如果不是，修改 [menu_registry.py](file:///Users/lu/code/code/py/autofill/app/core/menu_registry.py) 中的 `_assign_permissions_to_admin` 方法。

## 总结

菜单注册中心让菜单管理变得简单优雅：

- **开发新功能**：只需添加配置，重启即生效
- **修改菜单**：修改配置，重启即更新
- **团队协作**：配置化定义，易于代码审查
- **版本管理**：菜单变更纳入版本控制

不再需要手动执行 SQL 或脚本，真正实现"配置即代码"！
