import logging
from typing import Any, Dict, List, Optional

from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.core.crud import CRUDBase

logger = logging.getLogger(__name__)
from app.models.autofill import AppManagement, FillDataRecord
from app.schemas.autofill import AppCreate, AppUpdate, FillDataRecordCreate, FillDataRecordUpdate


class AppManagementController(CRUDBase[AppManagement, AppCreate, AppUpdate]):
    def __init__(self):
        super().__init__(model=AppManagement)

    async def create_app(self, obj_in: AppCreate) -> AppManagement:
        # 检查同一租户下应用名称是否已存在
        existing = await self.model.filter(
            tenant_id=obj_in.tenant_id,
            app_name=obj_in.app_name
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该租户下已存在同名应用")
        return await self.create(obj_in)

    async def update_app(self, id: int, obj_in: AppUpdate) -> AppManagement:
        app = await self.get(id=id)
        # 如果修改了 app_name，需要检查唯一性
        if obj_in.app_name and obj_in.app_name != app.app_name:
            existing = await self.model.filter(
                tenant_id=app.tenant_id,
                app_name=obj_in.app_name
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="该租户下已存在同名应用")
        return await self.update(id=id, obj_in=obj_in)


class FillDataRecordController(CRUDBase[FillDataRecord, FillDataRecordCreate, FillDataRecordUpdate]):
    def __init__(self):
        super().__init__(model=FillDataRecord)

    async def record_fill_data(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str,
        data: Optional[Dict[str, Any]] = None,
        phone: Optional[str] = None,
        user_unique_id: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> FillDataRecord:
        """记录填单数据，支持数据合并"""
        # 查询现有记录
        record = await self.model.filter(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name
        ).first()

        if record:
            # 合并数据: 传入数据覆盖旧数据
            existing_data = record.data or {}
            new_data = data or {}
            merged_data = {**existing_data, **new_data}

            record.data = merged_data
            if phone:
                record.phone = phone
            if user_unique_id:
                record.user_unique_id = user_unique_id
            if user_name:
                record.user_name = user_name
            await record.save()
        else:
            # 创建新记录
            record = await self.model.create(
                session_id=session_id,
                phone=phone or "",
                user_unique_id=user_unique_id or "",
                user_name=user_name or "",
                app_name=app_name,
                tenant_id=tenant_id,
                data=data or {}
            )

        return record

    async def save_original_data(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str,
        data: Dict[str, Any]
    ) -> FillDataRecord:
        """存储原始数据，包装为 {original_data: {...}}"""
        record = await self.model.filter(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name
        ).first()

        wrapped_data = {"original_data": data}

        if record:
            existing = record.data or {}
            existing["original_data"] = data
            record.data = existing
            await record.save()
        else:
            record = await self.model.create(
                session_id=session_id,
                app_name=app_name,
                tenant_id=tenant_id,
                data=wrapped_data
            )

        return record


# 创建控制器实例
app_management_controller = AppManagementController()
fill_data_record_controller = FillDataRecordController()
