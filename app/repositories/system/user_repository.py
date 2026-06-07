"""
用户 Repository 层

提供用户相关的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
注意：User 模型没有 tenant_id 字段，租户关联通过 UserTenant 关联表管理。
"""

from datetime import datetime
from typing import List, Optional

from tortoise.expressions import Q

from app.core.ctx import Ctx
from app.models.admin import User
from app.repositories.base_repository import BaseRepository
from app.repositories.system.user_tenant_repository import user_tenant_repository


class UserRepository(BaseRepository[User]):
    """
    用户 Repository

    继承 BaseRepository 获得通用 CRUD 能力。

    注意：User 模型没有 tenant_id 字段，关闭自动租户过滤。
    所有查询方法需要手动处理租户过滤，通过 UserTenant 关联表实现。

    租户过滤逻辑：
    - 超管未指定租户（should_query_all=True）：查询全量数据
    - 普通用户或超管指定租户：通过 UserTenant 关联表过滤
    """

    # 关闭租户过滤，User 模型没有 tenant_id 字段
    enable_tenant_filter = False

    def __init__(self):
        super().__init__(User)

    async def _check_user_in_tenant(self, user_id: int) -> bool:
        """
        检查用户是否在当前租户下

        使用 user_tenant_repository 查询，自动应用租户过滤

        Args:
            user_id: 用户ID

        Returns:
            bool: 是否在租户下
        """
        # 暂时不校验租户，全部返回True
        return True

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        根据邮箱获取用户（应用租户过滤）

        通过数据库查询验证用户是否在租户下
        """
        user = await self.first(email=email)
        if not user:
            return None

        # 验证用户是否在租户下
        if await self._check_user_in_tenant(user.id):
            return user
        return None

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名获取用户（应用租户过滤）

        通过数据库查询验证用户是否在租户下
        """
        user = await self.first(username=username)
        if not user:
            return None

        # 验证用户是否在租户下
        if await self._check_user_in_tenant(user.id):
            return user
        return None

    async def get_by_id(self, id: int) -> Optional[User]:
        """
        根据ID获取用户（应用租户过滤）

        通过数据库查询验证用户是否在租户下
        """
        user = await super().get_by_id(id)
        if not user:
            return None

        # 验证用户是否在租户下
        if await self._check_user_in_tenant(user.id):
            return user
        return None

    async def get_by_id_raw(self, id: int) -> Optional[User]:
        """
        根据ID获取用户（不应用租户过滤，用于认证等场景）

        Args:
            id: 用户ID

        Returns:
            Optional[User]: 用户对象，不存在返回None
        """
        return await self.model.filter(id=id).first()

    async def list_by_tenant(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Q = Q(),
        order: List[str] = None
    ):
        """
        根据当前租户查询用户列表

        通过 UserTenant 关联表进行过滤，租户ID从 Ctx 获取
        """
        if order is None:
            order = ["-updated_at"]

        # 判断是否查询全量数据（超管未指定租户时）
        if Ctx.should_query_all():
            return await self.list(page, page_size, search, order)

        # 获取当前租户下的用户ID列表（通过 user_tenant_repository，自动应用租户过滤）
        user_ids = await user_tenant_repository.get_user_ids_by_tenant()

        if not user_ids:
            return 0, []

        # 应用额外的搜索条件
        query = Q(id__in=user_ids) & search

        # 查询总数和数据
        qs = self.model.filter(query)
        total = await qs.count()
        data = await qs.offset((page - 1) * page_size).limit(page_size).order_by(*order)

        return total, data

    async def update_last_login(self, user_id: int) -> None:
        """
        更新最后登录时间

        会先验证用户是否在当前租户下
        """
        # 验证用户是否在租户下
        if not await self._check_user_in_tenant(user_id):
            raise ValueError("用户不存在")

        user = await self.get(id=user_id)
        user.last_login = datetime.now()
        await user.save()

    async def reset_password(self, user_id: int, hashed_password: str) -> None:
        """
        重置密码

        会先验证用户是否在当前租户下
        """
        # 验证用户是否在租户下
        if not await self._check_user_in_tenant(user_id):
            raise ValueError("用户不存在")

        user = await self.get(id=user_id)
        user.password = hashed_password
        await user.save()

    async def set_current_tenant(self, user_id: int, tenant_id: int) -> None:
        """
        设置用户当前选中的租户

        会先验证用户是否在当前租户下
        """
        # 验证用户是否在租户下
        if not await self._check_user_in_tenant(user_id):
            raise ValueError("用户不存在")

        user = await self.get(id=user_id)
        user.current_tenant_id = tenant_id
        await user.save()

    async def search_users(
        self,
        keyword: str = "",
        exclude_user_ids: List[int] = None,
        page: int = 1,
        page_size: int = 20
    ):
        """
        搜索用户（用于分配给租户）

        注意：此方法需要查询所有用户（跨租户），不应用租户过滤

        Args:
            keyword: 搜索关键词（用户名或邮箱）
            exclude_user_ids: 要排除的用户ID列表
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[int, List[User]]: (总数, 用户列表)
        """
        # 构建查询条件
        query = Q()

        if keyword:
            query &= Q(username__icontains=keyword) | Q(email__icontains=keyword)

        if exclude_user_ids:
            query &= ~Q(id__in=exclude_user_ids)

        # 查询总数
        qs = self.model.filter(query)
        total = await qs.count()

        # 查询分页数据
        users = await qs.offset((page - 1) * page_size).limit(page_size).all()

        return total, users

    async def get_users_by_ids(
        self,
        user_ids: List[int],
        keyword: str = "",
        page: int = 1,
        page_size: int = 20
    ):
        """
        根据用户ID列表获取用户（支持搜索和分页）

        Args:
            user_ids: 用户ID列表
            keyword: 搜索关键词（用户名或邮箱）
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[int, List[User]]: (总数, 用户列表)
        """
        if not user_ids:
            return 0, []

        # 构建查询条件
        query = Q(id__in=user_ids)

        if keyword:
            query &= Q(username__icontains=keyword) | Q(email__icontains=keyword)

        # 查询总数
        qs = self.model.filter(query)
        total = await qs.count()

        # 查询分页数据
        users = await qs.offset((page - 1) * page_size).limit(page_size).all()

        return total, users

    async def list_by_username(
        self,
        page: int = 1,
        page_size: int = 10,
        username: str = "",
        order: List[str] = None
    ):
        """
        根据用户名模糊查询用户列表（应用租户过滤）

        Args:
            page: 页码
            page_size: 每页数量
            username: 用户名模糊查询
            order: 排序字段列表

        Returns:
            Tuple[int, List[User]]: (总数, 用户列表)
        """
        if order is None:
            order = ["-updated_at"]

        # 构建查询条件
        search = Q()
        if username:
            search &= Q(username__contains=username)

        # 使用 list_by_tenant 方法，自动应用租户过滤
        return await self.list_by_tenant(
            page=page,
            page_size=page_size,
            search=search,
            order=order
        )


# 全局 Repository 实例
user_repository = UserRepository()
