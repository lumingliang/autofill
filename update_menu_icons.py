#!/usr/bin/env python3
"""更新数据库中菜单的图标配置为 Ant Design 图标名称"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = '/Users/lu/code/code/py/autofill'
sys.path.insert(0, project_root)
os.chdir(project_root)

from app.settings.config import settings

async def update_menu_icons():
    from tortoise import Tortoise
    from app.models import Menu

    # 构造数据库 URL
    db_url = f"mysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"

    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models']}
    )

    # 图标映射：将第三方图标名映射到 Ant Design 图标名
    icon_updates = {
        # AI 模型管理
        'material-symbols:model-training-outline': 'RobotOutlined',
        'material-symbols:settings-applications-outline': 'SettingOutlined',
        # 系统管理
        'carbon:gui-management': 'SettingOutlined',
        'material-symbols:person-outline-rounded': 'UserOutlined',
        'carbon:user-role': 'IdcardOutlined',
        'material-symbols:list-alt-outline': 'UnorderedListOutlined',
        'ant-design:api-outlined': 'ApiOutlined',
        'mingcute:department-line': 'ApartmentOutlined',
        'ph:clipboard-text-bold': 'FileTextOutlined',
        'material-symbols:domain': 'ClusterOutlined',
        # 智能填单
        'material-symbols:smart-toy-outline': 'RobotOutlined',
        'material-symbols:apps-outline': 'AppstoreOutlined',
        'material-symbols:web-outline': 'GlobalOutlined',
        'material-symbols:folder-outline': 'FolderOutlined',
        'material-symbols:format-list-bulleted-outline': 'UnorderedListOutlined',
        'material-symbols:description-outline': 'FileOutlined',
        'material-symbols:arrow-drop-down-circle-outline': 'DownCircleOutlined',
        'material-symbols:history-outline': 'HistoryOutlined',
    }

    print("=" * 80)
    print("更新菜单图标配置")
    print("=" * 80)

    for old_icon, new_icon in icon_updates.items():
        menus = await Menu.filter(icon=old_icon)
        for menu in menus:
            print(f"更新: {menu.name} - {old_icon} -> {new_icon}")
            menu.icon = new_icon
            await menu.save()

    print("\n" + "=" * 80)
    print("更新完成！")
    print("=" * 80)

    # 显示更新后的配置
    print("\n更新后的菜单图标配置:")
    print("=" * 80)
    menus = await Menu.all().order_by('parent_id', 'order')
    for menu in menus:
        icon_value = menu.icon if menu.icon else "(无图标)"
        print(f"【{menu.name}】图标: {icon_value}")

    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(update_menu_icons())
