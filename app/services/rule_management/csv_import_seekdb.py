"""
CSV 导入 seekdb 服务 - 优化版

设计原则：
1. 使用最小遍历次数的优化算法
2. 支持首次全量导入和增量导入
3. 支持联合主键和选择性字段同步
4. 支持 allow_add_new 开关控制是否新增数据
5. 直接落库到 seekdb
"""

import csv
import io
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Iterator

from app.log import logger
from app.services.storage.seekdb_service import seekdb_service


@dataclass
class ImportStats:
    """导入统计信息"""
    added_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    total_count: int = 0
    failed_reasons: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "added_count": self.added_count,
            "updated_count": self.updated_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "total_count": self.total_count,
            "failed_reasons": self.failed_reasons
        }


class CsvImportSeekdbService:
    """CSV 导入 seekdb 服务 - 优化版"""

    @staticmethod
    def parse_csv_streaming(csv_content: str) -> Tuple[List[str], Iterator[Dict[str, str]]]:
        """
        流式解析CSV，返回表头和行迭代器

        Args:
            csv_content: CSV 字符串内容

        Returns:
            (headers, row_generator)
        """
        if not csv_content or not csv_content.strip():
            return [], iter([])

        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        raw_headers = reader.fieldnames or []
        headers = [h.strip() for h in raw_headers]

        header_mapping = {raw: stripped for raw, stripped in zip(raw_headers, headers)}

        def row_generator():
            for row in reader:
                yield {header_mapping.get(k, k): v for k, v in row.items()}

        return headers, row_generator()

    @staticmethod
    def build_primary_key(row: Dict[str, Any], primary_keys: List[str]) -> Optional[str]:
        """
        构建主键值

        规则：
        - 无主键配置时返回特殊标记
        - 全部主键字段同时为空，返回None（跳过该行）
        """
        if not primary_keys:
            return "__no_pk__"

        key_parts = []
        all_empty = True

        for key in primary_keys:
            val = row.get(key, "")
            if val is not None and str(val).strip() != "":
                all_empty = False
            key_parts.append(str(val) if val is not None else "")

        if all_empty:
            return None

        return "|".join(key_parts)

    @staticmethod
    def merge_headers(existing: List[str], new: List[str]) -> List[str]:
        """
        合并表头：保留旧表头顺序，追加新字段
        """
        existing_set = set(existing)
        merged = list(existing)

        for h in new:
            if h not in existing_set:
                merged.append(h)

        return merged

    @staticmethod
    async def execute_import(
        collection_name: str,
        csv_content: str,
        rule_id: int,
        version_no: int,
        tenant_id: int,
        app_name: str,
        rule_code: str,
        primary_keys: List[str],
        sync_fields: List[str],
        is_first_import: bool = False,
        allow_add_new: bool = True,
        source_collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行 CSV 导入到 seekdb

        Args:
            collection_name: seekdb 集合名称（目标集合）
            csv_content: CSV 字符串内容
            rule_id: 规则ID
            version_no: 版本号
            tenant_id: 租户ID
            app_name: 应用名称
            rule_code: 规则编码
            primary_keys: 主键字段列表
            sync_fields: 需要同步更新的字段列表
            is_first_import: 是否首次导入
            allow_add_new: 是否允许新增数据
            source_collection_name: 源集合名称（用于读取旧数据，增量导入时使用）

        Returns:
            导入结果统计
        """
        primary_keys = primary_keys or []
        sync_fields_set = set(sync_fields or [])
        stats = ImportStats()

        csv_headers, csv_rows = CsvImportSeekdbService.parse_csv_streaming(csv_content)

        if not csv_headers:
            return {
                "error": "CSV 表头为空",
                "added_count": 0,
                "updated_count": 0,
                "skipped_count": 0
            }

        if is_first_import:
            return await CsvImportSeekdbService._first_import(
                collection_name, csv_rows, csv_headers,
                rule_id, version_no, tenant_id, app_name, rule_code,
                primary_keys, stats
            )

        return await CsvImportSeekdbService._incremental_import(
            collection_name, csv_rows, csv_headers,
            rule_id, version_no, tenant_id, app_name, rule_code,
            primary_keys, sync_fields_set, allow_add_new, stats,
            source_collection_name
        )

    @staticmethod
    async def _first_import(
        collection_name: str,
        csv_rows: Iterator[Dict[str, str]],
        csv_headers: List[str],
        rule_id: int,
        version_no: int,
        tenant_id: int,
        app_name: str,
        rule_code: str,
        primary_keys: List[str],
        stats: ImportStats
    ) -> Dict[str, Any]:
        """
        首次导入 - 全量导入
        """
        collection = seekdb_service.get_or_create_collection(collection_name)
        seekdb_service.delete_collection(collection_name)
        collection = seekdb_service.get_or_create_collection(collection_name)

        ids = []
        metadatas = []
        seen_keys: Set[str] = set()
        has_primary_key = bool(primary_keys)
        row_index = 0

        for row in csv_rows:
            key = CsvImportSeekdbService.build_primary_key(row, primary_keys)
            if key is None:
                stats.skipped_count += 1
                continue

            if has_primary_key and key in seen_keys:
                stats.skipped_count += 1
                continue
            if has_primary_key:
                seen_keys.add(key)

            row_data = {h: row.get(h, "") for h in csv_headers}

            doc_id = f"{rule_id}_v{version_no}_{row_index}"
            ids.append(doc_id)
            metadatas.append({
                "rule_id": rule_id,
                "version_no": version_no,
                "row_index": row_index,
                "tenant_id": tenant_id,
                "app_name": app_name,
                "rule_code": rule_code,
                "data": row_data,
                "headers": csv_headers
            })

            stats.added_count += 1
            row_index += 1

        if ids:
            documents = [" | ".join([f"{h}: {row.get(h, '')}" for h in csv_headers]) for row in [m["data"] for m in metadatas]]
            collection.add(ids=ids, metadatas=metadatas, documents=documents)

        stats.total_count = len(ids)

        logger.info(
            "首次全量导入 CSV 到 seekdb",
            collection_name=collection_name,
            added_count=stats.added_count,
            skipped_count=stats.skipped_count
        )

        return {
            "added_count": stats.added_count,
            "updated_count": 0,
            "skipped_count": stats.skipped_count,
            "total_count": stats.total_count,
            "headers": csv_headers,
            "collection_name": collection_name
        }

    @staticmethod
    async def _incremental_import(
        collection_name: str,
        csv_rows: Iterator[Dict[str, str]],
        csv_headers: List[str],
        rule_id: int,
        version_no: int,
        tenant_id: int,
        app_name: str,
        rule_code: str,
        primary_keys: List[str],
        sync_fields_set: Set[str],
        allow_add_new: bool,
        stats: ImportStats,
        source_collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        增量导入 - 按主键匹配更新/新增
        修复说明：
        1. 保留所有旧数据，不删除未匹配的行
        2. 正确区分更新和新增操作
        3. 正确统计更新行数和新增行数
        4. 支持从源集合读取旧数据（用于新版本导入时）
        """
        # 从seekdb获取当前数据
        # 如果有指定源集合，则从源集合读取旧数据；否则从目标集合读取
        collection = seekdb_service.get_or_create_collection(collection_name)
        source_collection = seekdb_service.get_or_create_collection(
            source_collection_name if source_collection_name else collection_name
        )
        existing_results = source_collection.get()

        existing_headers = []
        existing_data = []

        if existing_results and existing_results.get("metadatas"):
            existing_headers = existing_results["metadatas"][0].get("headers", [])
            for metadata in existing_results["metadatas"]:
                existing_data.append(metadata.get("data", {}))

        # 合并表头
        all_headers = CsvImportSeekdbService.merge_headers(existing_headers, csv_headers)

        # 构建主键到旧数据的映射
        old_key_to_row: Dict[str, Dict] = {}
        has_primary_key = bool(primary_keys)

        for row in existing_data:
            key = CsvImportSeekdbService.build_primary_key(row, primary_keys)
            if key:
                old_key_to_row[key] = dict(row)  # 复制数据，避免修改原始数据

        # 处理新增字段：为所有旧数据添加新字段（空值）
        new_fields = set(csv_headers) - set(existing_headers)
        for key in old_key_to_row:
            for field in new_fields:
                if field not in old_key_to_row[key]:
                    old_key_to_row[key][field] = ""

        # 处理CSV数据
        seen_csv_keys: Set[str] = set()
        updated_keys: Set[str] = set()
        new_rows: List[Dict] = []

        for row in csv_rows:
            stats.total_count += 1
            key = CsvImportSeekdbService.build_primary_key(row, primary_keys)

            if key is None:
                stats.skipped_count += 1
                continue

            # 检查CSV内重复
            if has_primary_key and key in seen_csv_keys:
                stats.skipped_count += 1
                continue
            if has_primary_key:
                seen_csv_keys.add(key)

            if has_primary_key and key in old_key_to_row:
                # 主键存在，执行更新
                target_row = old_key_to_row[key]

                # 更新同步字段
                for field in sync_fields_set:
                    if field in row:
                        target_row[field] = row[field]

                # 更新新增字段
                for field in new_fields:
                    target_row[field] = row.get(field, "")

                updated_keys.add(key)
                stats.updated_count += 1
            elif allow_add_new:
                # 主键不存在且允许新增，创建新行
                new_row: Dict[str, Any] = {h: "" for h in all_headers}
                for field in csv_headers:
                    new_row[field] = row.get(field, "")
                new_rows.append(new_row)
                stats.added_count += 1
            else:
                # 主键不存在且不允许新增，跳过
                stats.skipped_count += 1

        # 构建最终结果：保留所有旧数据（包括未更新的），加上新数据
        result = []

        # 添加所有旧数据（已更新的会被更新后的数据替换）
        for key, row in old_key_to_row.items():
            # 确保所有字段都存在
            for h in all_headers:
                if h not in row:
                    row[h] = ""
            result.append(row)

        # 添加新数据
        result.extend(new_rows)

        # 删除旧数据，重新插入（仅在存在旧数据时删除）
        existing_ids = existing_results.get("ids", []) if existing_results else []
        if existing_ids:
            collection.delete(ids=existing_ids)

        # 保存所有数据
        ids = []
        metadatas = []
        for idx, row_data in enumerate(result):
            doc_id = f"{rule_id}_v{version_no}_{idx}"
            ids.append(doc_id)
            metadatas.append({
                "rule_id": rule_id,
                "version_no": version_no,
                "row_index": idx,
                "tenant_id": tenant_id,
                "app_name": app_name,
                "rule_code": rule_code,
                "data": row_data,
                "headers": all_headers
            })

        if ids:
            documents = [" | ".join([f"{h}: {row.get(h, '')}" for h in all_headers]) for row in result]
            collection.add(ids=ids, metadatas=metadatas, documents=documents)

        logger.info(
            "增量导入 CSV 到 seekdb",
            collection_name=collection_name,
            added_count=stats.added_count,
            updated_count=stats.updated_count,
            skipped_count=stats.skipped_count,
            total_count=len(result)
        )

        return {
            "added_count": stats.added_count,
            "updated_count": stats.updated_count,
            "skipped_count": stats.skipped_count,
            "total_count": len(result),
            "headers": all_headers,
            "collection_name": collection_name
        }


csv_import_seekdb_service = CsvImportSeekdbService()
