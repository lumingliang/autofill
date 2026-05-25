"""
CSV导入策略服务 - 提供可复用的导入策略功能

设计原则：
1. 策略模式：不同的导入逻辑封装为不同策略
2. 纯函数：无副作用，便于单元测试
3. 可复用：多处调用统一入口
"""
from typing import Any, Dict, List, Set, Tuple


class CsvImportStrategy:
    """CSV导入策略服务 - 提供可复用的导入策略"""

    @staticmethod
    def merge_headers(
        existing_headers: List[str],
        new_headers: Set[str]
    ) -> List[str]:
        """
        合并表头 - 保留原有顺序，添加新字段

        Args:
            existing_headers: 现有表头列表
            new_headers: 新表头集合

        Returns:
            合并后的表头列表
        """
        # 从现有表头开始
        merged = list(existing_headers)

        # 添加新表头（保持原有顺序，新字段追加到末尾）
        existing_set = set(existing_headers)
        for h in new_headers:
            if h not in existing_set:
                merged.append(h)

        return merged

    @staticmethod
    def apply_headers_to_data(
        headers: List[str],
        row: List[str]
    ) -> Dict[str, str]:
        """
        将表头应用到数据行

        Args:
            headers: 表头列表
            row: 数据行

        Returns:
            字典格式的数据行
        """
        result = {}
        for i, header in enumerate(headers):
            if i < len(row):
                result[header] = row[i]
            else:
                result[header] = ""  # 数据缺失时填空
        return result

    @staticmethod
    def sync_row_data(
        existing_row: Dict[str, Any],
        new_row: Dict[str, Any],
        sync_fields: List[str],
        all_headers: List[str]
    ) -> Dict[str, Any]:
        """
        同步行数据 - 更新指定字段，缺失字段置空

        Args:
            existing_row: 现有数据行
            new_row: 新数据行
            sync_fields: 需要同步的字段列表
            all_headers: 所有表头（用于检测缺失字段）

        Returns:
            同步后的数据行
        """
        result = dict(existing_row)

        # 更新同步字段
        for field in sync_fields:
            if field in new_row:
                result[field] = new_row[field]

        # 对于旧数据中有但新数据中不存在的字段，设置为空
        for header in all_headers:
            if header not in new_row and header in result:
                # 保留原有值（这是更新逻辑，不是替换）
                pass

        return result

    @staticmethod
    def classify_rows_by_primary_key(
        existing_data: List[Dict[str, Any]],
        new_data: List[Dict[str, Any]],
        primary_keys: List[str]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        根据主键将数据分类为：需要更新的、需要新增的

        Args:
            existing_data: 现有数据
            new_data: 新数据
            primary_keys: 主键字段列表

        Returns:
            (需要更新的行列表, 需要新增的行列表)
        """
        # 构建现有数据的主键索引
        existing_keys = {}
        for row in existing_data:
            key_parts = [str(row.get(pk, "")) for pk in primary_keys]
            key = tuple(key_parts)
            existing_keys[key] = row

        to_update = []
        to_add = []

        for new_row in new_data:
            key_parts = [str(new_row.get(pk, "")) for pk in primary_keys]
            key = tuple(key_parts)

            if key in existing_keys:
                to_update.append((existing_keys[key], new_row))
            else:
                to_add.append(new_row)

        return to_update, to_add
