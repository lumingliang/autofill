"""
RuleVersion Repository - 规则版本数据访问层
"""
from typing import List, Optional, Tuple

from app.models.rule_management import RuleVersion
from app.core.tenant import TenantContext
from .rule_info_repository import rule_info_repository


class RuleVersionRepository:
    """规则版本仓库"""

    def _apply_tenant_filter(self, query):
        """
        应用租户过滤条件

        使用全局统一的 TenantContext.build_query_filter 方法

        Args:
            query: 查询对象
        """
        filter_dict = TenantContext.build_query_filter(0, 'tenant_id')
        if filter_dict:
            query = query.filter(**filter_dict)
        return query

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
        query = RuleVersion.filter(id=version_id)

        query = self._apply_tenant_filter(query)

        if not include_deleted:
            query = query.filter(deleted=0)

        return await query.first()

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
        query = RuleVersion.filter(rule_id=rule_id)

        query = self._apply_tenant_filter(query)

        if not include_deleted:
            query = query.filter(deleted=0)

        return await query.order_by("-version_no").first()

    async def get_by_rule_code(
        self,
        rule_code: str,
        app_name: str = "",
        include_deleted: bool = False
    ) -> Optional[RuleVersion]:
        """
        根据规则编码获取最新版本（用于规则引擎执行）

        Args:
            rule_code: 规则编码
            app_name: 应用名称
            include_deleted: 是否包含已删除的

        Returns:
            RuleVersion 对象或 None
        """
        # 先通过 rule_info_repository 查询规则（只查询启用状态的规则）
        rule = await rule_info_repository.get_by_code(
            rule_code=rule_code,
            app_name=app_name,
            include_deleted=include_deleted,
            status=1 if not include_deleted else None
        )

        if not rule or not rule.latest_version_id:
            return None

        # 获取最新版本
        return await self.get_by_id(
            version_id=rule.latest_version_id,
            include_deleted=include_deleted
        )

    async def list(
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
        query = RuleVersion.filter(rule_id=rule_id)

        query = self._apply_tenant_filter(query)

        if not include_deleted:
            query = query.filter(deleted=0)

        total = await query.count()
        versions = await query.order_by("-version_no").offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return total, versions

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
        query = RuleVersion.filter(rule_id=rule_id, version_no=version_no)

        query = self._apply_tenant_filter(query)

        if not include_deleted:
            query = query.filter(deleted=0)

        return await query.first()


# 创建全局仓库实例
rule_version_repository = RuleVersionRepository()
