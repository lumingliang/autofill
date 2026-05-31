"""
RuleVersion Repository - 规则版本数据访问层（重构版）

严格遵循技术约束文档：
- 继承 BaseRepository 获得通用 CRUD 能力
- 自动应用租户过滤（通过 BaseRepository）
- 禁止手动传递 tenant_id 参数
- 使用 self.filter() 进行链式查询
"""
from typing import List, Optional, Tuple

from tortoise.expressions import Q

from app.models.rule_management import RuleVersion
from app.repositories.base_repository import BaseRepository


class RuleVersionRepository(BaseRepository[RuleVersion]):
    """
    规则版本 Repository

    职责：
    - 规则版本相关的数据访问操作
    - 继承 BaseRepository 获得通用 CRUD 能力
    - 自动应用租户过滤

    约束：
    - 禁止直接查询 Model，使用 self.filter() 方法
    - 禁止手动传递 tenant_id 参数，从 Ctx 获取
    """

    def __init__(self):
        super().__init__(RuleVersion)

    async def get_by_id(
        self,
        version_id: int,
        include_deleted: bool = False
    ) -> Optional[RuleVersion]:
        """
        根据ID获取版本

        Args:
            version_id: 版本ID
            include_deleted: 是否包含已删除的

        Returns:
            RuleVersion 对象或 None
        """
        query = Q(id=version_id)

        if not include_deleted:
            query &= Q(deleted=0)

        return await self.filter(query).first()

    async def get_latest(
        self,
        rule_id: int,
        include_deleted: bool = False
    ) -> Optional[RuleVersion]:
        """
        获取规则的最新版本

        Args:
            rule_id: 规则ID
            include_deleted: 是否包含已删除的

        Returns:
            RuleVersion 对象或 None
        """
        query = Q(rule_id=rule_id)

        if not include_deleted:
            query &= Q(deleted=0)

        return await self.filter(query).order_by("-version_no").first()

    async def get_by_rule_id_and_version_no(
        self,
        rule_id: int,
        version_no: int,
        include_deleted: bool = False
    ) -> Optional[RuleVersion]:
        """
        根据规则ID和版本号获取版本

        Args:
            rule_id: 规则ID
            version_no: 版本号
            include_deleted: 是否包含已删除的

        Returns:
            RuleVersion 对象或 None
        """
        query = Q(rule_id=rule_id, version_no=version_no)

        if not include_deleted:
            query &= Q(deleted=0)

        return await self.filter(query).first()

    async def list_versions(
        self,
        rule_id: int,
        include_deleted: bool = False,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[int, List[RuleVersion]]:
        """
        获取规则的版本列表

        Args:
            rule_id: 规则ID
            include_deleted: 是否包含已删除的
            page: 页码
            page_size: 每页数量

        Returns:
            (总数, 版本列表)
        """
        query = Q(rule_id=rule_id)

        if not include_deleted:
            query &= Q(deleted=0)

        total = await self.filter(query).count()
        versions = await self.filter(query).order_by("-version_no").offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return total, versions

    async def delete_by_rule_id(self, rule_id: int) -> int:
        """
        删除指定规则的所有版本（物理删除）

        Args:
            rule_id: 规则ID

        Returns:
            删除的记录数
        """
        return await self.filter(rule_id=rule_id).delete()


# 创建全局仓库实例
rule_version_repository = RuleVersionRepository()
