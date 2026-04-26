import asyncio
from tortoise import Tortoise
from app.settings.config import settings
from app.models.admin import Menu, Role
from app.core.relation import RelationQuery


async def assign_autofill_menu():
    await Tortoise.init(config=settings.TORTOISE_ORM)

    # 获取智能填单菜单
    autofill_menu = await Menu.filter(name='智能填单').first()
    if not autofill_menu:
        print('智能填单菜单不存在')
        await Tortoise.close_connections()
        return

    # 获取子菜单
    children = await Menu.filter(parent_id=autofill_menu.id).all()
    menu_ids = [autofill_menu.id] + [m.id for m in children]

    # 获取管理员角色
    admin_role = await Role.filter(name='管理员').first()
    if not admin_role:
        print('管理员角色不存在')
        await Tortoise.close_connections()
        return

    # 分配菜单给管理员
    pairs = [(admin_role.id, mid) for mid in menu_ids]
    await RelationQuery.batch_add_role_menus(pairs)
    print(f'已将 {len(menu_ids)} 个菜单分配给管理员角色')

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(assign_autofill_menu())
