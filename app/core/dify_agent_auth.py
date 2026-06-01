"""
Dify Agent API Key 认证中间件

用于 Public Agent 接口的认证
根据 api_key 查询对应的 Dify Agent 配置
"""
from fastapi import Header, HTTPException

from app.core.ctx import Ctx
from app.services.autofill.dify_agent_service import dify_agent_service


class DifyAgentAuth:
    """Dify Agent API Key 认证类"""

    @classmethod
    async def authenticate(cls, authorization: str = Header(..., description="Authorization: Bearer {api_key}")) -> dict:
        """
        解析 Authorization: Bearer {api_key}
        验证 api_key 是否对应有效的 Dify Agent

        Args:
            authorization: Authorization header，格式为 "Bearer {api_key}"

        Returns:
            dict: 包含 agent 信息的字典
                - agent_id: Agent ID
                - agent_name: Agent 名称
                - tenant_id: 租户 ID

        Raises:
            HTTPException: 认证失败时抛出 401 错误
        """
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format. Expected: Bearer {api_key}")

        api_key = authorization.replace("Bearer ", "").strip()

        if not api_key:
            raise HTTPException(status_code=401, detail="API key is required")

        # 查询 Agent 配置
        agent = await dify_agent_service.get_agent_by_api_key(api_key)
        if not agent:
            raise HTTPException(status_code=401, detail="Invalid API key")

        if not agent.is_active:
            raise HTTPException(status_code=403, detail="Agent is disabled")

        # 设置租户上下文（通过 Ctx）
        Ctx.set_tenant_id(agent.tenant_id)

        return {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "tenant_id": agent.tenant_id,
            "api_key": api_key,
        }
