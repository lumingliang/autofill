"""
CSV 导入 seekdb 服务 - 优化版

设计原则：
1. 统一导入逻辑：无论首次还是增量导入，都先删除旧集合再新建
2. 使用最小遍历次数的优化算法
3. 支持联合主键和选择性字段同步
4. 只允许更新主键+sync_fields控制的字段
5. 直接落库到 seekdb，统一使用 embedding_function=None + 零向量
"""

import csv
import io
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Iterator

from app.services.storage.seekdb_service import seekdb_service, DEFAULT_QUERY_LIMIT


def build_collection_name(rule_id: int, rule_code: str, version_no: int) -> str:
    """构建 seekdb 集合名称"""
    return f"rule_{rule_id}_{rule_code}_v{version_no}"


@dataclass
class ImportStats:
    """导入统计信息"""
    added_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    total_count: int = 0


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
    def build_allowed_fields(
        existing_headers: List[str],
        primary_keys: List[str],
        sync_fields: List[str]
    ) -> Tuple[List[str], Set[str], Set[str]]:
        """
        构建允许的字段列表，返回三类字段

        规则：
        1. 第一类：主键字段 (primary_keys)
        2. 第二类：sync_fields_set 中的字段（需要同步更新的字段）
        3. 第三类：旧表中除上述两类之外的字段（保留但不同步）

        Args:
            existing_headers: 已有表头字段列表（旧CSV的表头）
            primary_keys: 主键字段列表
            sync_fields: 需要同步的字段列表

        Returns:
            (all_fields_list, pk_and_sync_fields_set, other_fields_set)
            - all_fields_list: 所有字段的有序列表
            - pk_and_sync_fields_set: 主键 + sync_fields 的集合（需要从新表取值的字段）
            - other_fields_set: 第三类字段的集合（需要从旧表取值或置空的字段）
        """
        primary_keys_set = set(primary_keys or [])
        sync_fields_set = set(sync_fields or [])

        # 第一类 + 第二类：主键 + sync_fields
        pk_and_sync_fields_set = primary_keys_set | sync_fields_set

        # 第三类：旧表中除主键和sync_fields之外的字段
        other_fields_set = set()
        if existing_headers:
            other_fields_set = set(existing_headers) - pk_and_sync_fields_set

        # 所有字段
        all_fields = pk_and_sync_fields_set | other_fields_set

        # 分离id字段和非id字段
        id_fields = [f for f in all_fields if f.lower().endswith('id')]
        non_id_fields = [f for f in all_fields if not f.lower().endswith('id')]

        # 构建有序列表
        # 顺序：非id主键 -> 非id sync_fields -> 非id其他字段 -> id字段
        ordered_non_id = []
        ordered_id = []
        seen = set()

        # 先添加非id主键
        for f in primary_keys:
            if f not in seen and f in non_id_fields:
                ordered_non_id.append(f)
                seen.add(f)

        # 再添加非id sync_fields（排除已在主键中的）
        for f in (sync_fields or []):
            if f not in seen and f in non_id_fields:
                ordered_non_id.append(f)
                seen.add(f)

        # 添加非id其他字段（按existing_headers顺序）
        if existing_headers:
            for f in existing_headers:
                if f in other_fields_set and f not in seen and f in non_id_fields:
                    ordered_non_id.append(f)
                    seen.add(f)

        # id字段放最后：先主键中的id，然后是sync_fields中的id，最后是其他id
        seen_id = set()

        # 主键中的id
        for f in primary_keys:
            if f in id_fields and f not in seen_id:
                ordered_id.append(f)
                seen_id.add(f)

        # sync_fields中的id
        for f in (sync_fields or []):
            if f in id_fields and f not in seen_id:
                ordered_id.append(f)
                seen_id.add(f)

        # 其他id字段（按existing_headers顺序）
        if existing_headers:
            for f in existing_headers:
                if f in other_fields_set and f in id_fields and f not in seen_id:
                    ordered_id.append(f)
                    seen_id.add(f)

        ordered_fields = ordered_non_id + ordered_id

        return ordered_fields, pk_and_sync_fields_set, other_fields_set

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
        source_collection_name: Optional[str] = None,
        allow_add_new: bool = True
    ) -> Dict[str, Any]:
        """
        执行 CSV 导入到 seekdb

        统一导入逻辑：
        1. 无论首次还是增量导入，都先删除旧集合再新建
        2. 只允许更新主键+sync_fields控制的字段
        3. 统一使用 embedding_function=None + 零向量

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
            source_collection_name: 源集合名称（用于读取旧数据进行合并）
            allow_add_new: 是否允许新增数据（当主键不存在时，是否将CSV数据作为新行导入）

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

        return await CsvImportSeekdbService._unified_import(
            collection_name, csv_rows, csv_headers,
            rule_id, version_no, tenant_id, app_name, rule_code,
            primary_keys, sync_fields_set, stats,
            source_collection_name, allow_add_new
        )

    @staticmethod
    async def execute_import_from_rows(
        collection_name: str,
        headers: List[str],
        rows: List[Dict[str, Any]],
        rule_id: int,
        version_no: int,
        tenant_id: int,
        app_name: str,
        rule_code: str,
        primary_keys: List[str],
        sync_fields: List[str],
        source_collection_name: Optional[str] = None,
        allow_add_new: bool = True
    ) -> Dict[str, Any]:
        """
        执行数据导入到 seekdb（直接从结构化数据导入，避免 CSV 编解码开销）

        Args:
            collection_name: seekdb 集合名称（目标集合）
            headers: 表头列表
            rows: 数据行列表，每行是一个字典
            rule_id: 规则ID
            version_no: 版本号
            tenant_id: 租户ID
            app_name: 应用名称
            rule_code: 规则编码
            primary_keys: 主键字段列表
            sync_fields: 需要同步更新的字段列表
            source_collection_name: 源集合名称（用于读取旧数据进行合并）
            allow_add_new: 是否允许新增数据

        Returns:
            导入结果统计
        """
        primary_keys = primary_keys or []
        sync_fields_set = set(sync_fields or [])
        stats = ImportStats()

        if not headers:
            return {
                "error": "表头为空",
                "added_count": 0,
                "updated_count": 0,
                "skipped_count": 0
            }

        # 将列表转换为迭代器，复用统一的导入逻辑
        rows_iterator = iter(rows)

        return await CsvImportSeekdbService._unified_import(
            collection_name, rows_iterator, headers,
            rule_id, version_no, tenant_id, app_name, rule_code,
            primary_keys, sync_fields_set, stats,
            source_collection_name, allow_add_new
        )

    @staticmethod
    async def _unified_import(
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
        stats: ImportStats,
        source_collection_name: Optional[str] = None,
        allow_add_new: bool = True
    ) -> Dict[str, Any]:
        """
        统一导入方法 - 无论首次还是增量导入都使用相同逻辑

        设计说明：
        1. 先删除旧集合，再新建集合，预防冲突
        2. 如果有源集合，读取旧数据进行合并
        3. 只允许更新主键+sync_fields控制的字段
        4. 统一使用 embedding_function=None + 零向量
        5. 旧数据在新CSV中无匹配则保留
        6. allow_add_new=False 时，CSV中存在但旧数据中不存在的主键将被跳过（不新增）
        """
        seekdb_service.delete_collection(collection_name)
        collection = seekdb_service.get_or_create_collection(collection_name, embedding_function=None)

        existing_data: List[Dict[str, Any]] = []
        existing_headers: List[str] = []

        if source_collection_name:
            source_collection = seekdb_service.get_or_create_collection(source_collection_name)
            existing_results = source_collection.get(limit=DEFAULT_QUERY_LIMIT)

            if existing_results and existing_results.get("metadatas"):
                for metadata in existing_results["metadatas"]:
                    row_data = metadata.get("data", {})
                    existing_data.append(row_data)
                    if not existing_headers and metadata.get("headers"):
                        existing_headers = metadata.get("headers", [])

            if not existing_headers and existing_data:
                existing_headers = list(existing_data[0].keys())

        csv_rows_list = list(csv_rows)

        csv_index: Dict[str, Dict[str, str]] = {}
        csv_seen_keys: Set[str] = set()
        has_primary_key = bool(primary_keys)

        for row in csv_rows_list:
            key = CsvImportSeekdbService.build_primary_key(row, primary_keys)
            if key is None:
                stats.skipped_count += 1
                continue
            if has_primary_key and key in csv_seen_keys:
                stats.skipped_count += 1
                continue
            if has_primary_key:
                csv_seen_keys.add(key)
            csv_index[key] = row

        existing_index: Dict[str, Dict[str, Any]] = {}
        for row in existing_data:
            key = CsvImportSeekdbService.build_primary_key(row, primary_keys)
            if key:
                existing_index[key] = row

        result_rows: List[Dict[str, Any]] = []
        processed_old_keys: Set[str] = set()

        # 使用公共方法构建允许的字段列表，返回三类字段
        allowed_fields_list, pk_and_sync_fields_set, other_fields_set = CsvImportSeekdbService.build_allowed_fields(
            existing_headers=existing_headers,
            primary_keys=primary_keys,
            sync_fields=list(sync_fields_set)
        )
        allowed_fields = set(allowed_fields_list)

        for key, csv_row in csv_index.items():
            if key in existing_index:
                # 更新现有数据：
                # 1. 主键 + sync_fields_set 的字段，使用新表的值
                # 2. 第三类字段直接使用旧表的值
                old_row = existing_index[key]
                new_row: Dict[str, Any] = {}
                has_real_update = False

                for field in allowed_fields_list:
                    if field in pk_and_sync_fields_set:
                        # 第一类 + 第二类：使用新表的值
                        old_val = old_row.get(field, "")
                        new_val = csv_row.get(field, "")
                        new_row[field] = new_val
                        # 对比新旧值，检查是否真的有更新
                        if str(old_val) != str(new_val):
                            has_real_update = True
                    else:
                        # 第三类：使用旧表的值
                        new_row[field] = old_row.get(field, "")

                result_rows.append(new_row)
                processed_old_keys.add(key)

                # 只有真正有字段变化时才计入更新统计
                if has_real_update:
                    stats.updated_count += 1
            elif allow_add_new:
                # 允许新增时：
                # 1. 主键 + sync_fields_set 的字段，使用新表的值
                # 2. 第三类字段设置为空
                new_row: Dict[str, Any] = {}
                for field in allowed_fields_list:
                    if field in pk_and_sync_fields_set:
                        # 第一类 + 第二类：使用新表的值
                        new_row[field] = csv_row.get(field, "")
                    else:
                        # 第三类：设置为空
                        new_row[field] = ""
                result_rows.append(new_row)
                stats.added_count += 1
            else:
                # 不允许新增时，跳过这条数据
                stats.skipped_count += 1

        for key, old_row in existing_index.items():
            if key not in processed_old_keys:
                # 未匹配的旧数据：只保留 allowed_fields，没有则置空
                new_row: Dict[str, Any] = {}
                for field in allowed_fields_list:
                    new_row[field] = old_row.get(field, "")
                result_rows.append(new_row)

        if result_rows:
            ids = []
            metadatas = []
            # 存储允许的字段列表作为 headers（使用排序后的列表）
            allowed_headers = allowed_fields_list
            for idx, row_data in enumerate(result_rows):
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
                    "headers": allowed_headers
                })

            embeddings = [[0.0] * 384 for _ in range(len(ids))]
            collection.add(ids=ids, metadatas=metadatas, embeddings=embeddings)

        stats.total_count = len(result_rows)

        return {
            "added_count": stats.added_count,
            "updated_count": stats.updated_count,
            "skipped_count": stats.skipped_count,
            "total_count": stats.total_count,
            "headers": allowed_headers,
            "collection_name": collection_name
        }
