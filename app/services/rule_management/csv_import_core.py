"""
CSV增量导入核心模块 - 提供可复用的CSV导入逻辑

设计原则：
1. 纯函数设计，不依赖外部状态
2. 支持首次导入（全量）和增量导入（新增/更新）
3. 支持多字段联合主键
4. 支持选择性字段同步更新
5. 完善的校验和统计反馈
"""

import csv
import io
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


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


@dataclass
class ImportConfig:
    """导入配置"""
    primary_keys: List[str] = field(default_factory=list)  # 主键字段列表（支持联合主键）
    sync_fields: List[str] = field(default_factory=list)  # 需要同步更新的字段列表


class CsvImportCore:
    """CSV导入核心类 - 提供纯函数的导入逻辑"""

    @staticmethod
    def parse_csv(csv_content: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        解析CSV内容

        Args:
            csv_content: CSV字符串内容

        Returns:
            (headers, data) - 表头列表和字典形式的数据列表
        """
        if not csv_content or not csv_content.strip():
            return [], []

        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        raw_headers = reader.fieldnames or []
        # 需求1：表头标准化 - 去除前后空格
        headers = [h.strip() for h in raw_headers]

        # 构建表头映射：原始表头 -> 标准化表头
        header_mapping = {raw: stripped for raw, stripped in zip(raw_headers, headers)}

        # 读取数据并标准化键名
        raw_data = list(reader)
        data = []
        for row in raw_data:
            standardized_row = {header_mapping.get(k, k): v for k, v in row.items()}
            data.append(standardized_row)

        return headers, data

    @staticmethod
    def build_primary_key(row: Dict[str, Any], primary_keys: List[str]) -> Optional[str]:
        """
        构建主键值

        规则：全部主键字段同时为空，才返回None（表示跳过该行）
              只要任意一个主键字段有值，则正常参与导入匹配

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
    def validate_data(
        csv_data: List[Dict[str, Any]],
        primary_keys: List[str]
    ) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
        """
        校验数据
        需求1：去除重复主键校验错误，改为保留第一条

        Args:
            csv_data: CSV数据
            primary_keys: 主键字段列表

        Returns:
            (is_valid, errors, duplicate_keys) - duplicate_keys 用于统计，不用于报错
        """
        errors = []
        duplicate_keys = []

        if not csv_data:
            return True, [], []

        # 检查主键字段是否存在于CSV中
        if primary_keys:
            csv_headers = set(csv_data[0].keys())
            missing_keys = [k for k in primary_keys if k not in csv_headers]
            if missing_keys:
                errors.append(f"主键字段不存在于CSV中: {', '.join(missing_keys)}")
                return False, errors, []

        # 需求1：检查CSV内部重复主键（仅用于统计，不报错）
        if primary_keys:
            key_count: Dict[str, List[int]] = {}
            for idx, row in enumerate(csv_data):
                key = CsvImportCore.build_primary_key(row, primary_keys)
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

        # 需求1：不再将重复主键视为错误，仅返回用于统计
        return len(errors) == 0, errors, duplicate_keys

    @staticmethod
    def merge_headers(
        existing_headers: List[str],
        csv_headers: Set[str]
    ) -> List[str]:
        """
        合并表头

        规则：
        1. 保留旧表头顺序
        2. 追加CSV中存在但旧表头中没有的新字段

        Args:
            existing_headers: 现有表头
            csv_headers: CSV中的表头

        Returns:
            合并后的表头列表
        """
        all_headers = list(existing_headers)  # 先保留旧表头顺序
        for h in csv_headers:
            if h not in all_headers:
                all_headers.append(h)  # 追加新字段
        return all_headers

    @staticmethod
    def execute_import(
        csv_content: str,
        existing_data: List[Dict[str, Any]],
        existing_headers: List[str],
        config: ImportConfig,
        is_first_import: bool = False,
        allow_add_new: bool = True
    ) -> Tuple[List[Dict[str, Any]], ImportStats, List[str]]:
        """
        执行CSV增量导入

        核心规则：
        1. 首次导入：清空原有数据，全量导入CSV所有有效行
        2. 非首次导入：按配置的主键做新增/更新，不删除系统原有旧数据
        3. 行级过滤：新CSV中，配置的全部主键字段同时为空，才忽略、跳过该行
        4. 数据匹配与更新：
           - 新CSV行的主键与系统已有数据主键完全一致：仅更新sync_fields中配置的字段
           - 新CSV行的主键在系统不存在：直接新增该行完整数据（仅当allow_add_new=True）
           - 系统存在但新CSV无对应主键：保留原有旧数据，不删除
        5. 表头兼容：
           - 按表头字段名称匹配，不按列顺序匹配
           - 新CSV比旧表头多字段：自动新增字段，历史旧数据该字段为空
           - 新CSV比旧表头少字段：系统原有字段保留，不删除、不清空

        Args:
            csv_content: CSV内容字符串
            existing_data: 现有数据（字典列表）
            existing_headers: 现有表头
            config: 导入配置
            is_first_import: 是否是首次导入
            allow_add_new: 是否允许新增数据（需求2新增）

        Returns:
            (merged_data, stats, all_headers) - 合并后的数据、统计信息和合并后的表头
        """
        primary_keys = config.primary_keys or []
        sync_fields = config.sync_fields or []

        stats = ImportStats()

        # 解析CSV（已包含表头标准化）
        csv_headers, csv_data = CsvImportCore.parse_csv(csv_content)

        if not csv_data:
            # 没有CSV数据，返回现有数据
            stats.total_count = len(existing_data)
            return existing_data, stats, existing_headers

        # 校验数据（重复主键不再报错）
        is_valid, errors, duplicate_keys = CsvImportCore.validate_data(csv_data, primary_keys)
        if not is_valid:
            stats.failed_count = len(errors)
            stats.failed_reasons = [{"row": 0, "reason": e} for e in errors]
            return existing_data, stats, existing_headers

        # 需求1：统计重复主键数量（用于返回信息，不报错）
        if duplicate_keys:
            for dup in duplicate_keys:
                stats.skipped_count += dup["count"] - 1

        # 首次导入：直接返回CSV数据（全量）
        if is_first_import:
            result = []
            processed_keys: Set[str] = set()
            for row in csv_data:
                # 检查是否需要跳过（全部主键为空）
                if primary_keys:
                    key = CsvImportCore.build_primary_key(row, primary_keys)
                    if key is None:
                        stats.skipped_count += 1
                        continue
                    # 需求1：跳过重复主键（保留第一条）
                    if key in processed_keys:
                        continue
                    processed_keys.add(key)
                result.append(dict(row))
                stats.added_count += 1

            stats.total_count = len(result)
            # 首次导入，使用CSV的表头
            return result, stats, csv_headers

        # 非首次导入：增量更新
        # 1. 合并所有表头（保留旧字段，添加新字段）- 需求3
        all_headers = CsvImportCore.merge_headers(existing_headers, set(csv_headers))

        # 2. 构建CSV数据的索引
        csv_index: Dict[str, Dict[str, Any]] = {}
        csv_processed_keys: Set[str] = set()
        for row in csv_data:
            if primary_keys:
                key = CsvImportCore.build_primary_key(row, primary_keys)
                if key is None:
                    stats.skipped_count += 1
                    continue
                # 需求1：跳过重复主键（保留第一条）
                if key in csv_processed_keys:
                    stats.skipped_count += 1
                    continue
                csv_processed_keys.add(key)
                csv_index[key] = row
            else:
                # 无主键时，无法建立索引
                pass

        # 3. 根据allow_add_new执行不同逻辑（需求2）
        if allow_add_new:
            # 开关开启：允许新增 - 遍历CSV数据
            result = CsvImportCore._execute_import_with_add(
                existing_data, existing_headers, csv_headers, all_headers,
                csv_index, primary_keys, sync_fields, stats
            )
        else:
            # 开关关闭：不新增 - 遍历旧数据
            result = CsvImportCore._execute_import_without_add(
                existing_data, existing_headers, csv_headers, all_headers,
                csv_index, primary_keys, sync_fields, stats
            )

        stats.total_count = len(result)
        return result, stats, all_headers

    @staticmethod
    def _execute_import_with_add(
        existing_data: List[Dict[str, Any]],
        existing_headers: List[str],
        csv_headers: List[str],
        all_headers: List[str],
        csv_index: Dict[str, Dict[str, Any]],
        primary_keys: List[str],
        sync_fields: List[str],
        stats: ImportStats
    ) -> List[Dict[str, Any]]:
        """
        执行允许新增的导入逻辑
        遍历旧数据 + 遍历CSV新增数据
        """
        # 构建现有数据索引
        existing_index: Dict[str, int] = {}
        for idx, row in enumerate(existing_data):
            if primary_keys:
                key = CsvImportCore.build_primary_key(row, primary_keys)
                if key is not None:
                    existing_index[key] = idx

        # 复制旧数据
        result = [dict(row) for row in existing_data]

        # 处理CSV数据
        for key, csv_row in csv_index.items():
            if key in existing_index:
                # 更新现有数据
                existing_idx = existing_index[key]
                for field in sync_fields:
                    if field in csv_row:
                        result[existing_idx][field] = csv_row[field]
                    else:
                        # 新CSV中不存在的字段，置空
                        result[existing_idx][field] = ""
                # 添加CSV中存在但现有数据中不存在的新字段
                for field in csv_headers:
                    if field not in existing_headers:
                        result[existing_idx][field] = csv_row.get(field, "")
                stats.updated_count += 1
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
                stats.added_count += 1

        return result

    @staticmethod
    def _execute_import_without_add(
        existing_data: List[Dict[str, Any]],
        existing_headers: List[str],
        csv_headers: List[str],
        all_headers: List[str],
        csv_index: Dict[str, Dict[str, Any]],
        primary_keys: List[str],
        sync_fields: List[str],
        stats: ImportStats
    ) -> List[Dict[str, Any]]:
        """
        执行不允许新增的导入逻辑
        只遍历旧数据，更新匹配的行，不新增任何数据
        """
        result = []

        for old_row in existing_data:
            new_row = dict(old_row)

            if primary_keys:
                key = CsvImportCore.build_primary_key(old_row, primary_keys)
                if key is not None and key in csv_index:
                    # 找到匹配的CSV行，更新sync_fields
                    csv_row = csv_index[key]
                    for field in sync_fields:
                        if field in csv_row:
                            new_row[field] = csv_row[field]
                        else:
                            # 新CSV中不存在该字段，置空
                            new_row[field] = ""
                    # 添加CSV中存在但现有数据中不存在的新字段
                    for field in csv_headers:
                        if field not in existing_headers:
                            new_row[field] = csv_row.get(field, "")
                    stats.updated_count += 1
                else:
                    # 未匹配到，保留原样
                    stats.skipped_count += 1
            else:
                # 无主键，无法匹配，保留原样
                stats.skipped_count += 1

            result.append(new_row)

        return result

    @staticmethod
    def convert_to_csv_format(
        data: List[Dict[str, Any]],
        headers: List[str]
    ) -> Tuple[List[str], List[List[str]]]:
        """
        将数据转换为CSV格式

        Args:
            data: 字典列表形式的数据
            headers: 表头列表

        Returns:
            (headers, csv_data) - 表头和CSV格式的数据（字符串列表的列表）
        """
        if not data:
            return headers, []

        csv_data = []
        for row in data:
            csv_row = [str(row.get(h, "")) for h in headers]
            csv_data.append(csv_row)

        return headers, csv_data


# 创建全局实例
csv_import_core = CsvImportCore()


# 便捷函数 - 供外部直接调用
def execute_csv_import(
    csv_content: str,
    existing_data: List[Dict[str, Any]],
    existing_headers: List[str],
    primary_keys: List[str],
    sync_fields: List[str],
    is_first_import: bool = False,
    allow_add_new: bool = True
) -> Tuple[List[Dict[str, Any]], ImportStats, List[str]]:
    """
    执行CSV增量导入的便捷函数

    Args:
        csv_content: CSV内容字符串
        existing_data: 现有数据（字典列表）
        existing_headers: 现有表头
        primary_keys: 主键字段列表
        sync_fields: 需要同步更新的字段列表
        is_first_import: 是否是首次导入
        allow_add_new: 是否允许新增数据（默认True）

    Returns:
        (merged_data, stats, all_headers) - 合并后的数据、统计信息和合并后的表头

    Example:
        >>> merged_data, stats, all_headers = execute_csv_import(
        ...     csv_content="id,name,age\n1,张三,20\n2,李四,25",
        ...     existing_data=[{"id": "1", "name": "张三", "age": "18"}],
        ...     existing_headers=["id", "name", "age"],
        ...     primary_keys=["id"],
        ...     sync_fields=["name", "age"],
        ...     is_first_import=False,
        ...     allow_add_new=True
        ... )
        >>> print(f"新增: {stats.added_count}, 更新: {stats.updated_count}")
    """
    config = ImportConfig(
        primary_keys=primary_keys,
        sync_fields=sync_fields
    )
    return CsvImportCore.execute_import(
        csv_content=csv_content,
        existing_data=existing_data,
        existing_headers=existing_headers,
        config=config,
        is_first_import=is_first_import,
        allow_add_new=allow_add_new
    )
