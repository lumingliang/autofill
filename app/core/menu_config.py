"""
系统菜单配置中心

所有菜单在此集中定义，应用启动时会自动同步到数据库
新增菜单只需在此文件中添加配置即可
"""

from app.core.menu_registry import MenuConfig, menu_registry
from app.schemas.menus import MenuType


# ==================== AI 模型管理菜单 ====================
ai_model_menus = [
    MenuConfig(
        name="AI 模型管理",
        path="/ai",
        menu_type=MenuType.CATALOG,
        icon="RobotOutlined",
        order=0,
        redirect="/ai/llm_config",
        children=[
            MenuConfig(
                name="模型配置",
                path="llm_config",
                menu_type=MenuType.MENU,
                icon="SettingOutlined",
                order=1,
                component="system/llm_config",
                keepalive=False,
            ),
        ],
    ),
]


# ==================== 系统管理菜单 ====================
system_menus = [
    MenuConfig(
        name="系统管理",
        path="/system",
        menu_type=MenuType.CATALOG,
        icon="SettingOutlined",
        order=99,
        redirect="/system/user",
        children=[
            MenuConfig(
                name="用户管理",
                path="user",
                menu_type=MenuType.MENU,
                icon="UserOutlined",
                order=1,
                component="system/user",
                keepalive=False,
            ),
            MenuConfig(
                name="角色管理",
                path="role",
                menu_type=MenuType.MENU,
                icon="IdcardOutlined",
                order=2,
                component="system/role",
                keepalive=False,
            ),
            MenuConfig(
                name="菜单管理",
                path="menu",
                menu_type=MenuType.MENU,
                icon="UnorderedListOutlined",
                order=3,
                component="system/menu",
                keepalive=False,
            ),
            MenuConfig(
                name="API管理",
                path="api",
                menu_type=MenuType.MENU,
                icon="ApiOutlined",
                order=4,
                component="system/api",
                keepalive=False,
            ),
            MenuConfig(
                name="部门管理",
                path="dept",
                menu_type=MenuType.MENU,
                icon="ApartmentOutlined",
                order=5,
                component="system/dept",
                keepalive=False,
            ),
            MenuConfig(
                name="审计日志",
                path="auditlog",
                menu_type=MenuType.MENU,
                icon="FileTextOutlined",
                order=6,
                component="system/auditlog",
                keepalive=False,
            ),
            MenuConfig(
                name="租户管理",
                path="tenant",
                menu_type=MenuType.MENU,
                icon="ClusterOutlined",
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
        icon="RobotOutlined",
        order=3,
        redirect="/autofill/app",
        children=[
            MenuConfig(
                name="应用管理",
                path="app",
                menu_type=MenuType.MENU,
                icon="AppstoreOutlined",
                order=1,
                component="autofill/app",
                keepalive=False,
            ),
            MenuConfig(
                name="页面管理",
                path="page",
                menu_type=MenuType.MENU,
                icon="FileOutlined",
                order=2,
                component="autofill/page",
                keepalive=False,
            ),
            MenuConfig(
                name="字段组管理",
                path="field_group",
                menu_type=MenuType.MENU,
                icon="FolderOutlined",
                order=3,
                component="autofill/field_group",
                keepalive=False,
            ),
            MenuConfig(
                name="字段管理",
                path="field_spec",
                menu_type=MenuType.MENU,
                icon="ProfileOutlined",
                order=4,
                component="autofill/field_spec",
                keepalive=False,
            ),
            MenuConfig(
                name="总结模板",
                path="template",
                menu_type=MenuType.MENU,
                icon="FileTextOutlined",
                order=5,
                component="autofill/template",
                keepalive=False,
            ),
            MenuConfig(
                name="下拉选项",
                path="dropdown",
                menu_type=MenuType.MENU,
                icon="DownCircleOutlined",
                order=6,
                component="autofill/dropdown",
                keepalive=False,
            ),
            MenuConfig(
                name="填单记录",
                path="record",
                menu_type=MenuType.MENU,
                icon="HistoryOutlined",
                order=7,
                component="autofill/record",
                keepalive=False,
            ),
            MenuConfig(
                name="测试填单",
                path="test_fill",
                menu_type=MenuType.MENU,
                icon="ExperimentOutlined",
                order=8,
                component="autofill/test_fill",
                keepalive=False,
            ),
        ],
    ),
]



def register_all_menus():
    """注册所有菜单配置"""
    menu_registry.register(ai_model_menus)
    menu_registry.register(system_menus)
    menu_registry.register(autofill_menus)
