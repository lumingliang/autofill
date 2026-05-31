"""
RuleInfo Repository - 规则基本信息数据访问层（重构版）

严格遵循技术约束文档：
- 继承 BaseRepository 获得通用 CRUD 能力
- 自动应用租户过滤（通过 BaseRepository）
- 禁止手动传递 tenant_id 参数
- 使用 self.filter() 进行链式查询
"""
from typing import List, Optional, Tuple

from tortoise.expressions import Q

from app.models.rule_management import RuleInfo
from app.repositories.base_repository import BaseRepository


class RuleInfoRepository(BaseRepository[RuleInfo]):
    """
    规则信息 Repository

    职责：
    - 规则信息相关的数据访问操作
    - 继承 BaseRepository 获得通用 CRUD 能力
    - 自动应用租户过滤

    约束：
    - 禁止直接查询 Model，使用 self.filter() 方法
    - 禁止手动传递 tenant_id 参数，从 Ctx 获取
    """

    def __init__(self):
        super().__init__(RuleInfo)

    async def get_by_id(
        self,
        rule_id: int
    ) -> Optional[RuleInfo]:
        """
        根据ID获取规则

        Args:
            rule_id: 规则ID

        Returns:
            RuleInfo 对象或 None
        """
        return await self.filter(Q(id=rule_id)).first()

    async def get_by_code(
        self,
        rule_code: str,
        app_name: str = "",
        status: Optional[int] = None
    ) -> Optional[RuleInfo]:
        """
        根据编码获取规则

        Args:
            rule_code: 规则编码
            app_name: 应用名称
            status: 状态筛选（可选）

        Returns:
            RuleInfo 对象或 None
        """
        query = Q(rule_code=rule_code)

        if app_name:
            query &= Q(app_name=app_name)

        if status is not None:
            query &= Q(status=status)

        return await self.filter(query).first()

    async def check_code_exists(
        self,
        rule_code: str,
        app_name: str = "",
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        检查规则编码是否已存在

        Args:
            rule_code: 规则编码
            app_name: 应用名称
            exclude_id: 要排除的规则ID（用于修改时排除自身）

        Returns:
            是否存在
        """
        query = Q(rule_code=rule_code)

        if app_name:
            query &= Q(app_name=app_name)

        if exclude_id:
            return await self.filter(query).exclude(id=exclude_id).exists()
        return await self.filter(query).exists()

    async def check_name_exists(
        self,
        rule_name: str,
        app_name: str = "",
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        检查规则名称是否已存在

        Args:
            rule_name: 规则名称
            app_name: 应用名称
            exclude_id: 要排除的规则ID（用于修改时排除自身）

        Returns:
            是否存在
        """
        query = Q(rule_name=rule_name)

        if app_name:
            query &= Q(app_name=app_name)

        if exclude_id:
            return await self.filter(query).exclude(id=exclude_id).exists()
        return await self.filter(query).exists()

    async def list_rules(
        self,
        app_name: str = "",
        keyword: str = "",
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[int, List[RuleInfo]]:
        """
        获取规则列表

        Args:
            app_name: 应用名称
            keyword: 关键词搜索（匹配 rule_code 或 rule_name）
            status: 状态筛选
            page: 页码
            page_size: 每页数量

        Returns:
            (总数, 规则列表)
        """
        query = Q()

        if app_name:
            query &= Q(app_name=app_name)

        if keyword:
            query &= Q(rule_code__contains=keyword) | Q(rule_name__contains=keyword)

        if status is not None:
            query &= Q(status=status)

        total = await self.filter(query).count()
        rules = await self.filter(query).order_by("-updated_at").offset(
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
            规则列表（只返回状态为启用的）
        """
        query = Q(status=1)

        if app_name:
            query &= Q(app_name=app_name)

        return await self.filter(query).all()


# 创建全局仓库实例
rule_info_repository = RuleInfoRepository()
