"""
Dify Agent 管理接口

参考 depts.py 简洁风格：
- 直接在路由函数中调用 Service 层
- 不使用 API 类包装
- 认证由中间件统一处理
- 租户过滤由 Repository 层自动处理
"""
from fastapi import APIRouter, Depends, Query

from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.dify_agent import DifyAgentCreate, DifyAgentUpdate, DifyAgentListQuery
from app.services.autofill.dify_agent_service import dify_agent_service

router = APIRouter()


@router.get("/dify-agent/list", summary="Dify Agent 列表")
async def list_dify_agent(
    query: DifyAgentListQuery = Depends(),
):
    """获取 Dify Agent 列表"""
    total, agents = await dify_agent_service.list_agents(
        name=query.name,
        page=query.page,
        page_size=query.page_size
    )
    data = [await obj.to_dict() for obj in agents]
    return SuccessExtra(
        data=data,
        total=total,
        page=query.page,
        page_size=query.page_size
    )


@router.get("/dify-agent/get", summary="Dify Agent 详情")
async def get_dify_agent(
    id: int = Query(..., description="Agent ID"),
):
    """获取 Dify Agent 详情"""
    agent = await dify_agent_service.get_agent_by_id(agent_id=id)
    if not agent:
        return Fail(code=404, msg="Agent 不存在")
    return Success(data=await agent.to_dict())


@router.post("/dify-agent/create", summary="创建 Dify Agent")
async def create_dify_agent(
    agent_in: DifyAgentCreate,
):
    """
    创建 Dify Agent

    租户ID由 Repository 层自动从上下文获取并注入
    """
    try:
        agent = await dify_agent_service.create_agent(agent_in=agent_in)
        return Success(data=await agent.to_dict())
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.post("/dify-agent/update", summary="更新 Dify Agent")
async def update_dify_agent(
    agent_in: DifyAgentUpdate,
):
    """更新 Dify Agent 信息"""
    try:
        updated = await dify_agent_service.update_agent(
            agent_id=agent_in.id,
            agent_in=agent_in
        )
        return Success(data=await updated.to_dict())
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.delete("/dify-agent/delete", summary="删除 Dify Agent")
async def delete_dify_agent(
    id: int = Query(..., description="Agent ID"),
):
    """删除 Dify Agent"""
    try:
        await dify_agent_service.delete_agent(agent_id=id)
        return Success(msg="删除成功")
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.get("/dify-agent/select", summary="Dify Agent 下拉列表")
async def get_dify_agent_select():
    """获取 Dify Agent 下拉列表"""
    agents = await dify_agent_service.get_active_agents()
    data = [{"label": agent.name, "value": agent.id} for agent in agents]
    return Success(data=data)
