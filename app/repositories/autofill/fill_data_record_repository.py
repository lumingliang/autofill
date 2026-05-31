"""
FillDataRecord Repository - 填单记录数据访问层

严格遵循技术约束文档：
- 继承 BaseRepository 获得通用 CRUD 能力
- 自动应用租户过滤（通过 BaseRepository）
- 禁止手动传递 tenant_id 参数
- 使用 self.filter() 进行链式查询
"""
from typing import Any, Dict, List, Optional

from app.models.autofill import FillDataRecord
from app.repositories.base_repository import BaseRepository


class FillDataRecordRepository(BaseRepository[FillDataRecord]):
    """
    填单记录 Repository

    职责：
    - 填单记录相关的数据访问操作
    - 继承 BaseRepository 获得通用 CRUD 能力
    - 自动应用租户过滤

    约束：
    - 禁止直接查询 Model，使用 self.filter() 方法
    - 禁止手动传递 tenant_id 参数，从 Ctx 获取
    """

    def __init__(self):
        super().__init__(FillDataRecord)

    async def get_by_session_id(self, session_id: str) -> Optional[FillDataRecord]:
        """
        根据会话ID获取记录

        自动应用租户过滤（通过 self.filter）

        Args:
            session_id: 会话ID

        Returns:
            FillDataRecord 对象或 None
        """
        return await self.filter(session_id=session_id).first()

    async def get_by_session_and_app(
        self,
        session_id: str,
        app_name: str
    ) -> Optional[FillDataRecord]:
        """
        根据会话ID和应用名称获取记录

        自动应用租户过滤（通过 self.filter）

        Args:
            session_id: 会话ID
            app_name: 应用名称

        Returns:
            FillDataRecord 对象或 None
        """
        return await self.filter(session_id=session_id, app_name=app_name).first()

    async def list_by_phone(self, phone: str) -> List[FillDataRecord]:
        """
        根据手机号获取记录列表

        自动应用租户过滤（通过 self.filter）

        Args:
            phone: 手机号

        Returns:
            FillDataRecord 列表
        """
        return await self.filter(phone=phone).all()

    async def update_record_data(
        self,
        record: FillDataRecord,
        data: dict,
        phone: Optional[str] = None,
        user_unique_id: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> FillDataRecord:
        """
        更新填单记录数据

        Args:
            record: 填单记录对象
            data: 要合并的数据
            phone: 手机号（可选）
            user_unique_id: 用户唯一标识（可选）
            user_name: 用户名称（可选）

        Returns:
            更新后的 FillDataRecord 对象
        """
        existing_data = record.data or {}
        merged_data = {**existing_data, **data}
        record.data = merged_data

        if phone is not None:
            record.phone = phone
        if user_unique_id is not None:
            record.user_unique_id = user_unique_id
        if user_name is not None:
            record.user_name = user_name

        await record.save()
        return record

    async def get_by_session_and_app_with_tenant(
        self,
        session_id: str,
        app_name: str
    ) -> Optional[FillDataRecord]:
        """
        根据会话ID和应用名称获取记录（自动应用租户过滤）

        与 get_by_session_and_app 相同，但明确用于需要租户过滤的场景

        Args:
            session_id: 会话ID
            app_name: 应用名称

        Returns:
            FillDataRecord 对象或 None
        """
        return await self.filter(session_id=session_id, app_name=app_name).first()

    async def save_step_request(
        self,
        session_id: str,
        app_name: str,
        request_data: Dict[str, Any],
        step: int
    ) -> FillDataRecord:
        """
        保存步骤请求数据

        如果记录存在则更新，不存在则创建

        Args:
            session_id: 会话ID
            app_name: 应用名称
            request_data: 请求数据
            step: 步骤编号

        Returns:
            FillDataRecord 对象
        """
        record = await self.get_by_session_and_app_with_tenant(session_id, app_name)

        if record:
            existing_data = record.data or []
            if not isinstance(existing_data, list):
                existing_data = [existing_data] if existing_data else []

            existing_data.append({
                "step": step,
                "request": request_data
            })

            record.data = existing_data
            await record.save()
            return record
        else:
            return await self.create({
                "session_id": session_id,
                "app_name": app_name,
                "data": [{
                    "step": step,
                    "request": request_data
                }],
                "result": [],
                "status": "processing"
            })

    async def save_step_result(
        self,
        session_id: str,
        app_name: str,
        step: int,
        results: Dict[str, Any],
        elapsed_time: float,
        is_last: bool
    ) -> Optional[FillDataRecord]:
        """
        保存步骤结果数据

        Args:
            session_id: 会话ID
            app_name: 应用名称
            step: 步骤编号
            results: 结果数据
            elapsed_time: 执行耗时
            is_last: 是否为最后一步

        Returns:
            FillDataRecord 对象或 None（如果记录不存在）
        """
        record = await self.get_by_session_and_app_with_tenant(session_id, app_name)

        if not record:
            return None

        existing_result = record.result or []
        if not isinstance(existing_result, list):
            existing_result = [existing_result] if existing_result else []

        existing_result.append({
            "step": step,
            "fields": results,
            "timing": {"elapsed_time": elapsed_time}
        })

        record.result = existing_result

        if is_last:
            record.status = "completed"
            from datetime import datetime
            record.processed_at = datetime.now()

        await record.save()
        return record


# 创建全局仓库实例
fill_data_record_repository = FillDataRecordRepository()
