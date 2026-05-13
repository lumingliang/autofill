from typing import Optional, Set, Tuple
import jwt
from fastapi import Depends, Header, HTTPException, Request

from app.core.ctx import CTX_USER_ID
from app.core.relation import RelationQuery
from app.core.redis import redis_client
from app.models import User
from app.models.admin import Api
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
                decode_data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                user_id = decode_data.get("user_id")
            user = await User.filter(id=user_id).first()
            if not user:
                raise HTTPException(status_code=401, detail="Authentication failed")
            # 从 token 中解析当前租户 ID 并设置到用户对象上
            current_tenant_id = decode_data.get("current_tenant_id")
            if current_tenant_id:
                user.current_tenant_id = current_tenant_id
            # 从 token 中解析租户域名并设置到用户对象上
            tenant_domain = decode_data.get("tenant_domain")
            if tenant_domain:
                user.tenant_domain = tenant_domain
            else:
                user.tenant_domain = ""
            CTX_USER_ID.set(int(user_id))
            return user
        except jwt.DecodeError:
            raise HTTPException(status_code=401, detail="Invalid Token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Login expired")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{repr(e)}")


class PermissionControl:
    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed)) -> None:
        if current_user.is_superuser:
            return
        
        method = request.method
        path = request.url.path
        tenant_id = getattr(current_user, "current_tenant_id", 0)
        
        # 尝试从缓存获取权限
        cache_key = f"user_perms:{current_user.id}:{tenant_id}"
        
        try:
            cached_perms = await redis_client.get_json(cache_key)
            if cached_perms:
                permission_apis = set(tuple(p) for p in cached_perms)
            else:
                # 单次批量查询代替 N+1
                role_ids = await RelationQuery.get_role_ids_by_user_id(current_user.id)
                if not role_ids:
                    raise HTTPException(status_code=403, detail="The user is not bound to a role")
                
                # 使用优化后的方法一次性获取权限
                permission_apis = await RelationQuery.get_user_api_permissions(current_user.id, tenant_id)
                
                if not permission_apis:
                    raise HTTPException(status_code=403, detail="The user is not bound to a role")
                
                # 缓存权限（5分钟）
                await redis_client.set_json(
                    cache_key,
                    [list(p) for p in permission_apis],
                    ttl=300
                )
            
            if (method, path) not in permission_apis:
                raise HTTPException(status_code=403, detail=f"Permission denied method:{method} path:{path}")
        
        except HTTPException:
            raise
        except Exception as e:
            # 如果 Redis 出错，降级直接查询数据库
            role_ids = await RelationQuery.get_role_ids_by_user_id(current_user.id)
            if not role_ids:
                raise HTTPException(status_code=403, detail="The user is not bound to a role")
            
            api_ids_mapping = await RelationQuery.batch_get_api_ids_by_role_ids(role_ids)
            all_api_ids = list({aid for ids in api_ids_mapping.values() for aid in ids})
            
            if not all_api_ids:
                raise HTTPException(status_code=403, detail="The user is not bound to a role")
            
            apis = await Api.filter(id__in=all_api_ids).values("method", "path")
            permission_apis = {(api["method"], api["path"]) for api in apis}
            
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
    
    根据当前用户和传入的租户 ID，返回租户查询参数
    - 超级管理员且指定了租户 ID：返回指定租户 ID
    - 普通用户：返回当前用户的租户 ID（如果已设置）
    - 无租户限制：返回 0
    
    Args:
        current_user: 当前用户对象
        tenant_id: 传入的租户 ID（仅超级管理员有效）
    
    Returns:
        dict: 包含 tenant_id 的字典，用于查询条件构建
    """
    if tenant_id > 0 and is_superuser(current_user):
        return {"tenant_id": tenant_id}
    elif not is_superuser(current_user):
        if current_user.current_tenant_id > 0:
            return {"tenant_id": current_user.current_tenant_id}
    return {"tenant_id": 0}


def get_effective_tenant_id(current_user: User, tenant_id: int = 0) -> int:
    """
    获取有效的租户 ID
    
    根据当前用户和传入的租户 ID，返回实际应该使用的租户 ID
    - 超级管理员且指定了租户 ID：返回指定租户 ID
    - 普通用户：返回当前用户的租户 ID
    - 无租户：返回 0
    
    Args:
        current_user: 当前用户对象
        tenant_id: 传入的租户 ID（仅超级管理员有效）
    
    Returns:
        int: 有效的租户 ID
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

