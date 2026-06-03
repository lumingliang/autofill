"""
批量测试任务 Repository - 数据访问层

严格遵循技术约束文档：
- 继承 BaseRepository 获得通用 CRUD 能力
- 自动应用租户过滤（通过 BaseRepository）
- 禁止手动传递 tenant_id 参数
- 使用 self.filter() 进行链式查询
"""
from typing import List, Optional, Tuple

from tortoise.expressions import Q

from app.models.batch_test import BatchTestTask
from app.repositories.base_repository import BaseRepository


class BatchTestRepository(BaseRepository[BatchTestTask]):
    """
    批量测试任务 Repository

    职责：
    - 批量测试任务相关的数据访问操作
    - 继承 BaseRepository 获得通用 CRUD 能力
    - 自动应用租户过滤

    约束：
    - 禁止直接查询 Model，使用 self.filter() 方法
    - 禁止手动传递 tenant_id 参数，从 Ctx 获取
    """

    def __init__(self):
        super().__init__(BatchTestTask)

    async def get_by_id_with_tenant(self, task_id: int) -> Optional[BatchTestTask]:
        """
        根据ID获取任务（自动应用租户过滤）

        Args:
            task_id: 任务ID

        Returns:
            BatchTestTask 对象或 None
        """
        return await self.get_by_id(task_id)

    async def list_tasks(
        self,
        keyword: str = "",
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[int, List[BatchTestTask]]:
        """
        获取任务列表

        自动应用租户过滤（通过 self.filter）

        Args:
            keyword: 关键词搜索（任务名称）
            status: 状态筛选
            page: 页码
            page_size: 每页数量

        Returns:
            (总数, 任务列表)
        """
        search = Q()
        if keyword:
            search &= Q(task_name__contains=keyword)
        if status is not None:
            search &= Q(status=status)

        return await self.list(
            page=page,
            page_size=page_size,
            search=search,
            order=["-updated_at"]
        )

    async def check_task_name_exists(
        self,
        name: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        检查任务名称是否已存在

        自动应用租户过滤（通过 self.filter）

        Args:
            name: 任务名称
            exclude_id: 排除的ID（用于更新时检查）

        Returns:
            bool: 是否存在
        """
        query = self.filter(task_name=name)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    async def get_running_tasks(self) -> List[BatchTestTask]:
        """
        获取所有执行中的任务

        自动应用租户过滤（通过 self.filter）

        Returns:
            执行中的任务列表
        """
        return await self.filter(status=1).all()


# Repository 实例
batch_test_repository = BatchTestRepository()
