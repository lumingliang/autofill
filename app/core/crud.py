from typing import Any, Dict, Generic, List, NewType, Tuple, Type, TypeVar, Union

from pydantic import BaseModel
from tortoise.expressions import Q
from tortoise.models import Model

Total = NewType("Total", int)
ModelType = TypeVar("ModelType", bound=Model)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, id: int) -> ModelType:
        return await self.model.get(id=id)

    async def list(self, page: int, page_size: int, search: Q = Q(), order: list = []) -> Tuple[Total, List[ModelType]]:
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
        obj = obj.update_from_dict(obj_dict)
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
