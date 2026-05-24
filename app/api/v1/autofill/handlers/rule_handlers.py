"""
规则管理接口
"""
from typing import Optional

from fastapi import APIRouter, Header, Query, UploadFile, File, Form
from fastapi.responses import PlainTextResponse

from app.controllers.rule_management import (
    rule_info_controller,
    rule_version_controller
)
from app.core.dependency import AuthControl, build_tenant_query, TenantControl
from app.models.rule_management import RuleInfo, RuleVersion
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
from app.log import logger

router = APIRouter()


@router.get("/rule/list", summary="规则列表")
async def list_rules(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    keyword: str = Query("", description="搜索关键词"),
    status: Optional[int] = Query(None, description="状态筛选（0-禁用，1-启用）"),
    tenant_id: int = Query(0, description="租户ID"),
    app_name: str = Query("", description="应用名称"),
    token: str = Header(..., description="token验证"),
):
    """获取规则列表"""
    current_user = await AuthControl.is_authed(token)

    tenant_query = build_tenant_query(current_user, tenant_id)
    effective_tenant_id = tenant_query.get("tenant_id", 0)
    # 优先使用传入的 app_name，否则使用 tenant_query 中的
    effective_app_name = app_name if app_name else tenant_query.get("app_name", "")

    total, rules = await rule_info_controller.list_rules(
        tenant_id=effective_tenant_id,
        app_name=effective_app_name,
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size
    )

    data = []
    for rule in rules:
        rule_dict = await rule.to_dict()
        latest_version = await rule_version_controller.get_version_history(
            rule_code=rule.rule_code,
            tenant_id=effective_tenant_id,
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
    id: int = Query(..., description="规则ID"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """获取规则详情（包含最新版本）
    
    权限：
    - 超管：可传 tenant_id 指定租户，不传则查询所有租户
    - 普通用户：使用当前租户
    """
    current_user = await AuthControl.is_authed(token)

    tenant_query = build_tenant_query(current_user, tenant_id)
    effective_tenant_id = tenant_query.get("tenant_id", 0)

    # 使用 id + tenant_id 查询规则
    query = RuleInfo.filter(
        id=id,
        deleted=0
    )
    # 非超管或指定了租户ID时，添加租户过滤
    if effective_tenant_id > 0:
        query = query.filter(tenant_id=effective_tenant_id)

    rule = await query.first()

    if not rule:
        return Fail(code=404, msg="规则不存在")

    # 构建详情
    result = {
        "rule_info": await rule.to_dict(),
        "current_version": None
    }

    if rule.latest_version_id:
        version = await RuleVersion.filter(
            id=rule.latest_version_id,
            deleted=0
        ).first()
        if version:
            result["current_version"] = await rule_service._version_to_dict(version)

    return Success(data=result)


@router.post("/rule/create", summary="创建规则")
async def create_rule(
    rule_in: RuleCreate,
    token: str = Header(..., description="token验证"),
):
    """创建新规则
    
    权限要求：
    - 超管：必须指定租户ID和应用名称
    - 普通用户：必须指定应用名称，租户ID从当前上下文自动获取
    """
    current_user = await AuthControl.is_authed(token)

    # 优先从请求体获取 tenant_id
    request_tenant_id = rule_in.tenant_id

    if current_user.is_superuser:
        # 超管：必须指定租户ID
        if request_tenant_id <= 0:
            return Fail(code=400, msg="超级管理员必须指定租户ID")
        effective_tenant_id = request_tenant_id
        # 超管：必须指定应用名称
        if not rule_in.app_name:
            return Fail(code=400, msg="超级管理员必须指定应用名称")
        app_name = rule_in.app_name
    else:
        # 普通用户：租户ID从当前上下文获取
        effective_tenant_id = getattr(current_user, "current_tenant_id", 0)
        if effective_tenant_id <= 0:
            return Fail(code=400, msg="您当前未选择租户，无法执行此操作")
        # 普通用户：必须指定应用名称
        if not rule_in.app_name:
            return Fail(code=400, msg="应用名称不能为空")
        app_name = rule_in.app_name

    try:
        rule = await rule_info_controller.create_rule(
            obj_in=rule_in,
            tenant_id=effective_tenant_id,
            app_name=app_name
        )
        return Success(data=await rule.to_dict())
    except ValueError as e:
        return Fail(code=400, msg=str(e))


@router.post("/rule/update", summary="更新规则")
async def update_rule(
    rule_in: RuleUpdate,
    token: str = Header(..., description="token验证"),
):
    """更新规则信息"""
    current_user = await AuthControl.is_authed(token)

    # 从请求体获取 tenant_id 和 id
    request_tenant_id = rule_in.tenant_id
    rule_id = rule_in.id

    tenant_query = build_tenant_query(current_user, request_tenant_id)
    effective_tenant_id = tenant_query.get("tenant_id", 0)

    # 使用 id + tenant_id 查询规则
    query = RuleInfo.filter(
        id=rule_id,
        deleted=0
    )
    if effective_tenant_id > 0:
        query = query.filter(tenant_id=effective_tenant_id)

    existing_rule = await query.first()

    if not existing_rule:
        return Fail(code=404, msg="规则不存在")

    try:
        rule = await rule_info_controller.update_rule(
            rule_id=rule_id,
            obj_in=rule_in,
            tenant_id=effective_tenant_id
        )
        return Success(data=await rule.to_dict())
    except ValueError as e:
        return Fail(code=400, msg=str(e))


@router.delete("/rule/delete", summary="删除规则")
async def delete_rule(
    id: int = Query(..., description="规则ID"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """删除规则（软删除）
    
    权限：
    - 超管：可传 tenant_id 指定租户
    - 普通用户：使用当前租户
    """
    current_user = await AuthControl.is_authed(token)

    tenant_query = build_tenant_query(current_user, tenant_id)
    effective_tenant_id = tenant_query.get("tenant_id", 0)

    # 使用 id + tenant_id 查询规则
    query = RuleInfo.filter(
        id=id,
        deleted=0
    )
    if effective_tenant_id > 0:
        query = query.filter(tenant_id=effective_tenant_id)

    existing_rule = await query.first()

    if not existing_rule:
        return Fail(code=404, msg="规则不存在")

    success, msg = TenantControl.validate_delete_permission(
        current_user, existing_rule.tenant_id
    )
    if not success:
        return Fail(code=403, msg=msg)

    try:
        await rule_info_controller.delete_rule(
            rule_code=existing_rule.rule_code,
            tenant_id=existing_rule.tenant_id,
            app_name=existing_rule.app_name
        )
        return Success(msg="删除成功")
    except ValueError as e:
        return Fail(code=400, msg=str(e))


@router.post("/rule/save", summary="保存规则版本")
async def save_version(
    version_in: RuleVersionSave,
    token: str = Header(..., description="token验证"),
):
    """保存新版本（带乐观锁）
    
    权限：
    - 超管：可传 tenant_id 指定租户
    - 普通用户：使用当前租户
    """
    current_user = await AuthControl.is_authed(token)

    # 从请求体获取 tenant_id 和 rule_id
    request_tenant_id = version_in.tenant_id
    rule_id = version_in.rule_id

    tenant_query = build_tenant_query(current_user, request_tenant_id)
    effective_tenant_id = tenant_query.get("tenant_id", 0)

    # 使用 id + tenant_id 查询规则
    query = RuleInfo.filter(
        id=rule_id,
        deleted=0
    )
    if effective_tenant_id > 0:
        query = query.filter(tenant_id=effective_tenant_id)

    rule = await query.first()

    if not rule:
        return Fail(code=404, msg="规则不存在")

    try:
        version = await rule_version_controller.save_version(
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
    rule_id: int = Query(..., description="规则ID"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """获取版本历史列表
    
    权限：
    - 超管：可传 tenant_id 指定租户
    - 普通用户：使用当前租户
    """
    current_user = await AuthControl.is_authed(token)

    tenant_query = build_tenant_query(current_user, tenant_id)
    effective_tenant_id = tenant_query.get("tenant_id", 0)

    # 使用 id + tenant_id 查询规则
    query = RuleInfo.filter(
        id=rule_id,
        deleted=0
    )
    if effective_tenant_id > 0:
        query = query.filter(tenant_id=effective_tenant_id)

    rule = await query.first()

    if not rule:
        return Fail(code=404, msg="规则不存在")

    try:
        total, versions = await rule_version_controller.get_version_history(
            rule_code=rule.rule_code,
            tenant_id=rule.tenant_id,
            page=page,
            page_size=page_size
        )
        return SuccessExtra(data=versions, total=total, page=page, page_size=page_size)
    except ValueError as e:
        return Fail(code=404, msg=str(e))


@router.get("/rule/version", summary="获取指定版本")
async def get_version_by_no(
    rule_id: int = Query(..., description="规则ID"),
    version_no: int = Query(..., description="版本号"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """获取指定版本详情
    
    权限：
    - 超管：可传 tenant_id 指定租户
    - 普通用户：使用当前租户
    """
    current_user = await AuthControl.is_authed(token)

    tenant_query = build_tenant_query(current_user, tenant_id)
    effective_tenant_id = tenant_query.get("tenant_id", 0)

    # 使用 id + tenant_id 查询规则
    query = RuleInfo.filter(
        id=rule_id,
        deleted=0
    )
    if effective_tenant_id > 0:
        query = query.filter(tenant_id=effective_tenant_id)

    rule = await query.first()

    if not rule:
        return Fail(code=404, msg="规则不存在")

    version = await rule_version_controller.get_version_by_no(
        rule_code=rule.rule_code,
        version_no=version_no,
        tenant_id=rule.tenant_id
    )

    if not version:
        return Fail(code=404, msg="版本不存在")

    return Success(data=version)


@router.post("/rule/rollback", summary="回滚版本")
async def rollback_version(
    rollback_in: RuleVersionRollback,
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """回滚到指定版本
    
    权限：
    - 超管：可传 tenant_id 指定租户
    - 普通用户：使用当前租户（从build_tenant_query获取）
    """
    current_user = await AuthControl.is_authed(token)

    # 使用全局函数获取租户查询条件
    tenant_query = build_tenant_query(current_user, tenant_id)
    effective_tenant_id = tenant_query.get("tenant_id", 0)

    # 使用 id 查询规则（超管不传tenant_id时可查询所有租户）
    rule_query = RuleInfo.filter(
        id=rollback_in.rule_id,
        deleted=0
    )
    # 非超管或指定了租户ID时，添加租户过滤
    if effective_tenant_id > 0:
        rule_query = rule_query.filter(tenant_id=effective_tenant_id)

    rule = await rule_query.first()
    if not rule:
        return Fail(code=404, msg="规则不存在")

    try:
        # 使用规则的tenant_id进行回滚，确保service层能正确查询
        version = await rule_version_controller.rollback_version(
            rule_code=rule.rule_code,
            version_no=rollback_in.version_no,
            tenant_id=rule.tenant_id,
            app_name=rule.app_name
        )
        return Success(data={
            "version_no": version.version_no,
            "new_md5": version.content_md5,
            "created_at": version.created_at.strftime("%Y-%m-%d %H:%M:%S") if version.created_at else ""
        })
    except ValueError as e:
        return Fail(code=400, msg=str(e))


@router.post("/rule/import", summary="导入CSV")
async def import_csv(
    file: UploadFile = File(..., description="CSV文件"),
    rule_id: int = Form(..., description="规则ID"),
    current_md5: str = Form("", description="当前版本MD5（可选）"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """导入CSV文件，返回预览数据
    
    权限：
    - 超管：可传 tenant_id 指定租户
    - 普通用户：使用当前租户（从build_tenant_query获取）
    """
    current_user = await AuthControl.is_authed(token)

    # 使用全局函数获取租户查询条件
    tenant_query = build_tenant_query(current_user, tenant_id)
    effective_tenant_id = tenant_query.get("tenant_id", 0)

    # 使用 id + tenant_id 查询规则
    query = RuleInfo.filter(
        id=rule_id,
        deleted=0
    )
    # 指定了租户ID时，添加租户过滤
    if effective_tenant_id > 0:
        query = query.filter(tenant_id=effective_tenant_id)

    rule = await query.first()

    if not rule:
        return Fail(code=404, msg="规则不存在")

    try:
        content = await file.read()
        csv_content = content.decode('utf-8')

        content_json = await rule_service.parse_csv_to_json(csv_content)

        return Success(data={
            "headers": content_json["headers"],
            "data": content_json["data"][:10],
            "row_count": len(content_json["data"]),
            "preview": True,
            "full_content": content_json
        })
    except Exception as e:
        logger.error("CSV导入失败", error=str(e))
        return Fail(code=400, msg=f"CSV解析失败: {str(e)}")


@router.get("/rule/export", summary="导出CSV")
async def export_csv(
    rule_id: int = Query(..., description="规则ID"),
    version_no: Optional[int] = Query(None, description="版本号，为空则导出最新版本"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """导出CSV文件
    
    权限：
    - 超管：可传 tenant_id 指定租户
    - 普通用户：使用当前租户
    """
    current_user = await AuthControl.is_authed(token)

    tenant_query = build_tenant_query(current_user, tenant_id)
    effective_tenant_id = tenant_query.get("tenant_id", 0)

    # 使用 id + tenant_id 查询规则
    query = RuleInfo.filter(
        id=rule_id,
        deleted=0
    )
    if effective_tenant_id > 0:
        query = query.filter(tenant_id=effective_tenant_id)

    rule = await query.first()

    if not rule:
        return Fail(code=404, msg="规则不存在")

    try:
        if version_no:
            version = await rule_version_controller.get_version_by_no(
                rule_code=rule.rule_code,
                version_no=version_no,
                tenant_id=rule.tenant_id
            )
        else:
            if rule.latest_version_id:
                version_obj = await RuleVersion.filter(
                    id=rule.latest_version_id,
                    deleted=0
                ).first()
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
