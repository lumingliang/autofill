"""
系统菜单配置中心

所有菜单在此集中定义，应用启动时会自动同步到数据库
新增菜单只需在此文件中添加配置即可
"""

from app.core.menu_registry import MenuConfig, menu_registry
from app.schemas.menus import MenuType


# ==================== 系统管理菜单 ====================
system_menus = [
    MenuConfig(
        name="系统管理",
        path="/system",
        menu_type=MenuType.CATALOG,
        icon="carbon:gui-management",
        order=1,
        redirect="/system/user",
        children=[
            MenuConfig(
                name="用户管理",
                path="user",
                menu_type=MenuType.MENU,
                icon="material-symbols:person-outline-rounded",
                order=1,
                component="system/user",
                keepalive=False,
            ),
            MenuConfig(
                name="角色管理",
                path="role",
                menu_type=MenuType.MENU,
                icon="carbon:user-role",
                order=2,
                component="system/role",
                keepalive=False,
            ),
            MenuConfig(
                name="菜单管理",
                path="menu",
                menu_type=MenuType.MENU,
                icon="material-symbols:list-alt-outline",
                order=3,
                component="system/menu",
                keepalive=False,
            ),
            MenuConfig(
                name="API管理",
                path="api",
                menu_type=MenuType.MENU,
                icon="ant-design:api-outlined",
                order=4,
                component="system/api",
                keepalive=False,
            ),
            MenuConfig(
                name="部门管理",
                path="dept",
                menu_type=MenuType.MENU,
                icon="mingcute:department-line",
                order=5,
                component="system/dept",
                keepalive=False,
            ),
            MenuConfig(
                name="审计日志",
                path="auditlog",
                menu_type=MenuType.MENU,
                icon="ph:clipboard-text-bold",
                order=6,
                component="system/auditlog",
                keepalive=False,
            ),
            MenuConfig(
                name="租户管理",
                path="tenant",
                menu_type=MenuType.MENU,
                icon="material-symbols:domain",
                order=7,
                component="system/tenant",
                keepalive=False,
            ),
        ],
    ),
]



# ==================== 智能填单菜单 ====================
autofill_menus = [
    MenuConfig(
        name="智能填单",
        path="/autofill",
        menu_type=MenuType.CATALOG,
        icon="material-symbols:smart-toy-outline",
        order=3,
        redirect="/autofill/app",
        children=[
            MenuConfig(
                name="应用管理",
                path="app",
                menu_type=MenuType.MENU,
                icon="material-symbols:apps-outline",
                order=1,
                component="autofill/app",
                keepalive=False,
            ),
            MenuConfig(
                name="总结模板",
                path="template",
                menu_type=MenuType.MENU,
                icon="material-symbols:description-outline",
                order=2,
                component="autofill/template",
                keepalive=False,
            ),
            MenuConfig(
                name="下拉选项",
                path="dropdown",
                menu_type=MenuType.MENU,
                icon="material-symbols:arrow-drop-down-circle-outline",
                order=3,
                component="autofill/dropdown",
                keepalive=False,
            ),
            MenuConfig(
                name="填单记录",
                path="record",
                menu_type=MenuType.MENU,
                icon="material-symbols:history-outline",
                order=4,
                component="autofill/record",
                keepalive=False,
            ),
        ],
    ),
]



def register_all_menus():
    """注册所有菜单配置"""
    menu_registry.register(system_menus)
    menu_registry.register(autofill_menus)
