import asyncio
from tortoise import Tortoise
from app.settings.config import settings
from app.models.admin import Menu
from app.schemas.menus import MenuType


async def create_autofill_menus():
    await Tortoise.init(config=settings.TORTOISE_ORM)

    # 检查是否已存在
    existing = await Menu.filter(name='智能填单').first()
    if existing:
        print('智能填单菜单已存在')
        await Tortoise.close_connections()
        return

    # 创建智能填单菜单
    autofill_menu = await Menu.create(
        menu_type=MenuType.CATALOG,
        name='智能填单',
        path='/autofill',
        order=3,
        parent_id=0,
        icon='material-symbols:smart-toy-outline',
        is_hidden=False,
        component='Layout',
        keepalive=False,
        redirect='/autofill/app',
    )

    autofill_children = [
        Menu(
            menu_type=MenuType.MENU,
            name='应用管理',
            path='app',
            order=1,
            parent_id=autofill_menu.id,
            icon='material-symbols:apps-outline',
            is_hidden=False,
            component='/autofill/app',
            keepalive=False,
        ),
        Menu(
            menu_type=MenuType.MENU,
            name='总结模板',
            path='template',
            order=2,
            parent_id=autofill_menu.id,
            icon='material-symbols:description-outline',
            is_hidden=False,
            component='/autofill/template',
            keepalive=False,
        ),
        Menu(
            menu_type=MenuType.MENU,
            name='下拉选项',
            path='dropdown',
            order=3,
            parent_id=autofill_menu.id,
            icon='material-symbols:arrow-drop-down-circle-outline',
            is_hidden=False,
            component='/autofill/dropdown',
            keepalive=False,
        ),
        Menu(
            menu_type=MenuType.MENU,
            name='填单记录',
            path='record',
            order=4,
            parent_id=autofill_menu.id,
            icon='material-symbols:history-outline',
            is_hidden=False,
            component='/autofill/record',
            keepalive=False,
        ),
    ]
    await Menu.bulk_create(autofill_children)
    print('智能填单菜单创建成功')

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(create_autofill_menus())
