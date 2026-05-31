"""
菜单 Service 层

处理菜单相关的业务逻辑，包括：
- 获取用户菜单
- 构建菜单树结构
- 菜单CRUD操作

约束：
- 使用 @atomic 装饰器控制事务
- 不重复判断权限（中间件已完成认证）
- 租户信息从 Ctx 获取
- 不直接查询 Model 层，通过 Repository 层访问数据
"""

from typing import Any, Dict, List, Tuple

from tortoise.transactions import atomic

from app.core.ctx import Ctx
from app.models.admin import Menu
from app.repositories import menu_repository


class MenuService:
    """
    菜单 Service

    职责：
    - 处理菜单相关的业务逻辑
    - 调用 Repository 层进行数据操作

    约束：
    - 不直接操作数据库，通过 Repository 层访问数据
    - 不处理 HTTP 请求/响应
    """

    async def get_user_menus(self, user_id: int, is_superuser: bool) -> List[dict]:
        """
        获取用户菜单

        Args:
            user_id: 用户ID
            is_superuser: 是否为超级管理员

        Returns:
            菜单树结构列表
        """
        if is_superuser:
            menus = await menu_repository.get_all()
        else:
            current_tenant_id = Ctx.get_effective_tenant_id()
            if not current_tenant_id:
                return []

            menu_ids = await menu_repository.get_user_menu_ids(user_id)
            if not menu_ids:
                return []

            all_menu_ids = await self._get_all_parent_menu_ids(menu_ids)
            menus = await menu_repository.get_by_ids(list(all_menu_ids))

        return await self._build_menu_tree(menus)

    async def list_with_permission(
        self,
        user_id: int,
        is_superuser: bool,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[int, List[dict]]:
        """
        根据用户权限获取菜单列表（返回树形结构）

        Args:
            user_id: 用户ID
            is_superuser: 是否为超级管理员
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[int, List[dict]]: (总数, 菜单树列表)
        """
        if is_superuser:
            menus = await menu_repository.filter().order_by("order").all()
        else:
            menu_ids = await menu_repository.get_user_menu_ids(user_id)
            if not menu_ids:
                return 0, []

            all_menu_ids = await self._get_all_parent_menu_ids(menu_ids)
            menus = await menu_repository.get_by_ids(list(all_menu_ids))

        total = len(menus)
        menu_tree = await self._build_menu_tree(menus)
        return total, menu_tree

    async def get_by_id(self, menu_id: int) -> Dict[str, Any]:
        """
        根据ID获取菜单

        Args:
            menu_id: 菜单ID

        Returns:
            Dict[str, Any]: 菜单字典
        """
        menu = await menu_repository.get_by_id(menu_id)
        return await menu.to_dict()

    @atomic()
    async def create(self, menu_in: Dict[str, Any]) -> None:
        """
        创建菜单

        Args:
            menu_in: 菜单创建数据
        """
        await menu_repository.create(menu_in)

    @atomic()
    async def update(self, menu_id: int, menu_in: Dict[str, Any]) -> None:
        """
        更新菜单

        Args:
            menu_id: 菜单ID
            menu_in: 菜单更新数据
        """
        await menu_repository.update(menu_id, menu_in)

    @atomic()
    async def delete(self, menu_id: int) -> None:
        """
        删除菜单

        Args:
            menu_id: 菜单ID

        Raises:
            ValueError: 如果菜单有子菜单
        """
        children_count = await menu_repository.get_children_count(menu_id)
        if children_count > 0:
            raise ValueError("Cannot delete a menu with child menus")
        await menu_repository.delete(menu_id)

    async def _get_all_parent_menu_ids(self, menu_ids: set) -> set:
        """递归获取所有父菜单ID"""
        if not menu_ids:
            return set()

        all_menu_ids = set(menu_ids)
        current_ids = set(menu_ids)

        while current_ids:
            menus = await menu_repository.get_by_ids(list(current_ids))
            parent_ids = {menu.parent_id for menu in menus if menu.parent_id != 0}

            new_parent_ids = parent_ids - all_menu_ids
            if not new_parent_ids:
                break

            all_menu_ids.update(new_parent_ids)
            current_ids = new_parent_ids

        return all_menu_ids

    async def _build_menu_tree(self, menus: List[Menu]) -> List[dict]:
        """构建菜单树结构"""
        if not menus:
            return []

        menu_map = {menu.id: await menu.to_dict() for menu in menus}

        root_menus = [menu_map[menu.id] for menu in menus if menu.parent_id == 0]

        def build_children(parent_id: int) -> List[dict]:
            children = []
            for menu in menus:
                if menu.parent_id == parent_id:
                    menu_dict = menu_map[menu.id]
                    menu_dict["children"] = build_children(menu.id)
                    children.append(menu_dict)
            children.sort(key=lambda x: x.get("order", 0))
            return children

        result = []
        for root_menu in root_menus:
            root_menu["children"] = build_children(root_menu["id"])
            result.append(root_menu)

        result.sort(key=lambda x: x.get("order", 0))
        return result


menu_service = MenuService()
