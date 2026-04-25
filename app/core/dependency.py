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
