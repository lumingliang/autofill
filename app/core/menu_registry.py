"""
菜单注册中心 - 优雅的菜单自动初始化机制

使用方式：
1. 在模块中定义菜单配置
2. 在应用启动时自动注册
3. 系统会自动对比数据库，进行增量更新

示例：
    from app.core.menu_registry import menu_registry, MenuConfig

    # 定义菜单
    ai_menus = [
        MenuConfig(
            name="AI大模型",
            path="/ai",
            menu_type=MenuType.CATALOG,
            icon="material-symbols:psychology-outline",
            order=4,
            redirect="/ai/llm-config",
            children=[
                MenuConfig(
                    name="LLM配置",
                    path="llm-config",
                    menu_type=MenuType.MENU,
                    icon="material-symbols:model-training-outline",
                    order=1,
                    component="/ai/llm-config",
                ),
            ]
        ),
    ]

    # 注册菜单
    menu_registry.register(ai_menus)
"""

from dataclasses import dataclass, field
from typing import List, Optional

from app.core.relation import RelationQuery
from app.log import logger
from app.models.admin import Menu, Role, RoleMenu
from app.schemas.menus import MenuType


@dataclass
class MenuConfig:
    """菜单配置数据类"""
    name: str
    path: str
    menu_type: MenuType = MenuType.CATALOG
    icon: str = ""
    order: int = 0
    parent_id: int = 0
    is_hidden: bool = False
    component: str = "Layout"
    keepalive: bool = False
    redirect: str = ""
    children: List["MenuConfig"] = field(default_factory=list)

    # 唯一标识字段，用于判断菜单是否已存在
    @property
    def unique_key(self) -> str:
        """生成唯一标识：路径+名称"""
        return f"{self.path}:{self.name}"


class MenuRegistry:
    """菜单注册中心"""

    def __init__(self):
        self._menu_configs: List[MenuConfig] = []

    def register(self, menus: List[MenuConfig]):
        """注册菜单配置"""
        self._menu_configs.extend(menus)
        logger.info(f"[MenuRegistry] 注册了 {len(menus)} 个根菜单")

    def clear(self):
        """清空注册表（主要用于测试）"""
        self._menu_configs.clear()

    async def sync_to_database(self):
        """
        同步菜单配置到数据库
        实现增量更新：新增、更新、禁用（不删除）
        """
        logger.info("[MenuRegistry] 开始同步菜单到数据库...")

        # 获取数据库中所有现有菜单
        existing_menus = await Menu.all()
        existing_map = {f"{m.path}:{m.name}": m for m in existing_menus}

        # 记录需要分配给管理员角色的新菜单ID
        new_menu_ids = []
        created_count = 0
        updated_count = 0
        skipped_count = 0

        # 递归处理菜单
        async def process_menu(config: MenuConfig, parent_id: int = 0):
            nonlocal created_count, updated_count, skipped_count

            key = config.unique_key
            config.parent_id = parent_id

            if key in existing_map:
                # 菜单已存在，检查是否需要更新
                existing = existing_map[key]
                needs_update = False

                # 检查各字段是否需要更新
                if existing.icon != config.icon:
                    existing.icon = config.icon
                    needs_update = True
                if existing.order != config.order:
                    existing.order = config.order
                    needs_update = True
                if existing.component != config.component:
                    existing.component = config.component
                    needs_update = True
                if existing.redirect != config.redirect:
                    existing.redirect = config.redirect
                    needs_update = True
                if existing.is_hidden != config.is_hidden:
                    existing.is_hidden = config.is_hidden
                    needs_update = True

                if needs_update:
                    await existing.save()
                    updated_count += 1
                    logger.debug(f"[MenuRegistry] 更新菜单: {config.name}")
                else:
                    skipped_count += 1

                menu_id = existing.id
            else:
                # 创建新菜单
                new_menu = await Menu.create(
                    name=config.name,
                    path=config.path,
                    menu_type=config.menu_type,
                    icon=config.icon,
                    order=config.order,
                    parent_id=parent_id,
                    is_hidden=config.is_hidden,
                    component=config.component,
                    keepalive=config.keepalive,
                    redirect=config.redirect,
                )
                menu_id = new_menu.id
                created_count += 1
                new_menu_ids.append(menu_id)
                logger.info(f"[MenuRegistry] 创建菜单: {config.name} (ID: {menu_id})")

            # 递归处理子菜单
            for child in config.children:
                await process_menu(child, menu_id)

            return menu_id

        # 处理所有注册的根菜单
        for menu_config in self._menu_configs:
            await process_menu(menu_config)

        # 为新菜单分配权限给管理员角色
        if new_menu_ids:
            await self._assign_permissions_to_admin(new_menu_ids)

        logger.info(
            f"[MenuRegistry] 菜单同步完成: "
            f"创建 {created_count}, 更新 {updated_count}, 跳过 {skipped_count}"
        )

    async def _assign_permissions_to_admin(self, menu_ids: List[int]):
        """为新菜单分配权限给管理员角色"""
        # 查找管理员角色（假设ID为1，或者是超级管理员）
        admin_role = await Role.filter(id=1).first()
        if not admin_role:
            logger.warning("[MenuRegistry] 未找到管理员角色，跳过权限分配")
            return

        # 检查哪些权限还未分配
        existing_permissions = await RoleMenu.filter(
            role_id=admin_role.id,
            menu_id__in=menu_ids
        ).values_list("menu_id", flat=True)

        new_permissions = [mid for mid in menu_ids if mid not in existing_permissions]

        if new_permissions:
            pairs = [(admin_role.id, mid) for mid in new_permissions]
            await RelationQuery.batch_add_role_menus(pairs)
            logger.info(
                f"[MenuRegistry] 为管理员角色分配了 {len(new_permissions)} 个菜单权限"
            )


# 全局菜单注册中心实例
menu_registry = MenuRegistry()
