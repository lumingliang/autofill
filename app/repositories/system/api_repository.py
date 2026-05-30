"""
API Repository 层

提供API相关的数据访问操作，继承 BaseRepository 获得通用 CRUD 能力。
Api 模型没有 tenant_id 字段，关闭自动租户过滤。
"""

from typing import List, Optional, Set, Tuple

from app.models.admin import Api
from app.repositories.base_repository import BaseRepository
from app.repositories.system.role_api_repository import role_api_repository
from app.repositories.system.user_role_repository import user_role_repository


class ApiRepository(BaseRepository[Api]):
    """
    API Repository

    继承 BaseRepository 获得通用 CRUD 能力。
    Api 模型没有 tenant_id 字段，关闭自动租户过滤。
    """

    enable_tenant_filter = False

    def __init__(self):
        super().__init__(Api)

    async def get_all_ids(self) -> List[int]:
        return await self.model.all().values_list("id", flat=True)

    async def get_all(self) -> List[Api]:
        return await self.model.all()

    async def get_all_method_path_pairs(self) -> List[Tuple[str, str]]:
        """获取所有API的 (method, path) 列表"""
        apis = await self.model.all()
        return [(api.method, api.path) for api in apis]

    async def get_by_ids(self, api_ids: List[int]) -> List[Api]:
        if not api_ids:
            return []
        return await self.model.filter(id__in=api_ids).all()

    async def get_by_method_path(self, method: str, path: str) -> Optional[Api]:
        """根据 method 和 path 获取 API"""
        return await self.model.filter(method=method, path=path).first()

    async def get_by_codes(self, api_codes: List[str]) -> List[Api]:
        if not api_codes:
            return []
        return await self.model.filter(api_code__in=api_codes).all()

    async def get_codes_by_ids(self, api_ids: List[int]) -> List[str]:
        if not api_ids:
            return []
        rows = await self.model.filter(id__in=api_ids).values("api_code")
        return [r["api_code"] for r in rows]

    async def delete_by_ids(self, api_ids: List[int]) -> None:
        """根据ID列表删除API"""
        if not api_ids:
            return
        await self.model.filter(id__in=api_ids).delete()

    async def get_user_api_ids(self, user_id: int) -> Set[int]:
        if not user_id:
            return set()

        role_ids = await user_role_repository.get_role_ids_by_user_id(user_id)
        if not role_ids:
            return set()

        rows = await role_api_repository.batch_get_api_ids_by_role_ids(role_ids)
        api_ids: Set[int] = set()
        for rid, aids in rows.items():
            api_ids.update(aids)
        return api_ids

    async def get_user_api_ids_by_tenant(self, user_id: int, tenant_id: int) -> Set[int]:
        """
        获取用户在指定租户下的所有API ID

        Args:
            user_id: 用户ID
            tenant_id: 租户ID

        Returns:
            Set[int]: API ID集合
        """
        if not user_id or not tenant_id:
            return set()

        role_ids = await user_role_repository.get_role_ids_by_user_id(user_id)
        if not role_ids:
            return set()

        rows = await role_api_repository.batch_get_api_ids_by_role_ids(role_ids)
        api_ids: Set[int] = set()
        for rid, aids in rows.items():
            api_ids.update(aids)
        return api_ids


api_repository = ApiRepository()
