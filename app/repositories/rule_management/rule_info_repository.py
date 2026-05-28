"""
RuleInfo Repository - 规则基本信息数据访问层
"""
from typing import List, Optional, Tuple

from app.models.rule_management import RuleInfo
from app.core.tenant import TenantContext
from tortoise.expressions import Q


class RuleInfoRepository:
    """规则基本信息仓库"""

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
        rule_id: int,
        include_deleted: bool = False
    ) -> Optional[RuleInfo]:
        """
        根据ID获取规则

        Args:
            rule_id: 规则ID
            include_deleted: 是否包含已删除的规则

        Returns:
            RuleInfo 对象或 None
        """
        query = RuleInfo.filter(id=rule_id)

        query = self._apply_tenant_filter(query)

        if not include_deleted:
            query = query.filter(deleted=0)

        return await query.first()

    async def get_by_code(
        self,
        rule_code: str,
        app_name: str = "",
        include_deleted: bool = False,
        status: Optional[int] = None
    ) -> Optional[RuleInfo]:
        """
        根据编码获取规则

        Args:
            rule_code: 规则编码
            app_name: 应用名称
            include_deleted: 是否包含已删除的规则
            status: 状态筛选（可选）

        Returns:
            RuleInfo 对象或 None
        """
        query = RuleInfo.filter(rule_code=rule_code)

        query = self._apply_tenant_filter(query)

        if app_name:
            query = query.filter(app_name=app_name)

        if not include_deleted:
            query = query.filter(deleted=0)

        if status is not None:
            query = query.filter(status=status)

        return await query.first()

    async def check_code_exists(
        self,
        rule_code: str,
        app_name: str = "",
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        检查规则编码是否已存在（排除已删除的）

        Args:
            rule_code: 规则编码
            app_name: 应用名称
            exclude_id: 要排除的规则ID（用于修改时排除自身）

        Returns:
            是否存在（只检查未删除的）
        """
        query = RuleInfo.filter(
            rule_code=rule_code,
            deleted=0  # 只检查未删除的
        )

        query = self._apply_tenant_filter(query)

        if app_name:
            query = query.filter(app_name=app_name)

        if exclude_id:
            query = query.exclude(id=exclude_id)

        return await query.exists()

    async def check_name_exists(
        self,
        rule_name: str,
        app_name: str = "",
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        检查规则名称是否已存在（排除已删除的）

        Args:
            rule_name: 规则名称
            app_name: 应用名称
            exclude_id: 要排除的规则ID（用于修改时排除自身）

        Returns:
            是否存在（只检查未删除的）
        """
        query = RuleInfo.filter(
            rule_name=rule_name,
            deleted=0  # 只检查未删除的
        )

        query = self._apply_tenant_filter(query)

        if app_name:
            query = query.filter(app_name=app_name)

        if exclude_id:
            query = query.exclude(id=exclude_id)

        return await query.exists()

    async def list(
        self,
        app_name: str = "",
        keyword: str = "",
        status: Optional[int] = None,
        include_deleted: bool = False,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[int, List[RuleInfo]]:
        """
        获取规则列表

        Args:
            app_name: 应用名称
            keyword: 关键词搜索（匹配 rule_code 或 rule_name）
            status: 状态筛选
            include_deleted: 是否包含已删除的
            page: 页码
            page_size: 每页数量

        Returns:
            (总数, 规则列表)
        """
        query = RuleInfo.filter()

        if not include_deleted:
            query = query.filter(deleted=0)

        query = self._apply_tenant_filter(query)

        if app_name:
            query = query.filter(app_name=app_name)

        if keyword:
            query = query.filter(
                Q(rule_code__contains=keyword) | Q(rule_name__contains=keyword)
            )

        if status is not None:
            query = query.filter(status=status)

        total = await query.count()
        rules = await query.order_by("-updated_at").offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return total, rules

    async def get_all_active(
        self,
        app_name: str = ""
    ) -> List[RuleInfo]:
        """
        获取所有启用的规则（用于规则引擎执行）

        Args:
            app_name: 应用名称

        Returns:
            规则列表（只返回未删除且状态为启用的）
        """
        query = RuleInfo.filter(
            deleted=0,
            status=1
        )

        query = self._apply_tenant_filter(query)

        if app_name:
            query = query.filter(app_name=app_name)

        return await query.all()


# 创建全局仓库实例
rule_info_repository = RuleInfoRepository()
