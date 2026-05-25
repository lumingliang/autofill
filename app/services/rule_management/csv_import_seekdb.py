"""
CSV 导入 seekdb 服务
支持全量导入、增量导入、表头变更处理
"""
import csv
import io
from typing import Any, Dict, List, Optional, Tuple

from app.log import logger
from app.services.storage.seekdb_service import seekdb_service


class CsvImportSeekdbService:
    """CSV 导入 seekdb 服务"""

    @staticmethod
    def parse_csv(csv_content: str) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        解析 CSV 内容

        Args:
            csv_content: CSV 字符串内容

        Returns:
            (headers, data) - 表头列表和数据字典列表
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        headers = reader.fieldnames or []
        data = list(reader)
        return headers, data

    @staticmethod
    def merge_headers(
        existing_headers: List[str],
        new_headers: List[str]
    ) -> Tuple[List[str], Dict[str, str]]:
        """
        合并表头，处理字段增删

        Args:
            existing_headers: 现有表头列表
            new_headers: 新表头列表

        Returns:
            (merged_headers, field_mapping)
            - merged_headers: 合并后的表头列表（保留所有字段）
            - field_mapping: 字段映射关系 {新字段名: 原字段名}
        """
        # 保留现有表头顺序
        merged_headers = existing_headers.copy()

        # 添加新字段到末尾
        for header in new_headers:
            if header not in merged_headers:
                merged_headers.append(header)

        # 构建字段映射（用于处理字段重命名，后续可扩展）
        field_mapping = {}
        for header in new_headers:
            if header in existing_headers:
                field_mapping[header] = header

        return merged_headers, field_mapping

    @staticmethod
    def migrate_row_data(
        row: Dict[str, str],
        merged_headers: List[str],
        existing_headers: List[str]
    ) -> Dict[str, str]:
        """
        迁移行数据到新的表头结构

        Args:
            row: 原始行数据
            merged_headers: 合并后的表头列表
            existing_headers: 现有表头列表

        Returns:
            迁移后的行数据（包含所有字段，缺失字段为空字符串）
        """
        migrated_data = {}

        for header in merged_headers:
            if header in row:
                # 新 CSV 中有该字段
                migrated_data[header] = row[header]
            elif header in existing_headers:
                # 该字段在现有表头中但不在新 CSV 中（被删除的字段）
                # 保留空值
                migrated_data[header] = ""
            else:
                # 新增字段，设为空值
                migrated_data[header] = ""

        return migrated_data

    @staticmethod
    def detect_header_compatibility(
        existing_headers: List[str],
        new_headers: List[str]
    ) -> Dict[str, Any]:
        """
        检测表头兼容性

        Args:
            existing_headers: 现有表头
            new_headers: 新表头

        Returns:
            兼容性分析结果
        """
        existing_set = set(existing_headers)
        new_set = set(new_headers)

        added = new_set - existing_set
        removed = existing_set - new_set
        common = existing_set & new_set

        # 判断兼容性级别
        if not added and not removed:
            level = "compatible"  # 完全兼容（仅顺序变化）
        elif not removed and added:
            level = "additive"  # 向后兼容（仅新增字段）
        elif removed and not added:
            level = "destructive"  # 破坏性变更（删除字段）
        else:
            level = "mixed"  # 混合变更（增删都有）

        return {
            "level": level,
            "added_fields": list(added),
            "removed_fields": list(removed),
            "common_fields": list(common),
            "is_safe": level in ["compatible", "additive"],
            "warning": None if level in ["compatible", "additive"] else
                      f"检测到表头变更：新增 {len(added)} 个字段，删除 {len(removed)} 个字段"
        }

    @staticmethod
    async def full_import(
        collection_name: str,
        csv_content: str,
        rule_id: int,
        version_no: int,
        tenant_id: int,
        app_name: str,
        rule_code: str
    ) -> Dict[str, Any]:
        """
        全量导入 CSV 到 seekdb

        Args:
            collection_name: seekdb 集合名称
            csv_content: CSV 字符串内容
            rule_id: 规则ID
            version_no: 版本号
            tenant_id: 租户ID
            app_name: 应用名称
            rule_code: 规则编码

        Returns:
            导入结果统计
        """
        # 1. 解析 CSV
        headers, data = CsvImportSeekdbService.parse_csv(csv_content)

        if not headers:
            return {
                "error": "CSV 表头为空",
                "added_count": 0,
                "updated_count": 0,
                "headers_changed": False
            }

        # 2. 删除旧集合（如果存在）
        seekdb_service.delete_collection(collection_name)

        # 3. 保存到 seekdb
        doc_count = await seekdb_service.save_rule_data(
            collection_name=collection_name,
            headers=headers,
            data=data,
            rule_id=rule_id,
            version_no=version_no,
            tenant_id=tenant_id,
            app_name=app_name,
            rule_code=rule_code
        )

        logger.info(
            "全量导入 CSV 到 seekdb",
            collection_name=collection_name,
            doc_count=doc_count,
            headers=headers
        )

        return {
            "added_count": doc_count,
            "updated_count": 0,
            "total_count": doc_count,
            "headers": headers,
            "collection_name": collection_name
        }

    @staticmethod
    async def incremental_import(
        collection_name: str,
        csv_content: str,
        rule_id: int,
        version_no: int,
        tenant_id: int,
        app_name: str,
        rule_code: str,
        primary_keys: List[str]
    ) -> Dict[str, Any]:
        """
        增量导入 CSV 到 seekdb

        Args:
            collection_name: seekdb 集合名称
            csv_content: CSV 字符串内容
            rule_id: 规则ID
            version_no: 版本号
            tenant_id: 租户ID
            app_name: 应用名称
            rule_code: 规则编码
            primary_keys: 主键字段列表

        Returns:
            导入结果统计
        """
        # 1. 解析新 CSV
        new_headers, new_data = CsvImportSeekdbService.parse_csv(csv_content)

        if not new_headers:
            return {
                "error": "CSV 表头为空",
                "added_count": 0,
                "updated_count": 0,
                "headers_changed": False
            }

        # 2. 获取现有数据
        collection = seekdb_service.get_or_create_collection(collection_name)
        existing_results = collection.get()

        existing_headers = []
        existing_dict = {}

        if existing_results and existing_results.get("metadatas"):
            # 从第一条记录获取现有表头
            existing_headers = existing_results["metadatas"][0].get("headers", [])

            # 构建主键索引
            for metadata in existing_results["metadatas"]:
                row_data = metadata.get("data", {})
                pk_values = [str(row_data.get(pk, "")) for pk in primary_keys]
                if all(pk_values):  # 主键字段都有值
                    pk_key = "|".join(pk_values)
                    existing_dict[pk_key] = metadata

        # 3. 合并表头
        merged_headers, _ = CsvImportSeekdbService.merge_headers(
            existing_headers, new_headers
        )

        # 4. 检测表头变更
        headers_changed = {
            "added": [h for h in new_headers if h not in existing_headers],
            "removed": [h for h in existing_headers if h not in new_headers],
            "unchanged": [h for h in new_headers if h in existing_headers],
            "total_before": len(existing_headers),
            "total_after": len(merged_headers)
        }

        # 5. 处理新增和更新
        ids_to_add = []
        metadatas_to_add = []
        ids_to_update = []
        metadatas_to_update = []
        added_count = 0
        updated_count = 0

        for row_index, row in enumerate(new_data):
            # 构建主键
            pk_values = [str(row.get(pk, "")) for pk in primary_keys]
            pk_key = "|".join(pk_values)

            # 构建完整行数据（包含所有字段）
            row_data = CsvImportSeekdbService.migrate_row_data(
                row, merged_headers, existing_headers
            )

            if pk_key in existing_dict:
                # 更新现有记录
                existing_id = existing_dict[pk_key]["id"]
                ids_to_update.append(existing_id)
                metadatas_to_update.append({
                    "rule_id": rule_id,
                    "version_no": version_no,
                    "row_index": row_index,
                    "tenant_id": tenant_id,
                    "app_name": app_name,
                    "rule_code": rule_code,
                    "data": row_data,
                    "headers": merged_headers
                })
                updated_count += 1
            else:
                # 新增记录
                doc_id = f"{rule_id}_v{version_no}_{row_index}"
                ids_to_add.append(doc_id)
                metadatas_to_add.append({
                    "rule_id": rule_id,
                    "version_no": version_no,
                    "row_index": row_index,
                    "tenant_id": tenant_id,
                    "app_name": app_name,
                    "rule_code": rule_code,
                    "data": row_data,
                    "headers": merged_headers
                })
                added_count += 1

        # 6. 批量写入 seekdb
        if ids_to_update:
            # seekdb 不支持直接更新，先删除再添加
            collection.delete(ids=ids_to_update)
            collection.add(ids=ids_to_update, metadatas=metadatas_to_update)

        if ids_to_add:
            collection.add(ids=ids_to_add, metadatas=metadatas_to_add)

        logger.info(
            "增量导入 CSV 到 seekdb",
            collection_name=collection_name,
            added_count=added_count,
            updated_count=updated_count,
            headers=merged_headers
        )

        return {
            "added_count": added_count,
            "updated_count": updated_count,
            "total_count": added_count + updated_count,
            "headers": merged_headers,
            "headers_changed": headers_changed["added"] or headers_changed["removed"],
            "headers_change_detail": headers_changed,
            "collection_name": collection_name
        }

    @staticmethod
    async def import_with_header_change(
        collection_name: str,
        csv_content: str,
        rule_id: int,
        version_no: int,
        tenant_id: int,
        app_name: str,
        rule_code: str,
        is_incremental: bool = False,
        primary_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        处理表头变更的 CSV 导入

        Args:
            collection_name: seekdb 集合名称
            csv_content: CSV 字符串内容
            rule_id: 规则ID
            version_no: 版本号
            tenant_id: 租户ID
            app_name: 应用名称
            rule_code: 规则编码
            is_incremental: 是否为增量导入
            primary_keys: 主键字段列表（增量导入时必需）

        Returns:
            导入结果统计，包含表头变更信息
        """
        if is_incremental:
            if not primary_keys:
                return {
                    "error": "增量导入必须指定主键字段",
                    "added_count": 0,
                    "updated_count": 0,
                    "headers_changed": False
                }
            return await CsvImportSeekdbService.incremental_import(
                collection_name=collection_name,
                csv_content=csv_content,
                rule_id=rule_id,
                version_no=version_no,
                tenant_id=tenant_id,
                app_name=app_name,
                rule_code=rule_code,
                primary_keys=primary_keys
            )
        else:
            return await CsvImportSeekdbService.full_import(
                collection_name=collection_name,
                csv_content=csv_content,
                rule_id=rule_id,
                version_no=version_no,
                tenant_id=tenant_id,
                app_name=app_name,
                rule_code=rule_code
            )

    @staticmethod
    async def safe_import_with_header_check(
        collection_name: str,
        csv_content: str,
        rule_id: int,
        version_no: int,
        tenant_id: int,
        app_name: str,
        rule_code: str,
        allow_header_change: bool = True,
        is_incremental: bool = False,
        primary_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        带表头检查的安全导入

        Args:
            allow_header_change: 是否允许表头变更（默认允许）
            ...其他参数同上

        Returns:
            导入结果，包含兼容性警告
        """
        # 解析新 CSV
        new_headers, _ = CsvImportSeekdbService.parse_csv(csv_content)

        # 获取现有表头
        existing_headers = []
        if is_incremental:
            collection = seekdb_service.get_or_create_collection(collection_name)
            existing_results = collection.get()
            if existing_results and existing_results.get("metadatas"):
                existing_headers = existing_results["metadatas"][0].get("headers", [])

        # 检测兼容性
        compatibility = CsvImportSeekdbService.detect_header_compatibility(
            existing_headers, new_headers
        )

        # 如果不允许表头变更且检测到变更，返回错误
        if not allow_header_change and (compatibility["added_fields"] or compatibility["removed_fields"]):
            return {
                "error": "表头变更被拒绝",
                "compatibility": compatibility,
                "message": compatibility.get("warning", "表头结构发生变化")
            }

        # 执行导入
        result = await CsvImportSeekdbService.import_with_header_change(
            collection_name=collection_name,
            csv_content=csv_content,
            rule_id=rule_id,
            version_no=version_no,
            tenant_id=tenant_id,
            app_name=app_name,
            rule_code=rule_code,
            is_incremental=is_incremental,
            primary_keys=primary_keys
        )

        # 添加兼容性信息
        result["compatibility"] = compatibility

        return result

    @staticmethod
    async def export_to_csv(collection_name: str) -> Tuple[str, List[str], List[Dict[str, str]]]:
        """
        从 seekdb 导出为 CSV 格式

        Args:
            collection_name: seekdb 集合名称

        Returns:
            (csv_content, headers, data)
        """
        return await seekdb_service.export_to_csv(collection_name)


csv_import_seekdb_service = CsvImportSeekdbService()
