from typing import Any, Dict, Generic, List, NewType, Optional, Tuple, Type, TypeVar, Union

from pydantic import BaseModel
from tortoise.expressions import Q
from tortoise.models import Model

from app.core.dependency import build_tenant_query

Total = NewType("Total", int)
ModelType = TypeVar("ModelType", bound=Model)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, id: int) -> ModelType:
        return await self.model.get(id=id)

    async def list(
        self, 
        page: int, 
        page_size: int, 
        search: Q = Q(), 
        order: list = [],
        user=None,
        tenant_id: int = 0
    ) -> Tuple[Total, List[ModelType]]:
        """
        列表查询，支持自动租户过滤
        
        Args:
            page: 页码
            page_size: 每页数量
            search: 查询条件
            order: 排序
            user: 当前用户（用于租户过滤）
            tenant_id: 请求的租户ID
        """
        if user:
            search = self._apply_tenant_filter(search, user, tenant_id)
        
        query = self.model.filter(search)
        return await query.count(), await query.offset((page - 1) * page_size).limit(page_size).order_by(*order)

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        if isinstance(obj_in, Dict):
            obj_dict = obj_in
        else:
            obj_dict = obj_in.model_dump()
        obj = self.model(**obj_dict)
        await obj.save()
        return obj

    async def update(self, id: int, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        if isinstance(obj_in, Dict):
            obj_dict = obj_in
            relation_fields = {}
        else:
            obj_dict = obj_in.model_dump(exclude_unset=True, exclude={"id"})
            relation_fields = self._extract_relation_fields(obj_in)

        obj = await self.get(id=id)
        obj = await obj.update_from_dict(obj_dict)
        await obj.save()

        if relation_fields:
            await self._update_relations(obj, relation_fields)

        return obj

    def _extract_relation_fields(self, obj_in: UpdateSchemaType) -> Dict[str, Any]:
        """提取关联字段（如 role_ids, tenant_ids），子类可覆盖"""
        return {}

    async def _update_relations(self, obj: ModelType, relation_fields: Dict[str, Any]) -> None:
        """更新关联关系，子类覆盖实现显式关联操作"""
        pass

    async def remove(self, id: int) -> None:
        obj = await self.get(id=id)
        await obj.delete()

    def _apply_tenant_filter(self, search: Q, user, tenant_id: int = 0) -> Q:
        """
        应用租户过滤条件
        
        Args:
            search: 原始查询条件
            user: 当前用户
            tenant_id: 请求的租户ID
        Returns:
            应用了租户过滤的查询条件
        """
        tenant_query = build_tenant_query(user, tenant_id)
        if tenant_query["tenant_id"] > 0:
            search &= Q(tenant_id=tenant_query["tenant_id"])
        return search

    async def filter_by_tenant(
        self,
        search: Q = Q(),
        user=None,
        tenant_id: int = 0,
        order: list = []
    ) -> List[ModelType]:
        """
        按租户过滤查询所有数据（不分页）
        
        Args:
            search: 查询条件
            user: 当前用户
            tenant_id: 请求的租户ID
            order: 排序
        Returns:
            模型实例列表
        """
        if user:
            search = self._apply_tenant_filter(search, user, tenant_id)
        
        query = self.model.filter(search)
        if order:
            query = query.order_by(*order)
        return await query.all()
