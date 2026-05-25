"""
规则导入接口 - 处理CSV导入的API端点
"""
import json
import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, Query

from app.core.dependency import AuthControl, build_tenant_query
from app.log import logger
from app.models.rule_management import RuleInfo, RuleVersion
from app.schemas.base import Fail, Success
from app.schemas.rule_management import (
    CurlImportApplyRequest,
    CurlImportPreviewRequest,
    CurlImportSaveConfigRequest,
    FilePreviewRequest,
    ImportApplyRequest,
)
from app.services.rule_management.csv_import_core import (
    CsvImportCore,
    ImportConfig,
    ImportStats,
)
from app.services.rule_management.rule_service import (
    NoChangeException,
    VersionConflictException,
    rule_service,
)

router = APIRouter()


def _parse_import_config(config_str: Optional[str]) -> Optional[Dict[str, Any]]:
    """解析导入配置"""
    if not config_str:
        return None
    try:
        config = json.loads(config_str)
        # 支持新配置格式
        if "primary_keys" in config or "sync_fields" in config:
            return config
        # 兼容旧配置格式
        if "field_mapping" in config and "unique_keys" in config:
            return {
                "primary_keys": config.get("unique_keys", []),
                "sync_fields": [
                    m.get("original_field", "")
                    for m in config.get("field_mapping", [])
                    if m.get("is_import", True)
                ],
            }
        return config
    except Exception:
        return None


async def _get_rule_with_tenant_check(
    rule_id: int, tenant_id: int, token: str
) -> Optional[RuleInfo]:
    """获取规则并验证租户权限"""
    current_user = await AuthControl.is_authed(token)
    tenant_query = build_tenant_query(current_user, tenant_id)
    effective_tenant_id = tenant_query.get("tenant_id", 0)

    query = RuleInfo.filter(id=rule_id, deleted=0)
    if effective_tenant_id > 0:
        query = query.filter(tenant_id=effective_tenant_id)

    return await query.first()


async def _get_existing_data_and_headers(
    rule: RuleInfo,
) -> tuple[List[Dict[str, Any]], List[str], bool]:
    """
    获取规则的现有数据和表头

    Returns:
        (existing_data, existing_headers, is_first_import)
    """
    existing_data: List[Dict[str, Any]] = []
    existing_headers: List[str] = []
    is_first_import = True

    if rule.latest_version_id:
        version = await RuleVersion.filter(
            id=rule.latest_version_id, deleted=0
        ).first()
        if version:
            content_json = await rule_service._get_content_json(version)
            if content_json:
                existing_headers = content_json.get("headers", [])
                data = content_json.get("data", [])
                # 转换为字典列表
                for row in data:
                    row_dict = {
                        header: row[i] if i < len(row) else ""
                        for i, header in enumerate(existing_headers)
                    }
                    existing_data.append(row_dict)
                is_first_import = False

    return existing_data, existing_headers, is_first_import


async def _save_primary_keys_config(
    rule: RuleInfo, primary_keys: List[str]
) -> None:
    """
    保存主键配置到规则config中

    只保存primary_keys，sync_fields不保存（每次实时从表头获取）
    """
    existing_config = _parse_import_config(rule.config) or {}

    # 只更新主键配置，保留其他配置（如curl_config）
    existing_config["primary_keys"] = primary_keys
    # 删除旧的sync_fields（如果存在）
    existing_config.pop("sync_fields", None)

    rule.config = json.dumps(existing_config, indent=2, ensure_ascii=False)
    await rule.save()

    logger.info(
        "自动保存主键配置",
        rule_id=rule.id,
        primary_keys=primary_keys,
    )


async def _save_import_result(
    rule: RuleInfo,
    merged_data: List[Dict[str, Any]],
    all_headers: List[str],
    stats: ImportStats,
    current_md5: str,
    remark: Optional[str] = None,
    import_type: str = "CSV",
) -> Dict[str, Any]:
    """
    保存导入结果为新版本

    Args:
        rule: 规则对象
        merged_data: 合并后的数据
        all_headers: 合并后的表头（保持正确的字段顺序）
        stats: 导入统计
        current_md5: 当前MD5
        remark: 备注
        import_type: 导入类型

    Returns:
        导入结果字典
    """
    from app.controllers.rule_management import rule_version_controller

    # 转换为CSV格式
    if merged_data:
        csv_data = [
            [str(row.get(h, "")) for h in all_headers] for row in merged_data
        ]
    else:
        all_headers = []
        csv_data = []

    content_json = {"headers": all_headers, "data": csv_data}

    # 构建备注
    if not remark:
        if stats.added_count > 0 and stats.updated_count == 0:
            remark = f"{import_type}首次导入：新增{stats.added_count}条，跳过{stats.skipped_count}条"
        else:
            remark = f"{import_type}增量导入：新增{stats.added_count}条，更新{stats.updated_count}条，跳过{stats.skipped_count}条"
        if stats.failed_count > 0:
            remark += f"，失败{stats.failed_count}条"

    # 保存新版本
    new_version = await rule_version_controller.save_version(
        rule=rule,
        content_json=content_json,
        current_md5=current_md5,
        remark=remark,
    )

    logger.info(
        f"{import_type}导入成功",
        rule_id=rule.id,
        version_no=new_version.version_no,
        added=stats.added_count,
        updated=stats.updated_count,
        skipped=stats.skipped_count,
        failed=stats.failed_count,
    )

    return {
        "version_no": new_version.version_no,
        "added_count": stats.added_count,
        "updated_count": stats.updated_count,
        "skipped_count": stats.skipped_count,
        "failed_count": stats.failed_count,
        "failed_reasons": stats.failed_reasons,
        "total_count": len(merged_data),
        "new_md5": new_version.content_md5,
    }


# ============ CSV 文件导入接口 ============


@router.post("/rule/import/file/preview", summary="预览CSV导入")
async def preview_file_import(
    request: FilePreviewRequest,
    token: str = Header(..., description="token验证"),
):
    """
    预览CSV导入 - 返回CSV表头、预览数据、是否是首次导入等信息

    如果请求中提供了primary_keys，会自动保存主键配置
    """
    await AuthControl.is_authed(token)

    rule = await RuleInfo.filter(id=request.rule_id, deleted=0).first()
    if not rule:
        return Fail(code=404, msg="规则不存在")

    existing_config = _parse_import_config(rule.config)
    existing_headers = []
    is_first_import = True

    if rule.latest_version_id:
        version = await RuleVersion.filter(
            id=rule.latest_version_id, deleted=0
        ).first()
        if version:
            content_json = await rule_service._get_content_json(version)
            if content_json:
                existing_headers = content_json.get("headers", [])
                is_first_import = False

    # 解析CSV获取预览数据
    csv_headers, csv_data = CsvImportCore.parse_csv(request.content)

    # 自动保存主键配置（如果提供了）
    primary_keys = existing_config.get("primary_keys", []) if existing_config else []
    if hasattr(request, "primary_keys") and request.primary_keys:
        primary_keys = request.primary_keys
        await _save_primary_keys_config(rule, primary_keys)

    # 合并表头：保留旧表头顺序，追加新字段
    merged_headers = CsvImportCore.merge_headers(existing_headers, set(csv_headers))

    # 同步字段从合并后的表头获取（排除主键）
    sync_fields = [h for h in merged_headers if h not in primary_keys]

    return Success(
        data={
            "csv_headers": csv_headers,
            "existing_headers": existing_headers,
            "merged_headers": merged_headers,  # 返回合并后的表头
            "row_count": len(csv_data),
            "preview_data": csv_data[:10],
            "is_first_import": is_first_import,
            "primary_keys": primary_keys,
            "sync_fields": sync_fields,
            "allow_add_new": True,  # 默认允许新增
        }
    )


@router.get("/rule/import/config", summary="获取导入配置")
async def get_import_config(
    rule_id: int = Query(..., description="规则ID"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """
    获取规则的导入配置 - 仅返回主键配置

    同步字段不保存，每次实时从表头获取
    """
    await AuthControl.is_authed(token)

    rule = await RuleInfo.filter(id=rule_id, deleted=0).first()
    if not rule:
        return Fail(code=404, msg="规则不存在")

    config = _parse_import_config(rule.config)
    primary_keys = config.get("primary_keys", []) if config else []

    return Success(data={"primary_keys": primary_keys})


@router.post("/rule/import/apply", summary="执行CSV导入")
async def apply_import(
    request: ImportApplyRequest,
    token: str = Header(..., description="token验证"),
):
    """
    执行CSV导入 - 根据配置进行增量更新，返回详细的导入统计

    会自动保存主键配置到规则config中
    """
    rule = await _get_rule_with_tenant_check(
        request.rule_id, request.tenant_id, token
    )
    if not rule:
        return Fail(code=404, msg="规则不存在")

    # 获取现有数据
    existing_data, existing_headers, is_first_import = (
        await _get_existing_data_and_headers(rule)
    )

    # 自动保存主键配置
    if request.config.primary_keys:
        await _save_primary_keys_config(rule, request.config.primary_keys)

    # 执行导入（使用新的核心模块）
    config = ImportConfig(
        primary_keys=request.config.primary_keys,
        sync_fields=request.config.sync_fields,
    )

    try:
        merged_data, stats, all_headers = CsvImportCore.execute_import(
            csv_content=request.content,
            existing_data=existing_data,
            existing_headers=existing_headers,
            config=config,
            is_first_import=is_first_import,
            allow_add_new=request.allow_add_new,
        )

        # 保存结果
        result = await _save_import_result(
            rule=rule,
            merged_data=merged_data,
            all_headers=all_headers,
            stats=stats,
            current_md5=request.current_md5,
            remark=request.remark,
            import_type="CSV",
        )

        return Success(data=result)

    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except VersionConflictException:
        return Fail(code=409, msg="规则已被他人修改，请刷新后重试")
    except NoChangeException:
        # 内容无变化时返回成功，但标记为无变化
        return Success(
            data={
                "version_no": rule.latest_version_id,
                "added_count": 0,
                "updated_count": 0,
                "skipped_count": 0,
                "failed_count": 0,
                "total_count": 0,
                "new_md5": request.current_md5 if request.current_md5 else "",
                "no_change": True,
                "message": "当前内容没有变化，无需保存新版本",
            }
        )
    except Exception as e:
        logger.error("CSV导入失败", error=str(e))
        return Fail(code=500, msg=f"导入失败: {str(e)}")


# ============ CURL 导入相关接口 ============


@router.post("/rule/import/curl/preview", summary="预览CURL导入")
async def preview_curl_import(
    request: CurlImportPreviewRequest,
    token: str = Header(..., description="token验证"),
):
    """预览CURL导入 - 执行CURL请求并返回CSV数据预览"""
    await AuthControl.is_authed(token)

    try:
        from app.services.rule_management.curl_import_service import (
            CurlImportService,
        )

        curl_config = request.curl_config

        # 构建配置
        config = {
            "global_vars": curl_config.get("global_vars", {}),
            "data_root_path": curl_config.get("data_root_path", "$.data"),
            "level_config": {},
            "curl_commands": curl_config.get("curl_commands", []),
        }

        # 转换层级配置
        level_config = curl_config.get("level_config", {})
        for level_name, level_cfg in level_config.items():
            fields = level_cfg.get("fields", [])
            config["level_config"][level_name] = {
                "source": level_cfg.get("source", {}),
                "fields": [
                    {
                        "csv_header": f.get("csv_header", ""),
                        "jsonpath": f.get("jsonpath", "$"),
                    }
                    for f in fields
                ],
                "children_jsonpath": level_cfg.get("children_jsonpath"),
                "params": level_cfg.get("params", {}),
            }

        # 创建服务并执行
        service = CurlImportService(config)
        result = await service.fetch_data()

        return Success(
            data={
                "headers": result["headers"],
                "data": result["data"],
                "row_count": result["row_count"],
                "mode": result["mode"],
                "preview_data": result["data"][:10] if result["data"] else [],
            }
        )

    except Exception as e:
        logger.error("CURL导入预览失败", error=str(e))
        return Fail(code=500, msg=f"CURL导入预览失败: {str(e)}")


@router.post("/rule/import/curl/config", summary="保存CURL导入配置")
async def save_curl_import_config(
    request: CurlImportSaveConfigRequest,
    token: str = Header(..., description="token验证"),
):
    """保存CURL导入配置 - 自动保存curl_config到规则配置中，保留原有主键配置"""
    current_user = await AuthControl.is_authed(token)
    tenant_query = build_tenant_query(current_user, request.tenant_id)
    effective_tenant_id = tenant_query.get("tenant_id", 0)

    query = RuleInfo.filter(id=request.rule_id, deleted=0)
    if effective_tenant_id > 0:
        query = query.filter(tenant_id=effective_tenant_id)

    rule = await query.first()
    if not rule:
        return Fail(code=404, msg="规则不存在")

    curl_config_dict = request.curl_config

    # 构建curl配置
    curl_config = {
        "description": curl_config_dict.get("description", ""),
        "global_vars": curl_config_dict.get("global_vars", {}),
        "data_root_path": curl_config_dict.get("data_root_path", "$.data"),
        "level_config": {},
        "curl_commands": curl_config_dict.get("curl_commands", []),
    }

    # 转换层级配置
    level_config = curl_config_dict.get("level_config", {})
    for level_name, level_cfg in level_config.items():
        fields = level_cfg.get("fields", [])
        curl_config["level_config"][level_name] = {
            "source": level_cfg.get("source", {}),
            "fields": [
                {
                    "csv_header": f.get("csv_header", ""),
                    "jsonpath": f.get("jsonpath", "$"),
                }
                for f in fields
            ],
            "children_jsonpath": level_cfg.get("children_jsonpath"),
            "params": level_cfg.get("params", {}),
        }

    # 获取现有配置
    existing_config = _parse_import_config(rule.config) or {}

    # 构建配置（只保存curl_config，保留原有的primary_keys）
    config = {
        "import_type": "curl",
        "primary_keys": existing_config.get("primary_keys", []),
        "curl_config": curl_config,
    }

    rule.config = json.dumps(config, indent=2, ensure_ascii=False)
    await rule.save()

    logger.info(
        "保存CURL导入配置成功",
        rule_id=rule.id,
        rule_code=rule.rule_code,
    )

    return Success(msg="配置保存成功")


@router.get("/rule/import/curl/config", summary="获取CURL导入配置")
async def get_curl_import_config(
    rule_id: int = Query(..., description="规则ID"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """获取CURL导入配置 - 仅返回主键配置和curl_config"""
    await AuthControl.is_authed(token)

    rule = await RuleInfo.filter(id=rule_id, deleted=0).first()
    if not rule:
        return Fail(code=404, msg="规则不存在")

    config = _parse_import_config(rule.config)
    if not config or config.get("import_type") != "curl":
        return Success(
            data={
                "primary_keys": [],
                "curl_config": {},
            }
        )

    return Success(
        data={
            "primary_keys": config.get("primary_keys", []),
            "curl_config": config.get("curl_config", {}),
        }
    )


@router.post("/rule/import/curl/apply", summary="执行CURL导入")
async def apply_curl_import(
    request: CurlImportApplyRequest,
    token: str = Header(..., description="token验证"),
):
    """
    执行CURL导入

    流程：
    1. 执行CURL请求获取数据
    2. 生成临时CSV文件
    3. 使用统一的CSV导入逻辑处理
    4. 删除临时文件
    5. 保存结果为新版本

    会自动保存主键配置到规则config中
    """
    rule = await _get_rule_with_tenant_check(
        request.rule_id, request.tenant_id, token
    )
    if not rule:
        return Fail(code=404, msg="规则不存在")

    # 使用请求中的curl_config（由前端传入）
    curl_config = request.curl_config

    # 使用请求中的主键（由前端公共配置传入）
    primary_keys = request.primary_keys
    sync_fields = request.sync_fields

    if not primary_keys:
        return Fail(code=400, msg="请配置主键字段")

    temp_file_path = None

    try:
        from app.services.rule_management.curl_import_service import (
            CurlImportService,
        )

        # 1. 执行CURL请求获取数据
        service = CurlImportService(curl_config)
        curl_result = await service.fetch_data()

        headers = curl_result["headers"]
        csv_data = curl_result["data"]

        if not csv_data:
            return Fail(code=400, msg="CURL请求未返回数据")

        # 2. 生成临时CSV文件
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            # 写入表头
            f.write(",".join(headers) + "\n")
            # 写入数据
            for row in csv_data:
                f.write(",".join(row) + "\n")
            temp_file_path = f.name

        logger.info(
            "CURL数据已保存到临时文件",
            temp_file=temp_file_path,
            rows=len(csv_data),
        )

        # 3. 读取临时文件内容
        with open(temp_file_path, "r", encoding="utf-8") as f:
            csv_content = f.read()

        # 4. 获取现有数据
        existing_data, existing_headers, is_first_import = (
            await _get_existing_data_and_headers(rule)
        )

        # 5. 自动保存主键配置
        await _save_primary_keys_config(rule, primary_keys)

        # 6. 执行导入（使用新的核心模块）
        config = ImportConfig(
            primary_keys=primary_keys,
            sync_fields=sync_fields,
        )

        merged_data, stats, all_headers = CsvImportCore.execute_import(
            csv_content=csv_content,
            existing_data=existing_data,
            existing_headers=existing_headers,
            config=config,
            is_first_import=is_first_import,
        )

        # 7. 保存结果
        result = await _save_import_result(
            rule=rule,
            merged_data=merged_data,
            all_headers=all_headers,
            stats=stats,
            current_md5=request.current_md5,
            remark=request.remark,
            import_type="CURL",
        )

        return Success(data=result)

    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except VersionConflictException:
        return Fail(code=409, msg="规则已被他人修改，请刷新后重试")
    except NoChangeException:
        return Fail(code=400, msg="当前内容没有变化，无需保存新版本")
    except Exception as e:
        logger.error("CURL导入失败", error=str(e))
        return Fail(code=500, msg=f"CURL导入失败: {str(e)}")
    finally:
        # 8. 删除临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info("临时文件已删除", temp_file=temp_file_path)
            except Exception as e:
                logger.warning(
                    "删除临时文件失败", temp_file=temp_file_path, error=str(e)
                )
