"""
填单记录服务层

严格遵循技术约束文档：
- 处理业务逻辑
- 调用 Repository 层进行数据操作
- 禁止直接查询 Model 层
- 租户过滤由 Repository 层自动处理
"""
from typing import List, Optional, Tuple

from tortoise.expressions import Q

from app.models.autofill import FillDataRecord
from app.repositories.autofill.fill_data_record_repository import fill_data_record_repository
from app.schemas.autofill import FillDataRecordUpdate


class FillDataRecordService:
    """
    填单记录业务服务

    职责：
    - 处理填单记录的业务逻辑
    - 调用 Repository 层进行数据操作
    - 构建查询条件

    约束：
    - 不直接查询 Model 层
    - 租户过滤由 Repository 层自动处理
    """

    async def list_records(
        self,
        session_id: str = "",
        phone: str = "",
        user_unique_id: str = "",
        app_name: str = "",
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[int, List[FillDataRecord]]:
        """
        获取填单记录列表

        Args:
            session_id: 会话ID筛选
            phone: 手机号筛选
            user_unique_id: 用户唯一标识筛选
            app_name: 应用名称筛选
            page: 页码
            page_size: 每页数量

        Returns:
            (总数, 记录列表)
        """
        q = Q()
        if session_id:
            q &= Q(session_id__contains=session_id)
        if phone:
            q &= Q(phone__contains=phone)
        if user_unique_id:
            q &= Q(user_unique_id__contains=user_unique_id)
        if app_name:
            q &= Q(app_name__contains=app_name)

        return await fill_data_record_repository.list(
            page=page,
            page_size=page_size,
            search=q,
            order=["-updated_at"]
        )

    async def get_record_by_id(self, record_id: int) -> Optional[FillDataRecord]:
        """
        根据ID获取记录

        Args:
            record_id: 记录ID

        Returns:
            FillDataRecord 对象或 None
        """
        return await fill_data_record_repository.get_by_id(record_id)

    async def update_record(
        self,
        record_id: int,
        record_in: FillDataRecordUpdate
    ) -> FillDataRecord:
        """
        更新填单记录

        Args:
            record_id: 记录ID
            record_in: 更新数据

        Returns:
            更新后的记录对象

        Raises:
            ValueError: 记录不存在
        """
        record = await self.get_record_by_id(record_id)
        if not record:
            raise ValueError("记录不存在")

        update_data = record_in.model_dump(exclude_unset=True, exclude_none=True)
        return await fill_data_record_repository.update(record_id, update_data)

    async def delete_record(self, record_id: int) -> None:
        """
        删除填单记录

        Args:
            record_id: 记录ID

        Raises:
            ValueError: 记录不存在
        """
        record = await self.get_record_by_id(record_id)
        if not record:
            raise ValueError("记录不存在")

        await fill_data_record_repository.delete(record_id)

    async def check_record_exists(self, record_id: int) -> bool:
        """
        检查记录是否存在

        Args:
            record_id: 记录ID

        Returns:
            是否存在
        """
        record = await self.get_record_by_id(record_id)
        return record is not None

    async def record_fill_data(
        self,
        session_id: str,
        app_name: str,
        data: dict,
        phone: Optional[str] = None,
        user_unique_id: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> FillDataRecord:
        """
        记录填单数据，支持数据合并

        Args:
            session_id: 会话ID
            app_name: 应用名称
            data: 填单数据
            phone: 用户手机号
            user_unique_id: 用户唯一标识
            user_name: 用户名称

        Returns:
            FillDataRecord 对象
        """
        record = await fill_data_record_repository.get_by_session_and_app(
            session_id=session_id,
            app_name=app_name
        )

        if record:
            record = await fill_data_record_repository.update_record_data(
                record=record,
                data=data,
                phone=phone,
                user_unique_id=user_unique_id,
                user_name=user_name
            )
        else:
            create_data = {
                "session_id": session_id,
                "app_name": app_name,
                "data": data,
                "phone": phone or "",
                "user_unique_id": user_unique_id or "",
                "user_name": user_name or ""
            }
            record = await fill_data_record_repository.create(create_data)

        return record


# 创建全局服务实例
fill_data_record_service = FillDataRecordService()
