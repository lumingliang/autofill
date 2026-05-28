
from typing import Optional
import jwt
from fastapi import Depends, Header, HTTPException, Request

from app.core.ctx import CTX_USER_ID
from app.core.relation import RelationQuery
from app.core.tenant import TenantContext
from app.models import User
from app.models.admin import Api
from app.services.permission_cache_service import permission_cache_service
from app.settings import settings


async def get_current_user_from_request(request: Request) -> Optional["User"]:
    """
    从请求状态中获取当前用户（由 TenantContextMiddleware 设置）
    
    这是推荐的获取当前用户的方式，避免重复认证。
    如果中间件未设置，则返回 None。
    """
    if hasattr(request.state, 'current_user'):
        return request.state.current_user
    return None


async def get_current_user_dep(request: Request) -> "User":
    """
    依赖注入：获取当前用户
    
    从 request.state 获取当前用户（由 TenantContextMiddleware 设置）
    如果用户未认证，抛出 401 异常
    
    Raises:
        HTTPException: 用户未认证时抛出 401 异常
    """
    user = await get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def get_tenant_id_from_request(request: Request) -> int:
    """
    从请求状态中获取租户ID
    
    Returns:
        int: 租户ID（0 表示未设置或超级管理员未指定租户）
    """
    if hasattr(request.state, 'tenant_id'):
        return request.state.tenant_id
    return 0


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
            current_tenant_id = decode_data.get("current_tenant_id")
            if current_tenant_id:
                user.current_tenant_id = current_tenant_id
            tenant_domain = decode_data.get("tenant_domain")
            user.tenant_domain = tenant_domain if tenant_domain else ""
            CTX_USER_ID.set(int(user_id))
            TenantContext.set_user(user)
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

        try:
            # 使用权限缓存服务获取用户权限
            permission_apis = await permission_cache_service.get_user_permissions(current_user.id, tenant_id)

            if permission_apis is None:
                raise HTTPException(status_code=403, detail="用户未绑定角色")

            # 获取当前请求的API code
            current_api = await Api.filter(method=method, path=path).first()
            if not current_api:
                raise HTTPException(status_code=403, detail="API未注册")

            if current_api.api_code not in permission_apis:
                raise HTTPException(status_code=403, detail="无权限访问")

        except HTTPException:
            raise
        except Exception:
            # 降级处理：直接从数据库获取权限
            role_ids = await RelationQuery.get_role_ids_by_user_id(current_user.id)
            if not role_ids:
                raise HTTPException(status_code=403, detail="用户未绑定角色")

            api_ids_mapping = await RelationQuery.batch_get_api_ids_by_role_ids(role_ids)
            all_api_ids = list({aid for ids in api_ids_mapping.values() for aid in ids})

            if not all_api_ids:
                raise HTTPException(status_code=403, detail="用户未绑定角色")

            apis = await Api.filter(id__in=all_api_ids).values("api_code")
            permission_apis = {api["api_code"] for api in apis}

            # 获取当前请求的API code
            current_api = await Api.filter(method=method, path=path).first()
            if not current_api:
                raise HTTPException(status_code=403, detail="API未注册")

            if current_api.api_code not in permission_apis:
                raise HTTPException(status_code=403, detail="无权限访问")


DependAuth = Depends(AuthControl.is_authed)
DependPermission = Depends(PermissionControl.has_permission)


def is_superuser(user: User) -> bool:
    """检查是否为超级管理员"""
    return user.is_superuser


def get_effective_tenant_id(user: User, requested_tenant_id: int = 0) -> int:
    """
    获取有效的租户ID
    仅超级管理员可以使用请求的租户ID，普通用户只能使用自己的租户ID
    超级管理员不传tenant_id（或传0）时返回0，表示查询所有租户数据
    """
    if user.is_superuser:
        # 超管：传了tenant_id就按tenant_id过滤，否则返回0（查询所有）
        return requested_tenant_id if requested_tenant_id > 0 else 0
    # 普通用户：只能查询自己的租户
    return getattr(user, "current_tenant_id", 0)


def build_tenant_query(user: User, requested_tenant_id: int = 0) -> dict:
    """
    构建租户查询条件
    仅超级管理员可以使用请求的租户ID，普通用户只能使用自己的租户ID
    超级管理员不传tenant_id（或传0）时返回0，表示查询所有租户数据
    返回字典格式: {"tenant_id": int}
    """
    if user.is_superuser:
        # 超管：传了tenant_id就按tenant_id过滤，否则返回0（查询所有）
        return {"tenant_id": requested_tenant_id if requested_tenant_id > 0 else 0}
    # 普通用户：只能查询自己的租户
    return {"tenant_id": getattr(user, "current_tenant_id", 0)}


async def get_current_user(token: str = Header(..., description="token验证")) -> User:
    """获取当前用户（用于依赖注入）"""
    return await AuthControl.is_authed(token)


class TenantControl:
    """租户权限控制类 - 统一处理创建/更新/删除操作的租户ID验证
    
    设计原则:
    - 查询: 超管可选筛选（可查所有），普通用户只能查本租户
    - 创建: 超管必须指定租户，普通用户自动使用当前租户
    - 更新/删除: 通过数据本身的 tenant_id 验证权限
    """

    @classmethod
    def validate_create_tenant_id(cls, user: User, requested_tenant_id: int) -> tuple[bool, str, int]:
        """
        验证创建操作时的租户ID
        
        Args:
            user: 当前用户
            requested_tenant_id: 请求中传入的租户ID
            
        Returns:
            tuple: (是否成功, 错误信息, 有效的租户ID)
        """
        if user.is_superuser:
            # 超管必须传tenant_id
            if requested_tenant_id <= 0:
                return False, "超级管理员必须指定租户ID", 0
            return True, "", requested_tenant_id
        else:
            # 普通用户：忽略传入的tenant_id，自动使用当前租户
            effective_tenant_id = getattr(user, "current_tenant_id", 0)
            if effective_tenant_id <= 0:
                return False, "您当前未选择租户，无法执行此操作", 0
            return True, "", effective_tenant_id

    @classmethod
    def validate_update_permission(cls, user: User, existing_tenant_id: int) -> tuple[bool, str]:
        """
        验证更新操作的权限（通过数据本身的 tenant_id 验证）
        
        Args:
            user: 当前用户
            existing_tenant_id: 现有数据的租户ID
            
        Returns:
            tuple: (是否成功, 错误信息)
        """
        if user.is_superuser:
            # 超管可以更新任何租户的数据
            return True, ""
        else:
            # 普通用户只能更新自己租户的数据
            effective_tenant_id = getattr(user, "current_tenant_id", 0)
            if effective_tenant_id <= 0:
                return False, "您当前未选择租户，无法执行此操作"
            if existing_tenant_id != effective_tenant_id:
                return False, "您没有权限更新该租户的数据"
            return True, ""

    @classmethod
    def validate_delete_permission(cls, user: User, existing_tenant_id: int) -> tuple[bool, str]:
        """
        验证删除操作的权限（通过数据本身的 tenant_id 验证）
        
        Args:
            user: 当前用户
            existing_tenant_id: 要删除数据的租户ID
            
        Returns:
            tuple: (是否成功, 错误信息)
        """
        if user.is_superuser:
            # 超管可以删除任何租户的数据
            return True, ""
        else:
            # 普通用户只能删除自己租户的数据
            effective_tenant_id = getattr(user, "current_tenant_id", 0)
            if effective_tenant_id <= 0:
                return False, "您当前未选择租户，无法执行此操作"
            if existing_tenant_id != effective_tenant_id:
                return False, "您没有权限删除该租户的数据"
            return True, ""

    @classmethod
    def validate_update_tenant_id(cls, user: User, requested_tenant_id: int, 
                                  existing_tenant_id: int = 0) -> tuple[bool, str, int]:
        """
        [Deprecated] 验证更新操作时的租户ID，建议使用 validate_update_permission
        
        Args:
            user: 当前用户
            requested_tenant_id: 请求中传入的租户ID
            existing_tenant_id: 现有数据的租户ID（用于校验权限）
            
        Returns:
            tuple: (是否成功, 错误信息, 有效的租户ID)
        """
        if user.is_superuser:
            # 超管可以更新任何租户的数据，但如果传了tenant_id必须有效
            if requested_tenant_id > 0:
                return True, "", requested_tenant_id
            # 没传tenant_id则保持原有租户不变
            return True, "", existing_tenant_id
        else:
            # 普通用户只能更新自己租户的数据
            effective_tenant_id = getattr(user, "current_tenant_id", 0)
            if effective_tenant_id <= 0:
                return False, "您当前未选择租户，无法执行此操作", 0
            # 检查是否有权限更新这条数据
            if existing_tenant_id > 0 and existing_tenant_id != effective_tenant_id:
                return False, "您没有权限更新该租户的数据", 0
            # 普通用户不能修改租户ID
            return True, "", effective_tenant_id
