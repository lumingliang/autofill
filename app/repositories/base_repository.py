"""
Repository 层泛型基类

提供通用的 CRUD 操作，所有 Repository 必须继承此类。
所有查询方法自动进行租户过滤，租户ID从 Ctx 中获取。
"""

from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar

from tortoise.expressions import Q
from tortoise.models import Model
from tortoise.queryset import QuerySet

from app.core.ctx import Ctx

ModelType = TypeVar("ModelType", bound=Model)
Total = int


class BaseRepository(Generic[ModelType]):
    """
    Repository 层泛型基类

    所有 Repository 必须继承此类，通用的 CRUD 操作直接调用基类方法，
    子类只需实现特殊的查询逻辑。

    特性：
    - 所有查询方法自动进行租户过滤（可关闭）
    - 租户ID从 Ctx 中获取，禁止手动传递
    - 创建时自动注入当前租户ID（可关闭）

    使用示例：
        class UserRepository(BaseRepository[User]):
            def __init__(self):
                super().__init__(User)

            # 只实现特殊查询逻辑
            # 其他 Model 可以直接在方法中使用
            async def get_user_with_roles(self, user_id: int):
                user = await self.get(id=user_id)
                roles = await Role.filter(user_roles__user_id=user_id)
                return user, roles

        class TenantRepository(BaseRepository[Tenant]):
            # Tenant 不需要租户过滤
            enable_tenant_filter = False

            def __init__(self):
                super().__init__(Tenant)
    """

    # 是否启用租户过滤，子类可覆盖
    enable_tenant_filter: bool = True

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def _get_tenant_filter(self) -> Dict[str, Any]:
        """
        获取租户过滤条件

        Returns:
            Dict[str, Any]: 租户过滤条件字典，空字典表示不过滤
        """
        if not self.enable_tenant_filter:
            return {}
        return Ctx.build_query_filter() or {}

    def _apply_tenant_filter_to_query(self, query: Q) -> Q:
        """
        应用租户过滤条件到 Q 对象

        注意：User 模型没有 tenant_id 字段，通过关联表查询
        此方法主要用于有 tenant_id 字段的模型
        """
        if not self.enable_tenant_filter:
            return query

        tenant_filter = Ctx.build_query_filter()
        if tenant_filter:
            for field, value in tenant_filter.items():
                query &= Q(**{field: value})
        return query

    async def get(self, id: int) -> ModelType:
        """
        根据ID获取单个对象，不存在抛出异常

        自动应用租户过滤（如果启用）
        """
        query = Q(id=id)
        query = self._apply_tenant_filter_to_query(query)
        return await self.model.get(query)

    async def get_or_none(self, id: int) -> Optional[ModelType]:
        """
        根据ID获取单个对象，不存在返回None

        自动应用租户过滤（如果启用）
        """
        query = Q(id=id)
        query = self._apply_tenant_filter_to_query(query)
        return await self.model.filter(query).first()

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        根据ID获取单个对象，不存在返回None

        自动应用租户过滤（如果启用）

        Args:
            id: 对象ID

        Returns:
            Optional[ModelType]: 对象，不存在返回None
        """
        return await self.get_or_none(id)

    async def get_by_ids(self, ids: List[int]) -> List[ModelType]:
        """
        根据ID列表批量获取对象（自动应用租户过滤）

        Args:
            ids: ID列表

        Returns:
            List[ModelType]: 对象列表
        """
        if not ids:
            return []

        tenant_filter = self._get_tenant_filter()
        if tenant_filter:
            return await self.model.filter(id__in=ids, **tenant_filter).all()
        return await self.model.filter(id__in=ids).all()

    async def list(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Q = Q(),
        order: List[str] = None
    ) -> Tuple[Total, List[ModelType]]:
        """
        分页查询列表

        自动应用租户过滤（如果启用）

        Args:
            page: 页码，从1开始
            page_size: 每页数量
            search: 查询条件
            order: 排序字段列表

        Returns:
            Tuple[Total, List[ModelType]]: (总数, 数据列表)
        """
        if order is None:
            order = ["-id"]

        # 应用租户过滤
        search = self._apply_tenant_filter_to_query(search)

        query = self.model.filter(search)
        total = await query.count()
        data = await query.offset((page - 1) * page_size).limit(page_size).order_by(*order)
        return total, data

    async def get_all_by_tenant(self) -> List[ModelType]:
        """
        获取当前租户下的所有对象（自动应用租户过滤）

        Returns:
            List[ModelType]: 对象列表
        """
        tenant_filter = self._get_tenant_filter()
        if tenant_filter:
            return await self.model.filter(**tenant_filter).all()
        return await self.model.all()

    async def filter_by_kwargs(self, **kwargs) -> List[ModelType]:
        """
        根据条件筛选对象（自动应用租户过滤）

        Args:
            **kwargs: 过滤条件

        Returns:
            List[ModelType]: 对象列表
        """
        tenant_filter = self._get_tenant_filter()
        if tenant_filter:
            return await self.model.filter(**kwargs, **tenant_filter).all()
        return await self.model.filter(**kwargs).all()

    def _has_field(self, field_name: str) -> bool:
        """检查模型是否有指定字段"""
        return field_name in self.model._meta.fields_map

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        创建新对象

        自动注入当前租户ID（如果启用且模型有 tenant_id 字段）
        """
        obj_dict = obj_in.copy()

        # 自动注入租户ID（如果启用且模型有 tenant_id 字段且未设置）
        if self.enable_tenant_filter:
            if self._has_field("tenant_id") and "tenant_id" not in obj_dict:
                effective_tenant_id = Ctx.get_effective_tenant_id()
                if effective_tenant_id > 0:
                    obj_dict["tenant_id"] = effective_tenant_id

        obj = self.model(**obj_dict)
        await obj.save()
        return obj

    async def update(
        self,
        id: int,
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """
        更新对象

        自动应用租户过滤（如果启用）
        """
        obj_dict = obj_in.copy()

        # 获取对象（自动应用租户过滤）
        obj = await self.get(id=id)

        # 更新字段
        for field, value in obj_dict.items():
            setattr(obj, field, value)

        await obj.save()
        return obj

    async def delete(self, id: int) -> None:
        """
        删除对象

        自动应用租户过滤（如果启用）
        """
        obj = await self.get(id=id)
        await obj.delete()

    async def all(self, order: List[str] = None) -> List[ModelType]:
        """
        获取所有对象

        自动应用租户过滤（如果启用）
        """
        query = Q()
        query = self._apply_tenant_filter_to_query(query)

        qs = self.model.filter(query)
        if order:
            qs = qs.order_by(*order)
        return await qs.all()

    def filter(self, *args, **kwargs) -> QuerySet[ModelType]:
        """
        获取已应用租户过滤的 QuerySet，支持链式调用

        使用示例：
            rows = await self.filter(user_id=user_id).values("role_id")
            ids = await self.filter(ancestor=ancestor_id).values_list("descendant", flat=True)
            await self.filter(user_id=user_id).delete()

        Returns:
            QuerySet[ModelType]: 已应用租户过滤的 QuerySet
        """
        # 应用租户过滤
        tenant_filter = self._get_tenant_filter()
        if tenant_filter:
            kwargs.update(tenant_filter)

        return self.model.filter(*args, **kwargs)

    async def exists(self, **kwargs) -> bool:
        """
        检查是否存在满足条件的对象

        自动应用租户过滤（如果启用）
        """
        # 应用租户过滤
        tenant_filter = self._get_tenant_filter()
        if tenant_filter:
            kwargs.update(tenant_filter)

        return await self.model.filter(**kwargs).exists()

    async def count(self, *args, **kwargs) -> int:
        """
        统计满足条件的对象数量

        自动应用租户过滤（如果启用）
        """
        # 应用租户过滤
        tenant_filter = self._get_tenant_filter()
        if tenant_filter:
            kwargs.update(tenant_filter)

        return await self.model.filter(*args, **kwargs).count()

    async def first(self, *args, **kwargs) -> Optional[ModelType]:
        """
        获取第一个匹配的对象

        自动应用租户过滤（如果启用）
        """
        # 应用租户过滤
        tenant_filter = self._get_tenant_filter()
        if tenant_filter:
            kwargs.update(tenant_filter)

        return await self.model.filter(*args, **kwargs).first()
