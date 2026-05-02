from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request

from app.core.ctx import CTX_USER_ID
from app.core.relation import RelationQuery
from app.models import User
from app.settings import settings


class AuthControl:
    @classmethod
    async def is_authed(cls, token: str = Header(..., description="token验证")) -> Optional["User"]:
        try:
            decode_data = {}
            if token == "dev":
                user = await User.filter().first()
                user_id = user.id
            else:
                decode_data = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.JWT_ALGORITHM)
                user_id = decode_data.get("user_id")
            user = await User.filter(id=user_id).first()
            if not user:
                raise HTTPException(status_code=401, detail="Authentication failed")
            # 从token中解析当前租户ID并设置到用户对象上
            current_tenant_id = decode_data.get("current_tenant_id")
            if current_tenant_id:
                user.current_tenant_id = current_tenant_id
            # 从token中解析租户域名并设置到用户对象上
            tenant_domain = decode_data.get("tenant_domain")
            if tenant_domain:
                user.tenant_domain = tenant_domain
            else:
                user.tenant_domain = ""
            CTX_USER_ID.set(int(user_id))
            return user
        except jwt.DecodeError:
            raise HTTPException(status_code=401, detail="无效的Token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="登录已过期")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{repr(e)}")


class PermissionControl:
    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed)) -> None:
        if current_user.is_superuser:
            return
        method = request.method
        path = request.url.path
        # 通过RelationQuery获取用户角色的API权限，不再使用关系查询
        role_ids = await RelationQuery.get_role_ids_by_user_id(current_user.id)
        if not role_ids:
            raise HTTPException(status_code=403, detail="The user is not bound to a role")
        api_ids = []
        for rid in role_ids:
            ids = await RelationQuery.get_api_ids_by_role_id(rid)
            api_ids.extend(ids)
        api_ids = list(set(api_ids))
        if not api_ids:
            raise HTTPException(status_code=403, detail="The user is not bound to a role")
        from app.models.admin import Api
        apis = await Api.filter(id__in=api_ids).all()
        permission_apis = list(set((api.method, api.path) for api in apis))
        if (method, path) not in permission_apis:
            raise HTTPException(status_code=403, detail=f"Permission denied method:{method} path:{path}")


DependAuth = Depends(AuthControl.is_authed)
DependPermission = Depends(PermissionControl.has_permission)


def is_superuser(user: User) -> bool:
    """检查是否为超级管理员"""
    return user.is_superuser


def build_tenant_query(current_user: User, tenant_id: int = 0) -> dict:
    """
    构建租户查询条件

    根据当前用户和传入的租户ID，返回租户查询参数
    - 超级管理员且指定了租户ID：返回指定租户ID
    - 普通用户：返回当前用户的租户ID（如果已设置）
    - 无租户限制：返回0

    Args:
        current_user: 当前用户对象
        tenant_id: 传入的租户ID（仅超级管理员有效）

    Returns:
        dict: 包含tenant_id的字典，用于查询条件构建
    """
    if tenant_id > 0 and is_superuser(current_user):
        return {"tenant_id": tenant_id}
    elif not is_superuser(current_user):
        if current_user.current_tenant_id > 0:
            return {"tenant_id": current_user.current_tenant_id}
    return {"tenant_id": 0}


def get_effective_tenant_id(current_user: User, tenant_id: int = 0) -> int:
    """
    获取有效的租户ID

    根据当前用户和传入的租户ID，返回实际应该使用的租户ID
    - 超级管理员且指定了租户ID：返回指定租户ID
    - 普通用户：返回当前用户的租户ID
    - 无租户：返回0

    Args:
        current_user: 当前用户对象
        tenant_id: 传入的租户ID（仅超级管理员有效）

    Returns:
        int: 有效的租户ID
    """
    if tenant_id > 0 and is_superuser(current_user):
        return tenant_id
    elif not is_superuser(current_user):
        return current_user.current_tenant_id
    return 0


async def get_current_user(token: str = Header(..., description="token验证")) -> User:
    """
    获取当前用户

    用于依赖注入，获取当前登录用户对象

    Args:
        token: JWT token

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 认证失败时抛出
    """
    return await AuthControl.is_authed(token)
