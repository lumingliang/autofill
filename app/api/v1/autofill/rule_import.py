"""
规则导入接口 - 处理CSV导入的API端点

参考 depts.py 简洁风格：
- 直接在路由函数中调用 Service 层
- 不使用 API 类包装
- 认证由中间件统一处理
"""
import csv
import io
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.log import logger
from app.schemas.base import Fail, Success
from app.schemas.rule_management import (
    CurlImportApplyRequest,
    CurlImportPreviewRequest,
    CurlImportSaveConfigRequest,
    FilePreviewRequest,
    ImportApplyRequest,
    ImportConfigQuery,
)
from app.services.rule_management.csv_import_seekdb import (
    CsvImportSeekdbService,
    build_collection_name,
)
from app.services.rule_management.curl_import_engine import CurlImportEngine
from app.services.rule_management.rule_service import (
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


async def _get_rule(rule_id: int) -> Optional[Any]:
    """获取规则 - 租户过滤由 Repository 层通过 TenantContext 自动处理"""
    return await rule_service.get_rule_by_id(rule_id=rule_id)


async def _prepare_import_version(rule: Any) -> tuple[int, Optional[str]]:
    """准备导入版本信息，返回版本号和源集合名称"""
    version_no = 1
    source_collection_name = None

    if rule.latest_version_id:
        version = await rule_service.get_version_by_id(version_id=rule.latest_version_id)
        if version:
            version_no = version.version_no + 1
            source_collection_name = build_collection_name(rule.id, rule.rule_code, version.version_no)

    return version_no, source_collection_name


async def _get_existing_headers(rule: Any) -> tuple[List[str], bool]:
    """获取规则的现有表头和判断是否首次导入"""
    if rule.latest_version_id:
        version = await rule_service.get_version_by_id(version_id=rule.latest_version_id)
        if version:
            content_json = await rule_service.get_content_json(version)
            if content_json and content_json.get("headers"):
                return content_json.get("headers", []), False
    return [], True


async def _save_primary_keys_config(rule: Any, primary_keys: List[str]) -> None:
    """保存主键配置到规则config中"""
    existing_config = _parse_import_config(rule.config) or {}
    existing_config["primary_keys"] = primary_keys
    existing_config.pop("sync_fields", None)

    await rule_service.update_rule_config(
        rule_id=rule.id,
        config=existing_config
    )
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


async def _save_version_record(
    rule: Any,
    collection_name: str,
    headers: List[str],
    doc_count: int,
    remark: Optional[str] = None,
) -> Dict[str, Any]:
    """创建版本记录"""
    if not remark:
        remark = "CSV导入"

    new_version = await rule_service.create_version_record(
        rule=rule,
        collection_name=collection_name,
        headers=headers,
        doc_count=doc_count,
        remark=remark,
    )

    return {
        "version_no": new_version.version_no,
        "new_md5": new_version.content_md5,
    }


async def _execute_csv_import_core(
    rule: Any,
    csv_content: str,
    primary_keys: List[str],
    sync_fields: Optional[List[str]] = None,
    remark: Optional[str] = None,
    allow_add_new: bool = True,
) -> Dict[str, Any]:
    """执行CSV导入的核心逻辑"""
    version_no, source_collection_name = await _prepare_import_version(rule)
    collection_name = build_collection_name(rule.id, rule.rule_code, version_no)

    if sync_fields is None:
        csv_headers, _ = CsvImportSeekdbService.parse_csv_streaming(csv_content)
        sync_fields = [h for h in csv_headers if h not in primary_keys]

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
        source_collection_name=source_collection_name,
        allow_add_new=allow_add_new,
    )

    if "error" in result:
        return {"success": False, "error": result["error"]}

    if not remark:
        if result["added_count"] > 0 and result["updated_count"] == 0:
            remark = f"CSV导入：新增{result['added_count']}条，跳过{result['skipped_count']}条"
        else:
            remark = f"CSV导入：新增{result['added_count']}条，更新{result['updated_count']}条，跳过{result['skipped_count']}条"

    version_result = await _save_version_record(
        rule=rule,
        collection_name=collection_name,
        headers=result.get("headers", []),
        doc_count=result.get("total_count", 0),
        remark=remark,
    )

    logger.info(
        "CSV导入成功",
        rule_id=rule.id,
        version_no=version_result["version_no"],
        added=result["added_count"],
        updated=result["updated_count"],
    )

    return {
        "success": True,
        "data": {
            "headers": result.get("headers", []),
            "row_count": result.get("total_count", 0),
            "version_no": version_result["version_no"],
            "added_count": result["added_count"],
            "updated_count": result["updated_count"],
            "skipped_count": result["skipped_count"],
            "total_count": result["total_count"],
            "new_md5": version_result["new_md5"],
        }
    }


async def _execute_import_from_rows_core(
    rule: Any,
    headers: List[str],
    rows: List[Dict[str, Any]],
    primary_keys: List[str],
    sync_fields: Optional[List[str]] = None,
    remark: Optional[str] = None,
    allow_add_new: bool = True,
) -> Dict[str, Any]:
    """执行数据导入的核心逻辑（直接从结构化数据导入）"""
    version_no, source_collection_name = await _prepare_import_version(rule)
    collection_name = build_collection_name(rule.id, rule.rule_code, version_no)

    if sync_fields is None:
        sync_fields = [h for h in headers if h not in primary_keys]

    result = await CsvImportSeekdbService.execute_import_from_rows(
        collection_name=collection_name,
        headers=headers,
        rows=rows,
        rule_id=rule.id,
        version_no=version_no,
        tenant_id=rule.tenant_id,
        app_name=rule.app_name,
        rule_code=rule.rule_code,
        primary_keys=primary_keys,
        sync_fields=sync_fields,
        source_collection_name=source_collection_name,
        allow_add_new=allow_add_new,
    )

    if "error" in result:
        return {"success": False, "error": result["error"]}

    if not remark:
        if result["added_count"] > 0 and result["updated_count"] == 0:
            remark = f"CURL导入：新增{result['added_count']}条，跳过{result['skipped_count']}条"
        else:
            remark = f"CURL导入：新增{result['added_count']}条，更新{result['updated_count']}条，跳过{result['skipped_count']}条"

    version_result = await _save_version_record(
        rule=rule,
        collection_name=collection_name,
        headers=result.get("headers", []),
        doc_count=result.get("total_count", 0),
        remark=remark,
    )

    logger.info(
        "CURL导入成功",
        rule_id=rule.id,
        version_no=version_result["version_no"],
        added=result["added_count"],
        updated=result["updated_count"],
    )

    return {
        "success": True,
        "data": {
            "headers": result.get("headers", []),
            "row_count": result.get("total_count", 0),
            "version_no": version_result["version_no"],
            "added_count": result["added_count"],
            "updated_count": result["updated_count"],
            "skipped_count": result["skipped_count"],
            "total_count": result["total_count"],
            "new_md5": version_result["new_md5"],
        }
    }


@router.post("/rule/import/file/preview", summary="预览CSV导入")
async def preview_file_import(file_request: FilePreviewRequest):
    """预览CSV导入 - 返回CSV表头、预览数据、是否是首次导入等信息"""
    rule = await _get_rule(rule_id=file_request.rule_id)
    if not rule:
        return Fail(code=404, msg="规则不存在")

    existing_headers, is_first_import = await _get_existing_headers(rule)
    csv_headers, csv_data = _parse_csv_content(file_request.content)

    primary_keys = []
    existing_config = _parse_import_config(rule.config) or {}
    if existing_config:
        primary_keys = existing_config.get("primary_keys", [])

    if hasattr(file_request, "primary_keys") and file_request.primary_keys:
        primary_keys = file_request.primary_keys
        await _save_primary_keys_config(rule, primary_keys)

    merged_headers = _merge_headers(existing_headers, csv_headers)
    sync_fields = [h for h in merged_headers if h not in primary_keys]

    # 从配置中读取 allow_add_new，默认为 True
    allow_add_new = existing_config.get("allow_add_new", True)

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
            "allow_add_new": allow_add_new,
        }
    )


@router.get("/rule/import/config", summary="获取导入配置")
async def get_import_config(query: ImportConfigQuery = Depends()):
    """获取规则的导入配置"""
    rule = await _get_rule(rule_id=query.rule_id)
    if not rule:
        return Fail(code=404, msg="规则不存在")

    config = _parse_import_config(rule.config) or {}

    return Success(data={
        "primary_keys": config.get("primary_keys", []),
        "sync_fields": config.get("sync_fields", []),
        "allow_add_new": config.get("allow_add_new", True),
    })


@router.post("/rule/import/file", summary="导入CSV文件")
async def import_csv_file(
    file: UploadFile = File(..., description="CSV文件"),
    rule_id: int = Form(..., description="规则ID"),
):
    """导入CSV文件，执行增量导入并保存为新版本"""
    rule = await _get_rule(rule_id=rule_id)
    if not rule:
        return Fail(code=404, msg="规则不存在")

    try:
        content = await file.read()
        csv_content = content.decode('utf-8')

        config_dict = _parse_import_config(rule.config) or {}
        primary_keys = config_dict.get("primary_keys", [])
        allow_add_new = config_dict.get("allow_add_new", True)

        import_result = await _execute_csv_import_core(
            rule=rule,
            csv_content=csv_content,
            primary_keys=primary_keys,
            allow_add_new=allow_add_new,
        )

        if not import_result["success"]:
            return Fail(code=400, msg=import_result["error"])

        return Success(data=import_result["data"])

    except Exception as e:
        logger.error("CSV导入失败", error=str(e))
        return Fail(code=400, msg=f"CSV导入失败: {str(e)}")


@router.post("/rule/import/apply", summary="执行CSV导入（通过内容）")
async def apply_import(import_request: ImportApplyRequest):
    """执行CSV导入 - 通过内容参数直接落库到seekdb"""
    rule = await _get_rule(rule_id=import_request.rule_id)
    if not rule:
        return Fail(code=404, msg="规则不存在")

    if import_request.primary_keys:
        await _save_primary_keys_config(rule, import_request.primary_keys)

    try:
        import_result = await _execute_csv_import_core(
            rule=rule,
            csv_content=import_request.content,
            primary_keys=import_request.primary_keys or [],
            sync_fields=import_request.sync_fields or [],
            remark=import_request.remark,
            allow_add_new=import_request.allow_add_new,
        )

        if not import_result["success"]:
            return Fail(code=400, msg=import_result["error"])

        return Success(data=import_result["data"])

    except VersionConflictException:
        return Fail(code=409, msg="规则已被他人修改，请刷新后重试")
    except Exception as e:
        logger.error("CSV导入失败", error=str(e))
        return Fail(code=500, msg=f"导入失败: {str(e)}")


@router.post("/rule/import/curl/preview", summary="预览CURL导入")
async def preview_curl_import(curl_request: CurlImportPreviewRequest):
    """预览CURL导入"""
    try:
        curl_config = curl_request.curl_config.model_dump()
        engine = CurlImportEngine(curl_config)
        result = await engine.fetch_data_as_csv()

        csv_content = result["csv_content"]
        headers = result["headers"]

        rows = []
        if csv_content:
            lines = csv_content.strip().split('\n')
            if len(lines) > 1:
                reader = csv.reader(lines[1:])
                rows = [row for row in reader]

        return Success(
            data={
                "headers": headers,
                "data": rows,
                "row_count": result["row_count"],
                "mode": "single" if len(curl_config.get("curl_commands", [])) == 1 else "cascade",
                "preview_data": rows[:10] if rows else [],
            }
        )

    except Exception as e:
        logger.error("CURL导入预览失败", error=str(e))
        return Fail(code=500, msg=f"CURL导入预览失败: {str(e)}")


@router.post("/rule/import/curl/config", summary="保存CURL导入配置")
async def save_curl_import_config(curl_config_request: CurlImportSaveConfigRequest):
    """保存CURL导入配置"""
    rule = await _get_rule(rule_id=curl_config_request.rule_id)
    if not rule:
        return Fail(code=404, msg="规则不存在")

    curl_config = curl_config_request.curl_config.model_dump()
    existing_config = _parse_import_config(rule.config) or {}
    config = {
        "import_type": "curl",
        "primary_keys": existing_config.get("primary_keys", []),
        "curl_config": curl_config,
    }

    await rule_service.update_rule_config(rule_id=rule.id, config=config)
    return Success(msg="配置保存成功")


@router.get("/rule/import/curl/config", summary="获取CURL导入配置")
async def get_curl_import_config(query: ImportConfigQuery = Depends()):
    """获取CURL导入配置"""
    rule = await _get_rule(rule_id=query.rule_id)
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
async def apply_curl_import(curl_apply_request: CurlImportApplyRequest):
    """执行CURL导入 - 获取数据后落库到seekdb"""
    rule = await _get_rule(rule_id=curl_apply_request.rule_id)
    if not rule:
        return Fail(code=404, msg="规则不存在")

    if not curl_apply_request.primary_keys:
        return Fail(code=400, msg="请配置主键字段")

    try:
        curl_config = curl_apply_request.curl_config.model_dump()
        engine = CurlImportEngine(curl_config)
        result = await engine.fetch_data_as_rows()

        headers = result["headers"]
        rows = result["rows"]
        if not rows:
            return Fail(code=400, msg="CURL请求未返回数据")

        await _save_primary_keys_config(rule, curl_apply_request.primary_keys)

        import_result = await _execute_import_from_rows_core(
            rule=rule,
            headers=headers,
            rows=rows,
            primary_keys=curl_apply_request.primary_keys,
            sync_fields=curl_apply_request.sync_fields,
            remark=curl_apply_request.remark or "CURL导入",
            allow_add_new=curl_apply_request.allow_add_new,
        )

        if not import_result["success"]:
            return Fail(code=400, msg=import_result["error"])

        return Success(data=import_result["data"])

    except VersionConflictException:
        return Fail(code=409, msg="规则已被他人修改，请刷新后重试")
    except Exception as e:
        logger.error("CURL导入失败", error=str(e))
        return Fail(code=500, msg=f"CURL导入失败: {str(e)}")
