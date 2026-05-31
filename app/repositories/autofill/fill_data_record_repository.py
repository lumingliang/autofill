"""
FillDataRecord Repository - 填单记录数据访问层

严格遵循技术约束文档：
- 继承 BaseRepository 获得通用 CRUD 能力
- 自动应用租户过滤（通过 BaseRepository）
- 禁止手动传递 tenant_id 参数
- 使用 self.filter() 进行链式查询
"""
from typing import List, Optional

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


# 创建全局仓库实例
fill_data_record_repository = FillDataRecordRepository()
