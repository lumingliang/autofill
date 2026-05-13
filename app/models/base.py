from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar
from tortoise import fields, models
from app.settings import settings


class BaseModel(models.Model):
    id = fields.BigIntField(pk=True, index=True)
    
    class Meta:
        abstract = True
    
    async def to_dict(
        self, 
        exclude_fields: Optional[List[str]] = None,
        include_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """支持包含/排除字段的字典转换"""
        exclude_fields = exclude_fields or []
        
        if include_fields:
            fields_to_include = include_fields
        else:
            fields_to_include = [
                f for f in self._meta.db_fields 
                if f not in exclude_fields
            ]
        
        d = {}
        for field in fields_to_include:
            value = getattr(self, field)
            if isinstance(value, datetime):
                value = value.strftime(settings.DATETIME_FORMAT)
            d[field] = value
        
        return d
    
    async def update_from_dict(self, data: Dict[str, Any]) -> "BaseModel":
        """从字典更新字段"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        await self.save()
        return self


class TimestampMixin:
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)


T = TypeVar('T', bound=BaseModel)


class CRUDManager:
    """增强的 CRUD 基类"""
    
    def __init__(self, model: T):
        self.model = model
    
    async def get(self, pk: int, related: Optional[List[str]] = None) -> Optional[T]:
        """获取单个对象"""
        query = self.model.filter(id=pk)
        if related:
            query = query.prefetch_related(*related)
        return await query.first()
    
    async def get_or_404(self, pk: int, related: Optional[List[str]] = None) -> T:
        """获取单个对象，不存在则抛出异常"""
        obj = await self.get(pk, related)
        if not obj:
            from app.core.exceptions import ResourceNotFoundException
            raise ResourceNotFoundException()
        return obj
    
    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Any = None,
        order: Optional[List[str]] = None,
        related: Optional[List[str]] = None
    ) -> tuple[int, List[T]]:
        """分页查询列表"""
        query = self.model.all()
        
        if search:
            query = query.filter(search)
        
        total = await query.count()
        
        if related:
            query = query.prefetch_related(*related)
        
        if order:
            query = query.order_by(*order)
        
        items = await query.offset((page - 1) * page_size).limit(page_size)
        
        return total, items
    
    async def all(
        self, 
        search: Any = None,
        order: Optional[List[str]] = None,
        related: Optional[List[str]] = None
    ) -> List[T]:
        """查询所有数据"""
        query = self.model.all()
        
        if search:
            query = query.filter(search)
        
        if related:
            query = query.prefetch_related(*related)
        
        if order:
            query = query.order_by(*order)
        
        return await query
    
    async def create(self, data: Dict[str, Any]) -> T:
        """创建对象"""
        return await self.model.create(**data)
    
    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[T]:
        """批量创建"""
        objs = [self.model(**data) for data in data_list]
        return await self.model.bulk_create(objs)
    
    async def update(self, pk: int, data: Dict[str, Any]) -> Optional[T]:
        """更新对象"""
        obj = await self.get(pk)
        if not obj:
            return None
        await obj.update_from_dict(data)
        return obj
    
    async def delete(self, pk: int) -> bool:
        """删除对象"""
        deleted_count = await self.model.filter(id=pk).delete()
        return deleted_count > 0
    
    async def bulk_delete(self, ids: List[int]) -> int:
        """批量删除"""
        return await self.model.filter(id__in=ids).delete()
    
    async def exists(self, **kwargs) -> bool:
        """检查是否存在"""
        return await self.model.filter(**kwargs).exists()
    
    async def count(self, search: Any = None) -> int:
        """统计数量"""
        if search:
            return await self.model.filter(search).count()
        return await self.model.all().count()
    
    async def get_or_create(self, defaults: Optional[Dict[str, Any]] = None, **kwargs) -> tuple[T, bool]:
        """获取或创建"""
        defaults = defaults or {}
        return await self.model.get_or_create(defaults=defaults, **kwargs)

