"""
规则导入服务层 - 处理CSV导入的增量更新和去重
"""
import csv
import io
import json
from typing import Any, Dict, List, Optional, Tuple

from app.log import logger
from app.schemas.rule_management import (
    CsvImportConfig,
    ImportApplyResponse,
    ImportValidateResult,
)


class CsvImportService:
    """CSV导入服务 - 实现增量更新和去重功能"""

    @staticmethod
    def parse_csv(content: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        解析CSV内容

        Returns:
            (headers, data) - 表头列表和字典形式的数据列表
        """
        if not content or not content.strip():
            return [], []

        reader = csv.DictReader(io.StringIO(content.strip()))
        headers = reader.fieldnames or []
        data = list(reader)
        return headers, data

    @staticmethod
    def build_primary_key(row: Dict[str, Any], primary_keys: List[str]) -> Optional[str]:
        """
        构建主键值

        Args:
            row: 数据行
            primary_keys: 主键字段列表

        Returns:
            主键字符串，如果所有主键字段都为空则返回None
        """
        if not primary_keys:
            return None

        key_parts = []
        all_empty = True

        for key in primary_keys:
            val = row.get(key, "")
            if val is not None and str(val).strip() != "":
                all_empty = False
            key_parts.append(str(val) if val is not None else "")

        # 规则：全部主键字段同时为空，才返回None（表示跳过该行）
        if all_empty:
            return None

        return "|".join(key_parts)

    @staticmethod
    def validate_csv(
        csv_data: List[Dict[str, Any]],
        primary_keys: List[str],
        existing_data: Optional[List[Dict[str, Any]]] = None
    ) -> ImportValidateResult:
        """
        校验CSV数据

        校验项：
        1. 主键字段是否存在
        2. CSV内部是否有重复主键
        """
        errors = []
        duplicate_keys = []

        if not csv_data:
            return ImportValidateResult(is_valid=True)

        # 检查主键字段是否存在于CSV中
        if primary_keys:
            csv_headers = set(csv_data[0].keys())
            missing_keys = [k for k in primary_keys if k not in csv_headers]
            if missing_keys:
                errors.append(f"主键字段不存在于CSV中: {', '.join(missing_keys)}")
                return ImportValidateResult(is_valid=False, errors=errors)

        # 检查CSV内部重复主键
        if primary_keys:
            key_count: Dict[str, List[int]] = {}
            for idx, row in enumerate(csv_data):
                key = CsvImportService.build_primary_key(row, primary_keys)
                if key is not None:  # 只检查有主键的行
                    if key not in key_count:
                        key_count[key] = []
                    key_count[key].append(idx + 1)  # 记录行号（从1开始）

            for key, rows in key_count.items():
                if len(rows) > 1:
                    duplicate_keys.append({
                        "key": key,
                        "rows": rows,
                        "count": len(rows)
                    })

        if duplicate_keys:
            errors.append(f"发现 {len(duplicate_keys)} 个重复主键")

        return ImportValidateResult(
            is_valid=len(errors) == 0,
            duplicate_keys=duplicate_keys,
            errors=errors
        )

    @staticmethod
    def merge_data(
        csv_data: List[Dict[str, Any]],
        existing_data: List[Dict[str, Any]],
        existing_headers: List[str],
        config: CsvImportConfig,
        is_first_import: bool = False
    ) -> Tuple[List[Dict[str, Any]], ImportApplyResponse]:
        """
        合并CSV数据与现有数据

        规则：
        1. 首次导入：清空原有数据，全量导入
        2. 非首次导入：按主键做新增/更新，不删除旧数据
        3. 行级过滤：全部主键字段同时为空才跳过
        4. 更新时只更新sync_fields中配置的字段
        5. 新CSV多字段：自动新增，旧数据该字段为空
        6. 新CSV少字段：系统原有字段保留

        Args:
            csv_data: CSV解析后的数据
            existing_data: 现有数据
            existing_headers: 现有表头
            config: 导入配置
            is_first_import: 是否是首次导入

        Returns:
            (merged_data, statistics)
        """
        primary_keys = config.primary_keys or []
        sync_fields = config.sync_fields or []

        # 统计信息
        stats = {
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "failed_reasons": []
        }

        # 首次导入：直接返回CSV数据（全量）
        if is_first_import:
            result = []
            for row in csv_data:
                # 检查是否需要跳过（全部主键为空）
                if primary_keys and CsvImportService.build_primary_key(row, primary_keys) is None:
                    stats["skipped"] += 1
                    continue
                result.append(dict(row))
                stats["added"] += 1

            return result, ImportApplyResponse(
                version_no=0,
                added_count=stats["added"],
                updated_count=0,
                skipped_count=stats["skipped"],
                failed_count=0,
                total_count=stats["added"],
                new_md5=""
            )

        # 非首次导入：增量更新
        # 1. 构建现有数据的索引
        existing_index: Dict[str, Tuple[int, Dict[str, Any]]] = {}
        for idx, row in enumerate(existing_data):
            if primary_keys:
                key = CsvImportService.build_primary_key(row, primary_keys)
                if key is not None:
                    existing_index[key] = (idx, row)

        # 2. 合并所有表头（保留旧字段，添加新字段）
        csv_headers = set(csv_data[0].keys()) if csv_data else set()
        all_headers = list(existing_headers)  # 先保留旧表头顺序
        for h in csv_headers:
            if h not in all_headers:
                all_headers.append(h)  # 追加新字段

        # 3. 处理CSV数据
        result = [dict(row) for row in existing_data]  # 先复制所有旧数据
        processed_keys = set()

        for row_idx, csv_row in enumerate(csv_data):
            try:
                # 检查是否需要跳过（全部主键为空）
                if primary_keys:
                    key = CsvImportService.build_primary_key(csv_row, primary_keys)
                    if key is None:
                        stats["skipped"] += 1
                        continue
                else:
                    key = None

                # 检查CSV内部重复
                if key is not None and key in processed_keys:
                    stats["failed"] += 1
                    stats["failed_reasons"].append({
                        "row": row_idx + 1,
                        "reason": "主键重复"
                    })
                    continue

                if key is not None:
                    processed_keys.add(key)

                # 判断是新增还是更新
                if key is not None and key in existing_index:
                    # 更新现有数据
                    existing_idx, _ = existing_index[key]
                    for field in sync_fields:
                        if field in csv_row:
                            result[existing_idx][field] = csv_row[field]
                    # 添加CSV中存在但现有数据中不存在的新字段
                    for field in csv_headers:
                        if field not in existing_headers:
                            result[existing_idx][field] = csv_row.get(field, "")
                    stats["updated"] += 1
                else:
                    # 新增数据
                    new_row: Dict[str, Any] = {}
                    # 先填充所有字段为空
                    for h in all_headers:
                        new_row[h] = ""
                    # 填充CSV中的数据
                    for h in csv_headers:
                        new_row[h] = csv_row.get(h, "")
                    result.append(new_row)
                    stats["added"] += 1

            except Exception as e:
                stats["failed"] += 1
                stats["failed_reasons"].append({
                    "row": row_idx + 1,
                    "reason": str(e)
                })
                logger.error(f"处理第{row_idx + 1}行失败", error=str(e))

        return result, ImportApplyResponse(
            version_no=0,
            added_count=stats["added"],
            updated_count=stats["updated"],
            skipped_count=stats["skipped"],
            failed_count=stats["failed"],
            failed_reasons=stats["failed_reasons"],
            total_count=len(result),
            new_md5=""
        )

    async def preview_import(
        self,
        csv_content: str,
        existing_headers: Optional[List[str]] = None,
        existing_config: Optional[Dict[str, Any]] = None,
        is_first_import: bool = False
    ) -> Dict[str, Any]:
        """
        预览导入

        Returns:
            预览结果
        """
        csv_headers, csv_data = self.parse_csv(csv_content)

        # 解析现有配置
        config = CsvImportConfig()
        if existing_config:
            config.primary_keys = existing_config.get("primary_keys", [])
            config.sync_fields = existing_config.get("sync_fields", [])

        # 预览数据（前10行）
        preview_data = csv_data[:10]

        return {
            "csv_headers": csv_headers,
            "existing_headers": existing_headers or [],
            "row_count": len(csv_data),
            "preview_data": preview_data,
            "is_first_import": is_first_import,
            "config": config.model_dump()
        }

    async def execute_import(
        self,
        csv_content: str,
        existing_data: List[Dict[str, Any]],
        existing_headers: List[str],
        config: CsvImportConfig,
        is_first_import: bool = False
    ) -> Tuple[List[Dict[str, Any]], ImportApplyResponse]:
        """
        执行导入

        Returns:
            (merged_data, statistics)
        """
        # 解析CSV
        csv_headers, csv_data = self.parse_csv(csv_content)

        if not csv_data:
            return existing_data, ImportApplyResponse(
                version_no=0,
                added_count=0,
                updated_count=0,
                skipped_count=0,
                failed_count=0,
                total_count=len(existing_data),
                new_md5=""
            )

        # 校验数据
        validation = self.validate_csv(csv_data, config.primary_keys or [], existing_data)
        if not validation.is_valid:
            logger.error("CSV校验失败", errors=validation.errors)
            raise ValueError(f"CSV校验失败: {'; '.join(validation.errors)}")

        # 合并数据
        merged_data, stats = self.merge_data(
            csv_data,
            existing_data,
            existing_headers,
            config,
            is_first_import
        )

        return merged_data, stats


# 创建服务实例
csv_import_service = CsvImportService()
