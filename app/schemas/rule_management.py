"""
规则管理模块 Schemas
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RuleCreate(BaseModel):
    """创建规则请求"""
    rule_code: str = Field("", max_length=64, description="规则唯一编码，为空时自动生成")
    rule_name: str = Field(..., max_length=128, description="规则名称")
    desc: str = Field("", max_length=512, description="规则描述")
    app_name: str = Field("", max_length=64, description="应用名称")
    tenant_id: int = Field(0, description="租户ID，超级管理员必须指定")


class RuleUpdate(BaseModel):
    """更新规则请求"""
    id: int = Field(0, description="规则ID")
    rule_name: str = Field("", max_length=128, description="规则名称")
    desc: str = Field("", max_length=512, description="规则描述")
    status: int = Field(-1, description="状态：0-禁用，1-启用，-1表示不修改")
    app_name: str = Field("", max_length=64, description="应用名称")
    tenant_id: int = Field(0, description="租户ID")


class RuleVersionSave(BaseModel):
    """保存版本请求"""
    rule_id: int = Field(..., description="规则ID")
    content_json: Dict[str, Any] = Field(..., description="规则内容JSON格式")
    current_md5: str = Field(..., max_length=32, description="当前版本MD5，用于乐观锁")
    remark: str = Field("", max_length=512, description="版本备注")
    tenant_id: int = Field(0, description="租户ID")
    is_major: bool = Field(False, description="是否主版本")


class RuleVersionRollback(BaseModel):
    """回滚版本请求"""
    rule_id: int = Field(..., description="规则ID")
    version_no: int = Field(..., description="目标版本号")


class RuleInfoOut(BaseModel):
    """规则信息输出"""
    id: int
    tenant_id: int = 0
    app_name: str = ""
    rule_code: str = ""
    rule_name: str = ""
    desc: str = ""
    latest_version_id: Optional[int] = None
    status: int = 1
    created_at: str = ""
    updated_at: str = ""

    class Config:
        from_attributes = True


class RuleVersionOut(BaseModel):
    """规则版本输出"""
    id: int
    tenant_id: int = 0
    app_name: str = ""
    version_no: int = 0
    content_md5: str = ""
    storage_type: int = 1
    content_json: Optional[Dict[str, Any]] = None
    file_size: int = 0
    remark: str = ""
    status: int = 1
    created_at: str = ""

    class Config:
        from_attributes = True


class RuleDetailOut(BaseModel):
    """规则详情输出"""
    rule_info: RuleInfoOut
    current_version: Optional[RuleVersionOut] = None


class RuleVersionHistoryItem(BaseModel):
    """版本历史项"""
    id: int
    version_no: int = 0
    content_md5: str = ""
    file_size: int = 0
    remark: str = ""
    status: int = 1
    created_at: str = ""


class RuleVersionHistoryOut(BaseModel):
    """版本历史输出"""
    total: int = 0
    items: List[RuleVersionHistoryItem] = []


# ============ CSV 导入配置相关 Schema (新设计) ============

class CsvImportConfig(BaseModel):
    """CSV导入配置"""
    primary_keys: List[str] = Field(default_factory=list, description="主键字段列表（联合唯一）")
    sync_fields: List[str] = Field(default_factory=list, description="需要同步更新的字段列表")


class FilePreviewRequest(BaseModel):
    """文件导入预览请求"""
    rule_id: int = Field(..., description="规则ID")
    tenant_id: int = Field(0, description="租户ID")
    content: str = Field(..., description="CSV内容")
    primary_keys: List[str] = Field(default_factory=list, description="主键字段列表（可选，提供时自动保存）")


class FilePreviewResponse(BaseModel):
    """文件导入预览响应"""
    csv_headers: List[str] = Field(default_factory=list, description="CSV表头")
    existing_headers: List[str] = Field(default_factory=list, description="系统现有表头")
    row_count: int = Field(0, description="数据行数")
    preview_data: List[Dict[str, Any]] = Field(default_factory=list, description="预览数据（前10行）")
    is_first_import: bool = Field(False, description="是否是首次导入")
    config: CsvImportConfig = Field(default_factory=CsvImportConfig, description="当前配置")


class ImportConfigSave(BaseModel):
    """保存导入配置请求"""
    rule_id: int = Field(..., description="规则ID")
    tenant_id: int = Field(0, description="租户ID")
    config: CsvImportConfig = Field(..., description="导入配置")


class ImportApplyRequest(BaseModel):
    """执行CSV导入请求"""
    rule_id: int = Field(..., description="规则ID")
    tenant_id: int = Field(0, description="租户ID")
    content: str = Field(..., description="CSV内容")
    current_md5: str = Field("", max_length=32, description="当前版本MD5，用于乐观锁")
    remark: str = Field("", max_length=512, description="版本备注")
    config: CsvImportConfig = Field(..., description="导入配置")


class ImportApplyResponse(BaseModel):
    """执行CSV导入响应"""
    version_no: int = Field(..., description="新版本号")
    added_count: int = Field(0, description="新增行数")
    updated_count: int = Field(0, description="更新行数")
    skipped_count: int = Field(0, description="忽略行数（主键全为空）")
    failed_count: int = Field(0, description="失败行数")
    failed_reasons: List[Dict[str, Any]] = Field(default_factory=list, description="失败原因列表")
    total_count: int = Field(0, description="总行数")
    new_md5: str = Field(..., description="新版本MD5")


class ImportValidateResult(BaseModel):
    """导入校验结果"""
    is_valid: bool = Field(True, description="是否通过校验")
    duplicate_keys: List[Dict[str, Any]] = Field(default_factory=list, description="重复主键列表")
    errors: List[str] = Field(default_factory=list, description="错误信息列表")


# ============ CURL 导入配置相关 Schema ============

class CurlLevelField(BaseModel):
    """CURL层级字段配置"""
    csv_header: str = Field(..., description="CSV表头名称")
    jsonpath: str = Field(..., description="JSONPath表达式")


class CurlLevelConfig(BaseModel):
    """CURL层级配置"""
    source: Dict[str, Any] = Field(default_factory=dict, description="数据源配置")
    fields: List[CurlLevelField] = Field(default_factory=list, description="字段列表")
    children_jsonpath: Optional[str] = Field(None, description="子节点JSONPath")
    params: Dict[str, str] = Field(default_factory=dict, description="请求参数映射")


class CurlImportConfig(BaseModel):
    """CURL导入配置"""
    description: str = Field("", description="配置描述")
    global_vars: Dict[str, str] = Field(default_factory=dict, description="全局变量")
    data_root_path: str = Field("$.data", description="数据根路径")
    level_config: Dict[str, CurlLevelConfig] = Field(default_factory=dict, description="层级配置")
    curl_commands: List[str] = Field(default_factory=list, description="CURL命令列表")


class CurlImportPreviewRequest(BaseModel):
    """CURL导入预览请求"""
    rule_id: int = Field(..., description="规则ID")
    tenant_id: int = Field(0, description="租户ID")
    curl_config: Dict[str, Any] = Field(..., description="CURL导入配置")


class CurlImportPreviewResponse(BaseModel):
    """CURL导入预览响应"""
    headers: List[str] = Field(default_factory=list, description="CSV表头")
    data: List[List[str]] = Field(default_factory=list, description="CSV数据")
    row_count: int = Field(0, description="数据行数")
    mode: str = Field("single", description="模式：single/cascade")
    preview_data: List[List[str]] = Field(default_factory=list, description="预览数据（前10行）")


class CurlImportSaveConfigRequest(BaseModel):
    """保存CURL导入配置请求 - 只保存curl_config，主键和同步字段在公共配置中管理"""
    rule_id: int = Field(..., description="规则ID")
    tenant_id: int = Field(0, description="租户ID")
    curl_config: Dict[str, Any] = Field(..., description="CURL导入配置")


class CurlImportApplyRequest(BaseModel):
    """执行CURL导入请求"""
    rule_id: int = Field(..., description="规则ID")
    tenant_id: int = Field(0, description="租户ID")
    current_md5: str = Field("", max_length=32, description="当前版本MD5，用于乐观锁")
    remark: str = Field("", max_length=512, description="版本备注")
    primary_keys: List[str] = Field(default_factory=list, description="主键字段列表")
    sync_fields: List[str] = Field(default_factory=list, description="同步字段列表")
    curl_config: Dict[str, Any] = Field(default_factory=dict, description="CURL导入配置")



