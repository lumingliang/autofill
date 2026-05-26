"""
规则导入接口 - 处理CSV导入的API端点

优化后的实现：
1. 直接落库到 seekdb
2. 使用简洁的增量导入算法
3. 不再使用旧的内存导入逻辑
"""
import csv
import io
import json
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
from app.services.rule_management.csv_import_seekdb import (
    CsvImportSeekdbService,
)
from app.services.rule_management.rule_service import (
    NoChangeException,
    VersionConflictException,
    rule_service,
)
from app.services.storage.seekdb_service import seekdb_service

router = APIRouter()


def _parse_import_config(config_str: Optional[str]) -> Optional[Dict[str, Any]]:
    """解析导入配置"""
    if not config_str:
        return None
    try:
        config = json.loads(config_str)
        if "primary_keys" in config or "sync_fields" in config:
            return config
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


def _build_collection_name(rule_id: int, rule_code: str, version_no: int) -> str:
    """构建 seekdb 集合名称"""
    return f"rule_{rule_id}_{rule_code}_v{version_no}"


def _get_collection_name_for_latest(rule_id: int, rule_code: str, version_no: int) -> str:
    """获取最新版本的集合名称"""
    return f"rule_{rule_id}_{rule_code}_v{version_no}"


async def _is_first_import(rule: RuleInfo) -> bool:
    """判断是否是首次导入"""
    return rule.latest_version_id is None


async def _get_existing_headers(rule: RuleInfo) -> tuple[List[str], bool]:
    """
    获取规则的现有表头和判断是否首次导入

    Returns:
        (existing_headers, is_first_import)
    """
    if rule.latest_version_id:
        version = await RuleVersion.filter(
            id=rule.latest_version_id, deleted=0
        ).first()
        if version:
            content_json = await rule_service._get_content_json(version)
            if content_json and content_json.get("headers"):
                return content_json.get("headers", []), False
    return [], True


async def _save_primary_keys_config(
    rule: RuleInfo, primary_keys: List[str]
) -> None:
    """保存主键配置到规则config中"""
    existing_config = _parse_import_config(rule.config) or {}
    existing_config["primary_keys"] = primary_keys
    existing_config.pop("sync_fields", None)
    rule.config = json.dumps(existing_config, indent=2, ensure_ascii=False)
    await rule.save()
    logger.info("自动保存主键配置", rule_id=rule.id, primary_keys=primary_keys)


def _parse_csv_content(csv_content: str) -> tuple[List[str], List[Dict[str, str]]]:
    """解析CSV内容"""
    if not csv_content or not csv_content.strip():
        return [], []
    reader = csv.DictReader(io.StringIO(csv_content.strip()))
    raw_headers = reader.fieldnames or []
    headers = [h.strip() for h in raw_headers]
    header_mapping = {raw: stripped for raw, stripped in zip(raw_headers, headers)}
    data = []
    for row in reader:
        data.append({header_mapping.get(k, k): v for k, v in row.items()})
    return headers, data


def _merge_headers(existing: List[str], new: List[str]) -> List[str]:
    """合并表头"""
    existing_set = set(existing)
    merged = list(existing)
    for h in new:
        if h not in existing_set:
            merged.append(h)
    return merged


async def _save_version_from_seekdb(
    rule: RuleInfo,
    collection_name: str,
    current_md5: str,
    remark: Optional[str] = None,
    import_type: str = "CSV"
) -> Dict[str, Any]:
    """从seekdb保存版本"""
    from app.controllers.rule_management import rule_version_controller

    collection = seekdb_service.get_or_create_collection(collection_name)
    results = collection.get()

    headers = []
    data = []

    if results and results.get("metadatas"):
        headers = results["metadatas"][0].get("headers", [])
        for metadata in results["metadatas"]:
            row_data = metadata.get("data", {})
            row_list = [row_data.get(h, "") for h in headers]
            data.append(row_list)

    if not headers:
        headers = []
        data = []

    content_json = {"headers": headers, "data": data}

    if not remark:
        remark = f"{import_type}导入"

    new_version = await rule_version_controller.save_version(
        rule=rule,
        content_json=content_json,
        current_md5=current_md5,
        remark=remark,
    )

    return {
        "version_no": new_version.version_no,
        "new_md5": new_version.content_md5,
    }


@router.post("/rule/import/file/preview", summary="预览CSV导入")
async def preview_file_import(
    request: FilePreviewRequest,
    token: str = Header(..., description="token验证"),
):
    """预览CSV导入 - 返回CSV表头、预览数据、是否是首次导入等信息"""
    await AuthControl.is_authed(token)

    rule = await RuleInfo.filter(id=request.rule_id, deleted=0).first()
    if not rule:
        return Fail(code=404, msg="规则不存在")

    existing_headers, is_first_import = await _get_existing_headers(rule)

    csv_headers, csv_data = _parse_csv_content(request.content)

    primary_keys = []
    existing_config = _parse_import_config(rule.config)
    if existing_config:
        primary_keys = existing_config.get("primary_keys", [])

    if hasattr(request, "primary_keys") and request.primary_keys:
        primary_keys = request.primary_keys
        await _save_primary_keys_config(rule, primary_keys)

    merged_headers = _merge_headers(existing_headers, csv_headers)
    sync_fields = [h for h in merged_headers if h not in primary_keys]

    return Success(
        data={
            "csv_headers": csv_headers,
            "existing_headers": existing_headers,
            "merged_headers": merged_headers,
            "row_count": len(csv_data),
            "preview_data": csv_data[:10],
            "is_first_import": is_first_import,
            "primary_keys": primary_keys,
            "sync_fields": sync_fields,
            "allow_add_new": True,
        }
    )


@router.get("/rule/import/config", summary="获取导入配置")
async def get_import_config(
    rule_id: int = Query(..., description="规则ID"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """获取规则的导入配置"""
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
    """执行CSV导入 - 直接落库到seekdb"""
    rule = await _get_rule_with_tenant_check(
        request.rule_id, request.tenant_id, token
    )
    if not rule:
        return Fail(code=404, msg="规则不存在")

    if request.config.primary_keys:
        await _save_primary_keys_config(rule, request.config.primary_keys)

    is_first_import = await _is_first_import(rule)

    version_no = 1
    source_collection_name = None
    if rule.latest_version_id:
        version = await RuleVersion.filter(
            id=rule.latest_version_id, deleted=0
        ).first()
        if version:
            version_no = version.version_no + 1
            # 增量导入时，从最新版本的集合读取旧数据
            source_collection_name = _build_collection_name(rule.id, rule.rule_code, version.version_no)

    collection_name = _build_collection_name(rule.id, rule.rule_code, version_no)

    try:
        result = await CsvImportSeekdbService.execute_import(
            collection_name=collection_name,
            csv_content=request.content,
            rule_id=rule.id,
            version_no=version_no,
            tenant_id=rule.tenant_id,
            app_name=rule.app_name,
            rule_code=rule.rule_code,
            primary_keys=request.config.primary_keys or [],
            sync_fields=request.config.sync_fields or [],
            is_first_import=is_first_import,
            allow_add_new=request.allow_add_new,
            source_collection_name=source_collection_name,
        )

        if "error" in result:
            return Fail(code=400, msg=result["error"])

        version_result = await _save_version_from_seekdb(
            rule=rule,
            collection_name=collection_name,
            current_md5=request.current_md5,
            remark=request.remark,
            import_type="CSV"
        )

        return Success(
            data={
                "version_no": version_result["version_no"],
                "added_count": result["added_count"],
                "updated_count": result["updated_count"],
                "skipped_count": result["skipped_count"],
                "total_count": result["total_count"],
                "new_md5": version_result["new_md5"],
            }
        )

    except VersionConflictException:
        return Fail(code=409, msg="规则已被他人修改，请刷新后重试")
    except Exception as e:
        logger.error("CSV导入失败", error=str(e))
        return Fail(code=500, msg=f"导入失败: {str(e)}")


@router.post("/rule/import/curl/preview", summary="预览CURL导入")
async def preview_curl_import(
    request: CurlImportPreviewRequest,
    token: str = Header(..., description="token验证"),
):
    """预览CURL导入"""
    await AuthControl.is_authed(token)

    try:
        from app.services.rule_management.curl_import_service import (
            CurlImportService,
        )

        curl_config = request.curl_config
        config = {
            "global_vars": curl_config.get("global_vars", {}),
            "data_root_path": curl_config.get("data_root_path", "$.data"),
            "level_config": {},
            "curl_commands": curl_config.get("curl_commands", []),
        }

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
    """保存CURL导入配置"""
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
    curl_config = {
        "description": curl_config_dict.get("description", ""),
        "global_vars": curl_config_dict.get("global_vars", {}),
        "data_root_path": curl_config_dict.get("data_root_path", "$.data"),
        "level_config": {},
        "curl_commands": curl_config_dict.get("curl_commands", []),
    }

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

    existing_config = _parse_import_config(rule.config) or {}
    config = {
        "import_type": "curl",
        "primary_keys": existing_config.get("primary_keys", []),
        "curl_config": curl_config,
    }

    rule.config = json.dumps(config, indent=2, ensure_ascii=False)
    await rule.save()

    logger.info("保存CURL导入配置成功", rule_id=rule.id, rule_code=rule.rule_code)

    return Success(msg="配置保存成功")


@router.get("/rule/import/curl/config", summary="获取CURL导入配置")
async def get_curl_import_config(
    rule_id: int = Query(..., description="规则ID"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """获取CURL导入配置"""
    await AuthControl.is_authed(token)

    rule = await RuleInfo.filter(id=rule_id, deleted=0).first()
    if not rule:
        return Fail(code=404, msg="规则不存在")

    config = _parse_import_config(rule.config)
    if not config or config.get("import_type") != "curl":
        return Success(data={"primary_keys": [], "curl_config": {}})

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
    """执行CURL导入 - 获取数据后落库到seekdb"""
    rule = await _get_rule_with_tenant_check(
        request.rule_id, request.tenant_id, token
    )
    if not rule:
        return Fail(code=404, msg="规则不存在")

    primary_keys = request.primary_keys
    sync_fields = request.sync_fields

    if not primary_keys:
        return Fail(code=400, msg="请配置主键字段")

    temp_file_path = None

    try:
        from app.services.rule_management.curl_import_service import (
            CurlImportService,
        )

        service = CurlImportService(request.curl_config)
        curl_result = await service.fetch_data()

        headers = curl_result["headers"]
        csv_data = curl_result["data"]

        if not csv_data:
            return Fail(code=400, msg="CURL请求未返回数据")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(",".join(headers) + "\n")
            for row in csv_data:
                f.write(",".join(row) + "\n")
            temp_file_path = f.name

        with open(temp_file_path, "r", encoding="utf-8") as f:
            csv_content = f.read()

        await _save_primary_keys_config(rule, primary_keys)

        is_first_import = await _is_first_import(rule)

        version_no = 1
        if rule.latest_version_id:
            version = await RuleVersion.filter(
                id=rule.latest_version_id, deleted=0
            ).first()
            if version:
                version_no = version.version_no + 1

        collection_name = _build_collection_name(rule.id, rule.rule_code, version_no)

        result = await CsvImportSeekdbService.execute_import(
            collection_name=collection_name,
            csv_content=csv_content,
            rule_id=rule.id,
            version_no=version_no,
            tenant_id=rule.tenant_id,
            app_name=rule.app_name,
            rule_code=rule.rule_code,
            primary_keys=primary_keys,
            sync_fields=sync_fields,
            is_first_import=is_first_import,
            allow_add_new=True,
        )

        if "error" in result:
            return Fail(code=400, msg=result["error"])

        version_result = await _save_version_from_seekdb(
            rule=rule,
            collection_name=collection_name,
            current_md5=request.current_md5,
            remark=request.remark,
            import_type="CURL"
        )

        return Success(
            data={
                "version_no": version_result["version_no"],
                "added_count": result["added_count"],
                "updated_count": result["updated_count"],
                "skipped_count": result["skipped_count"],
                "total_count": result["total_count"],
                "new_md5": version_result["new_md5"],
            }
        )

    except VersionConflictException:
        return Fail(code=409, msg="规则已被他人修改，请刷新后重试")
    except Exception as e:
        logger.error("CURL导入失败", error=str(e))
        return Fail(code=500, msg=f"CURL导入失败: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
