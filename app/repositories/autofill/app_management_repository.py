"""
AppManagement Repository - 应用管理数据访问层

严格遵循技术约束文档：
- 继承 BaseRepository 获得通用 CRUD 能力
- 自动应用租户过滤（通过 BaseRepository）
- 禁止手动传递 tenant_id 参数
- 使用 self.filter() 进行链式查询
"""
from typing import List, Optional

from app.models.autofill import AppManagement
from app.repositories.base_repository import BaseRepository


class AppManagementRepository(BaseRepository[AppManagement]):
    """
    应用管理 Repository

    职责：
    - 应用管理相关的数据访问操作
    - 继承 BaseRepository 获得通用 CRUD 能力
    - 自动应用租户过滤

    约束：
    - 禁止直接查询 Model，使用 self.filter() 方法
    - 禁止手动传递 tenant_id 参数，从 Ctx 获取
    """

    def __init__(self):
        super().__init__(AppManagement)

    async def get_by_app_name(self, app_name: str) -> Optional[AppManagement]:
        """
        根据应用名称获取应用

        自动应用租户过滤（通过 self.filter）

        Args:
            app_name: 应用名称

        Returns:
            AppManagement 对象或 None
        """
        return await self.filter(app_name=app_name).first()

    async def check_app_name_exists(self, app_name: str, exclude_id: Optional[int] = None) -> bool:
        """
        检查应用名称是否已存在

        Args:
            app_name: 应用名称
            exclude_id: 要排除的应用ID（用于更新时排除自身）

        Returns:
            是否存在
        """
        query = self.filter(app_name=app_name)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    async def get_active_apps(self) -> List[AppManagement]:
        """
        获取所有启用的应用

        自动应用租户过滤

        Returns:
            应用列表
        """
        return await self.filter(is_active=True).all()

    async def get_by_api_key(self, api_key: str) -> Optional[AppManagement]:
        """
        根据 API Key 获取应用

        注意：API Key 是全局唯一的，不需要租户过滤

        Args:
            api_key: API Key

        Returns:
            AppManagement 对象或 None
        """
        # API Key 全局唯一，关闭租户过滤后查询
        original_filter_setting = self.enable_tenant_filter
        self.enable_tenant_filter = False
        try:
            result = await self.filter(api_key=api_key).first()
        finally:
            self.enable_tenant_filter = original_filter_setting
        return result


# 创建全局仓库实例
app_management_repository = AppManagementRepository()
