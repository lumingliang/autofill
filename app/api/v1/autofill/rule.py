"""
规则管理接口

参考 depts.py 简洁风格：
- 直接在路由函数中调用 Service 层
- 不使用 API 类包装
- 认证由中间件统一处理
- 租户过滤由 Repository 层自动处理
"""
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import PlainTextResponse

from app.log import logger
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.rule_management import (
    RuleCreate,
    RuleUpdate,
    RuleVersionSave,
    RuleVersionRollback,
    RuleListQuery,
    RuleGetQuery,
    RuleDeleteQuery,
    RuleVersionsQuery,
    RuleExportQuery,
)
from app.services.rule_management.rule_service import (
    rule_service,
    VersionConflictException,
    NoChangeException
)

router = APIRouter()


@router.get("/rule/list", summary="规则列表")
async def list_rules(
    query: RuleListQuery = Depends(),
):
    """获取规则列表"""
    total, rules = await rule_service.list_rules(
        app_name=query.app_name,
        keyword=query.keyword,
        status=query.status,
        page=query.page,
        page_size=query.page_size
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

    return SuccessExtra(
        data=data,
        total=total,
        page=query.page,
        page_size=query.page_size
    )


@router.get("/rule/get", summary="规则详情")
async def get_rule(
    query: RuleGetQuery = Depends(),
):
    """获取规则详情（包含最新版本）"""
    rule = await rule_service.get_rule_by_id(rule_id=query.id)

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
    rule_in: RuleCreate,
):
    """创建新规则

    租户ID由 Repository 层自动从上下文获取并注入
    """
    if not rule_in.app_name:
        return Fail(code=400, msg="应用名称不能为空")

    try:
        rule = await rule_service.create_rule(
            rule_name=rule_in.rule_name,
            desc=rule_in.desc,
            rule_code=rule_in.rule_code,
            app_name=rule_in.app_name
        )
        return Success(data=await rule.to_dict())
    except ValueError as e:
        return Fail(code=400, msg=str(e))


@router.post("/rule/update", summary="更新规则")
async def update_rule(
    rule_in: RuleUpdate,
):
    """更新规则信息"""
    try:
        rule = await rule_service.update_rule(
            rule_id=rule_in.id,
            rule_name=rule_in.rule_name if rule_in.rule_name else None,
            desc=rule_in.desc if rule_in.desc else None,
            status=rule_in.status if rule_in.status >= 0 else None
        )
        return Success(data=await rule.to_dict())
    except ValueError as e:
        return Fail(code=400, msg=str(e))


@router.delete("/rule/delete", summary="删除规则")
async def delete_rule(
    query: RuleDeleteQuery = Depends(),
):
    """删除规则（软删除）"""
    existing_rule = await rule_service.get_rule_by_id(rule_id=query.id)

    if not existing_rule:
        return Fail(code=404, msg="规则不存在")

    try:
        await rule_service.delete_rule(rule_code=existing_rule.rule_code)
        return Success(msg="删除成功")
    except ValueError as e:
        return Fail(code=400, msg=str(e))


@router.post("/rule/save", summary="保存规则版本")
async def save_version(
    version_in: RuleVersionSave,
):
    """保存新版本（带乐观锁）"""
    rule = await rule_service.get_rule_by_id(rule_id=version_in.rule_id)

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
    query: RuleVersionsQuery = Depends(),
):
    """获取版本历史列表"""
    rule = await rule_service.get_rule_by_id(rule_id=query.rule_id)

    if not rule:
        return Fail(code=404, msg="规则不存在")

    try:
        total, versions = await rule_service.get_version_history(
            rule_code=rule.rule_code,
            page=query.page,
            page_size=query.page_size
        )
        return SuccessExtra(data=versions, total=total, page=query.page, page_size=query.page_size)
    except ValueError as e:
        return Fail(code=404, msg=str(e))


@router.get("/rule/version", summary="获取指定版本")
async def get_version_by_no(
    rule_id: int = Query(..., description="规则ID"),
    version_no: int = Query(..., description="版本号"),
):
    """获取指定版本详情"""
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
    rollback_in: RuleVersionRollback,
):
    """回滚到指定版本"""
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


@router.get("/rule/export", summary="导出CSV")
async def export_csv(
    query: RuleExportQuery = Depends(),
):
    """导出CSV文件"""
    rule = await rule_service.get_rule_by_id(rule_id=query.rule_id)

    if not rule:
        return Fail(code=404, msg="规则不存在")

    try:
        if query.version_no:
            version = await rule_service.get_version_by_no(
                rule_code=rule.rule_code,
                version_no=query.version_no
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
