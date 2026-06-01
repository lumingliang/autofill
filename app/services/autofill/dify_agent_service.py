"""
Dify Agent 服务层

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

from app.models.dify_agent import DifyAgent
from app.repositories.autofill import dify_agent_repository
from app.schemas.dify_agent import DifyAgentCreate, DifyAgentUpdate


class DifyAgentService:
    """
    Dify Agent 业务服务

    职责：
    - 处理 Dify Agent 的业务逻辑
    - 调用 Repository 层进行数据操作
    - 管理事务控制

    约束：
    - 写操作使用 @atomic() 装饰器
    - 不直接查询 Model 层
    - 不将 tenant_id 传递给 Repository 方法
    """

    async def get_agent_by_id(self, agent_id: int) -> Optional[DifyAgent]:
        """
        根据ID获取 Agent

        Args:
            agent_id: Agent ID

        Returns:
            DifyAgent 对象或 None
        """
        return await dify_agent_repository.get_by_id(agent_id)

    async def get_agent_by_api_key(self, api_key: str) -> Optional[DifyAgent]:
        """
        根据 API Key 获取 Agent（用于 public 接口）

        Args:
            api_key: Dify API Key

        Returns:
            DifyAgent 对象或 None
        """
        return await dify_agent_repository.get_by_api_key(api_key)

    async def list_agents(
        self,
        name: str = "",
        page: int = 1,
        page_size: int = 10
    ):
        """
        获取 Agent 列表

        Args:
            name: Agent 名称筛选
            page: 页码
            page_size: 每页数量

        Returns:
            (总数, Agent 列表)
        """
        search = Q()
        if name:
            search &= Q(name__contains=name)

        return await dify_agent_repository.list(
            page=page,
            page_size=page_size,
            search=search,
            order=["-updated_at"]
        )

    @atomic()
    async def create_agent(self, agent_in: DifyAgentCreate) -> DifyAgent:
        """
        创建新 Agent

        使用 @atomic() 装饰器控制事务

        Args:
            agent_in: 创建 Agent 的数据

        Returns:
            创建的 Agent 对象

        Raises:
            HTTPException: 如果 Agent 名称已存在
        """
        # 检查同一租户下 Agent 名称是否已存在
        if await dify_agent_repository.check_name_exists(agent_in.name):
            raise HTTPException(status_code=400, detail="该租户下已存在同名 Agent")

        # 创建 Agent（tenant_id 由 Repository 自动注入）
        create_data = {
            "name": agent_in.name,
            "api_key": agent_in.api_key,
            "agent_url": agent_in.agent_url,
            "description": agent_in.description,
            "is_active": agent_in.is_active,
        }

        return await dify_agent_repository.create(create_data)

    @atomic()
    async def update_agent(self, agent_id: int, agent_in: DifyAgentUpdate) -> DifyAgent:
        """
        更新 Agent 信息

        使用 @atomic() 装饰器控制事务

        Args:
            agent_id: Agent ID
            agent_in: 更新 Agent 的数据

        Returns:
            更新后的 Agent 对象

        Raises:
            HTTPException: 如果 Agent 不存在或名称冲突
        """
        # 获取 Agent（自动应用租户过滤）
        agent = await dify_agent_repository.get_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent 不存在")

        # 如果修改了 name，需要检查唯一性
        if agent_in.name and agent_in.name != agent.name:
            if await dify_agent_repository.check_name_exists(
                name=agent_in.name,
                exclude_id=agent_id
            ):
                raise HTTPException(status_code=400, detail="该租户下已存在同名 Agent")

        # 更新 Agent
        update_data = {}
        if agent_in.name is not None:
            update_data["name"] = agent_in.name
        if agent_in.api_key is not None:
            update_data["api_key"] = agent_in.api_key
        if agent_in.agent_url is not None:
            update_data["agent_url"] = agent_in.agent_url
        if agent_in.description is not None:
            update_data["description"] = agent_in.description
        if agent_in.is_active is not None:
            update_data["is_active"] = agent_in.is_active

        return await dify_agent_repository.update(agent_id, update_data)

    @atomic()
    async def delete_agent(self, agent_id: int) -> None:
        """
        删除 Agent

        使用 @atomic() 装饰器控制事务

        Args:
            agent_id: Agent ID

        Raises:
            HTTPException: 如果 Agent 不存在
        """
        # 获取 Agent（自动应用租户过滤）
        agent = await dify_agent_repository.get_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent 不存在")

        await dify_agent_repository.delete(agent_id)

    async def get_active_agents(self):
        """
        获取所有启用的 Agent

        Returns:
            Agent 列表
        """
        return await dify_agent_repository.list_active_agents()


# 服务实例
dify_agent_service = DifyAgentService()
