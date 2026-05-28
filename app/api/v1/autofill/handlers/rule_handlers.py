
"""
规则管理接口

注意：认证和租户上下文由 TenantContextMiddleware 在中间件层统一处理，
API Handler 不需要重复调用 AuthControl.is_authed() 或 TenantContext.set_tenant_id()
"""
from typing import Optional

from fastapi import APIRouter, Header, Query, UploadFile, File, Form, Request
from fastapi.responses import PlainTextResponse

from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.rule_management import (
    RuleCreate,
    RuleUpdate,
    RuleVersionSave,
    RuleVersionRollback
)
from app.services.rule_management.rule_service import (
    rule_service,
    VersionConflictException,
    NoChangeException
)
from app.api.v1.autofill.handlers.rule_import_handlers import import_csv_file
from app.log import logger

router = APIRouter()


@router.get("/rule/list", summary="规则列表")
async def list_rules(
    request: Request,
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    keyword: str = Query("", description="搜索关键词"),
    status: Optional[int] = Query(None, description="状态筛选（0-禁用，1-启用）"),
    app_name: str = Query("", description="应用名称"),
):
    """获取规则列表

    注意：租户上下文由 TenantContextMiddleware 中间件统一处理
    - 超管账号：可通过 tenant_id 查询参数筛选特定租户
    - 普通账号：自动使用当前租户ID
    """
    total, rules = await rule_service.list_rules(
        app_name=app_name,
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size
    )

    data = []
    for rule in rules:
        rule_dict = await rule.to_dict()
        latest_version = await rule_service.get_version_history(
            rule_code=rule.rule_code,
            page=1,
            page_size=1
        )
        if latest_version[1]:
            rule_dict["latest_version_no"] = latest_version[1][0].get("version_no", 0)
        else:
            rule_dict["latest_version_no"] = 0
        data.append(rule_dict)

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/rule/get", summary="规则详情")
async def get_rule(
    request: Request,
    id: int = Query(..., description="规则ID"),
):
    """获取规则详情（包含最新版本）

    注意：租户上下文由 Repository 层通过 TenantContext 自动处理
    """
    rule = await rule_service.get_rule_by_id(rule_id=id)

    if not rule:
        return Fail(code=404, msg="规则不存在")

    result = {
        "rule_info": await rule.to_dict(),
        "current_version": None
    }

    if rule.latest_version_id:
        version = await rule_service.get_version_by_id(version_id=rule.latest_version_id)
        if version:
            result["current_version"] = await rule_service.version_to_dict(version)

    return Success(data=result)


@router.post("/rule/create", summary="创建规则")
async def create_rule(
    request: Request,
    rule_in: RuleCreate,
):
    """创建新规则

    注意：
    - 超管：必须指定租户ID和应用名称（从请求体获取，中间件已设置 TenantContext）
    - 普通用户：必须指定应用名称，租户ID从当前上下文自动获取
    """
    current_user = request.state.current_user if hasattr(request.state, 'current_user') else None
    
    if not current_user:
        return Fail(code=401, msg="用户未认证")

    request_tenant_id = rule_in.tenant_id

    if current_user.is_superuser:
        if request_tenant_id <= 0:
            return Fail(code=400, msg="超级管理员必须指定租户ID")
        if not rule_in.app_name:
            return Fail(code=400, msg="超级管理员必须指定应用名称")
        app_name = rule_in.app_name
    else:
        if not rule_in.app_name:
            return Fail(code=400, msg="应用名称不能为空")
        app_name = rule_in.app_name

    try:
        rule = await rule_service.create_rule(
            rule_name=rule_in.rule_name,
            desc=rule_in.desc,
            rule_code=rule_in.rule_code,
            app_name=app_name,
            tenant_id=request_tenant_id if current_user.is_superuser and request_tenant_id > 0 else None
        )
        return Success(data=await rule.to_dict())
    except ValueError as e:
        return Fail(code=400, msg=str(e))


@router.post("/rule/update", summary="更新规则")
async def update_rule(
    request: Request,
    rule_in: RuleUpdate,
):
    """更新规则信息
    
    注意：租户上下文由 Repository 层通过 TenantContext 自动处理
    """
    rule_id = rule_in.id

    existing_rule = await rule_service.get_rule_by_id(rule_id=rule_id)

    if not existing_rule:
        return Fail(code=404, msg="规则不存在")

    try:
        rule = await rule_service.update_rule(
            rule_id=rule_id,
            rule_name=rule_in.rule_name,
            desc=rule_in.desc,
            status=rule_in.status
        )
        return Success(data=await rule.to_dict())
    except ValueError as e:
        return Fail(code=400, msg=str(e))


@router.delete("/rule/delete", summary="删除规则")
async def delete_rule(
    request: Request,
    id: int = Query(..., description="规则ID"),
):
    """删除规则（软删除）
    
    注意：租户上下文由 Repository 层通过 TenantContext 自动处理
    """
    existing_rule = await rule_service.get_rule_by_id(rule_id=id)

    if not existing_rule:
        return Fail(code=404, msg="规则不存在")

    try:
        await rule_service.delete_rule(
            rule_code=existing_rule.rule_code
        )
        return Success(msg="删除成功")
    except ValueError as e:
        return Fail(code=400, msg=str(e))


@router.post("/rule/save", summary="保存规则版本")
async def save_version(
    request: Request,
    version_in: RuleVersionSave,
):
    """保存新版本（带乐观锁）
    
    注意：租户上下文由 Repository 层通过 TenantContext 自动处理
    """
    rule_id = version_in.rule_id

    rule = await rule_service.get_rule_by_id(rule_id=rule_id)

    if not rule:
        return Fail(code=404, msg="规则不存在")

    try:
        version = await rule_service.save_version(
            rule=rule,
            content_json=version_in.content_json,
            current_md5=version_in.current_md5,
            remark=version_in.remark
        )
        return Success(data={
            "version_no": version.version_no,
            "new_md5": version.content_md5,
            "created_at": version.created_at.strftime("%Y-%m-%d %H:%M:%S") if version.created_at else ""
        })
    except VersionConflictException as e:
        return Fail(code=409, msg=str(e))
    except NoChangeException as e:
        return Fail(code=400, msg=str(e))
    except ValueError as e:
        return Fail(code=404, msg=str(e))


@router.get("/rule/versions", summary="版本历史")
async def get_version_history(
    request: Request,
    rule_id: int = Query(..., description="规则ID"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
):
    """获取版本历史列表
    
    注意：租户上下文由 Repository 层通过 TenantContext 自动处理
    """
    rule = await rule_service.get_rule_by_id(rule_id=rule_id)

    if not rule:
        return Fail(code=404, msg="规则不存在")

    try:
        total, versions = await rule_service.get_version_history(
            rule_code=rule.rule_code,
            page=page,
            page_size=page_size
        )
        return SuccessExtra(data=versions, total=total, page=page, page_size=page_size)
    except ValueError as e:
        return Fail(code=404, msg=str(e))


@router.get("/rule/version", summary="获取指定版本")
async def get_version_by_no(
    request: Request,
    rule_id: int = Query(..., description="规则ID"),
    version_no: int = Query(..., description="版本号"),
):
    """获取指定版本详情
    
    注意：租户上下文由 Repository 层通过 TenantContext 自动处理
    """
    rule = await rule_service.get_rule_by_id(rule_id=rule_id)

    if not rule:
        return Fail(code=404, msg="规则不存在")

    version = await rule_service.get_version_by_no(
        rule_code=rule.rule_code,
        version_no=version_no
    )

    if not version:
        return Fail(code=404, msg="版本不存在")

    return Success(data=version)


@router.post("/rule/rollback", summary="回滚版本")
async def rollback_version(
    request: Request,
    rollback_in: RuleVersionRollback,
):
    """回滚到指定版本
    
    注意：租户上下文由 Repository 层通过 TenantContext 自动处理
    """
    rule = await rule_service.get_rule_by_id(rule_id=rollback_in.rule_id)
    if not rule:
        return Fail(code=404, msg="规则不存在")

    try:
        version = await rule_service.rollback_version(
            rule_code=rule.rule_code,
            version_no=rollback_in.version_no
        )
        return Success(data={
            "version_no": version.version_no,
            "new_md5": version.content_md5,
            "created_at": version.created_at.strftime("%Y-%m-%d %H:%M:%S") if version.created_at else ""
        })
    except ValueError as e:
        return Fail(code=400, msg=str(e))


@router.post("/rule/import", summary="导入CSV（兼容旧接口）")
async def import_csv_compat(
    request: Request,
    file: UploadFile = File(..., description="CSV文件"),
    rule_id: int = Form(..., description="规则ID"),
):
    return await import_csv_file(request, file, rule_id)


@router.get("/rule/export", summary="导出CSV")
async def export_csv(
    request: Request,
    rule_id: int = Query(..., description="规则ID"),
    version_no: Optional[int] = Query(None, description="版本号，为空则导出最新版本"),
):
    """导出CSV文件
    
    注意：租户上下文由 Repository 层通过 TenantContext 自动处理
    """
    rule = await rule_service.get_rule_by_id(rule_id=rule_id)

    if not rule:
        return Fail(code=404, msg="规则不存在")

    try:
        if version_no:
            version = await rule_service.get_version_by_no(
                rule_code=rule.rule_code,
                version_no=version_no
            )
        else:
            if rule.latest_version_id:
                version_obj = await rule_service.get_version_by_id(version_id=rule.latest_version_id)
                version = await version_obj.to_dict() if version_obj else None
            else:
                version = None

        if not version or not version.get("content_json"):
            return Fail(code=404, msg="版本不存在或无内容")

        csv_content = await rule_service.convert_json_to_csv(version["content_json"])

        filename = f"{rule.rule_code}_v{version.get('version_no', 'latest')}_{version.get('created_at', '').replace(' ', '_').replace(':', '')}.csv"

        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        return Fail(code=404, msg=str(e))
    except Exception as e:
        logger.error("CSV导出失败", error=str(e))
        return Fail(code=500, msg=f"导出失败: {str(e)}")
