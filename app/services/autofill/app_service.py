"""
应用管理服务层

严格遵循技术约束文档：
- 处理业务逻辑
- 调用 Repository 层进行数据操作
- 使用 @atomic() 装饰器控制事务
- 禁止直接查询 Model 层
- 禁止将 tenant_id 传递给 Repository 方法
"""
from typing import Optional

from fastapi import HTTPException
from tortoise.expressions import Q
from tortoise.transactions import atomic

from app.models.autofill import AppManagement
from app.repositories.autofill import app_management_repository
from app.schemas.autofill import AppCreate, AppUpdate


class AppService:
    """
    应用管理业务服务

    职责：
    - 处理应用管理的业务逻辑
    - 调用 Repository 层进行数据操作
    - 管理事务控制

    约束：
    - 写操作使用 @atomic() 装饰器
    - 不直接查询 Model 层
    - 不将 tenant_id 传递给 Repository 方法
    """

    async def get_app_by_id(self, app_id: int) -> Optional[AppManagement]:
        """
        根据ID获取应用

        Args:
            app_id: 应用ID

        Returns:
            AppManagement 对象或 None
        """
        return await app_management_repository.get_by_id(app_id)

    async def get_app_by_name(self, app_name: str) -> Optional[AppManagement]:
        """
        根据应用名称获取应用

        Args:
            app_name: 应用名称

        Returns:
            AppManagement 对象或 None
        """
        return await app_management_repository.get_by_app_name(app_name)

    async def list_apps(
        self,
        app_name: str = "",
        page: int = 1,
        page_size: int = 10
    ):
        """
        获取应用列表

        Args:
            app_name: 应用名称筛选
            page: 页码
            page_size: 每页数量

        Returns:
            (总数, 应用列表)
        """
        search = Q()
        if app_name:
            search &= Q(app_name__contains=app_name)

        return await app_management_repository.list(
            page=page,
            page_size=page_size,
            search=search,
            order=["-updated_at"]
        )

    @atomic()
    async def create_app(self, app_in: AppCreate) -> AppManagement:
        """
        创建新应用

        使用 @atomic() 装饰器控制事务

        Args:
            app_in: 创建应用的数据

        Returns:
            创建的应用对象

        Raises:
            HTTPException: 如果应用名称已存在
        """
        # 检查同一租户下应用名称是否已存在
        if await app_management_repository.check_app_name_exists(app_in.app_name):
            raise HTTPException(status_code=400, detail="该租户下已存在同名应用")

        # 创建应用（tenant_id 由 Repository 自动注入）
        create_data = {
            "app_name": app_in.app_name,
            "description": app_in.description,
            "is_active": True,
        }

        return await app_management_repository.create(create_data)

    @atomic()
    async def update_app(self, app_id: int, app_in: AppUpdate) -> AppManagement:
        """
        更新应用信息

        使用 @atomic() 装饰器控制事务

        Args:
            app_id: 应用ID
            app_in: 更新应用的数据

        Returns:
            更新后的应用对象

        Raises:
            HTTPException: 如果应用不存在或名称冲突
        """
        # 获取应用（自动应用租户过滤）
        app = await app_management_repository.get_by_id(app_id)
        if not app:
            raise HTTPException(status_code=404, detail="应用不存在")

        # 如果修改了 app_name，需要检查唯一性
        if app_in.app_name and app_in.app_name != app.app_name:
            if await app_management_repository.check_app_name_exists(
                app_name=app_in.app_name,
                exclude_id=app_id
            ):
                raise HTTPException(status_code=400, detail="该租户下已存在同名应用")

        # 更新应用
        update_data = {}
        if app_in.app_name:
            update_data["app_name"] = app_in.app_name
        if app_in.description is not None:
            update_data["description"] = app_in.description
        if app_in.is_active is not None:
            update_data["is_active"] = app_in.is_active

        return await app_management_repository.update(app_id, update_data)

    @atomic()
    async def delete_app(self, app_id: int) -> None:
        """
        删除应用

        使用 @atomic() 装饰器控制事务

        Args:
            app_id: 应用ID

        Raises:
            HTTPException: 如果应用不存在
        """
        # 获取应用（自动应用租户过滤）
        app = await app_management_repository.get_by_id(app_id)
        if not app:
            raise HTTPException(status_code=404, detail="应用不存在")

        await app_management_repository.delete(app_id)

    async def get_active_apps(self):
        """
        获取所有启用的应用

        Returns:
            应用列表
        """
        return await app_management_repository.get_active_apps()

    async def list_all_apps(
        self,
        page: int = 1,
        page_size: int = 1000
    ):
        """
        获取所有应用列表（租户过滤由 Repository 自动处理）

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            (总数, 应用列表)
        """
        return await app_management_repository.list(
            page=page,
            page_size=page_size,
            order=["-updated_at"]
        )

    async def get_app_by_name_for_current_tenant(
        self,
        app_name: str
    ) -> Optional[AppManagement]:
        """
        根据应用名称获取应用（租户过滤由 Repository 自动处理）

        Args:
            app_name: 应用名称

        Returns:
            AppManagement 对象或 None
        """
        return await app_management_repository.get_by_app_name(app_name)


# 创建全局服务实例
app_service = AppService()
