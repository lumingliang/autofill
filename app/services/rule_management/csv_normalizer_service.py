"""
CSV数据标准化服务 - 提供可复用的CSV数据处理功能

设计原则：
1. 单一职责：每个方法只处理一种标准化任务
2. 纯函数：无副作用，便于单元测试
3. 可复用：多处调用统一入口
"""
from typing import Any, Dict, List


class CsvNormalizerService:
    """CSV数据标准化服务 - 提供可复用的数据标准化功能"""

    @staticmethod
    def normalize_headers(headers: List[str]) -> List[str]:
        """
        标准化表头 - 去除前后空格

        Args:
            headers: 原始表头列表

        Returns:
            标准化后的表头列表
        """
        return [h.strip() for h in headers]

    @staticmethod
    def deduplicate_by_primary_key(
        data: List[Dict[str, Any]],
        primary_keys: List[str]
    ) -> List[Dict[str, Any]]:
        """
        根据主键去重 - 保留第一条

        Args:
            data: 数据列表
            primary_keys: 主键字段列表

        Returns:
            去重后的数据列表
        """
        seen = set()
        result = []

        for row in data:
            # 构建主键值
            key_parts = []
            for pk in primary_keys:
                val = row.get(pk, "")
                key_parts.append(str(val))
            key = tuple(key_parts)

            if key not in seen:
                seen.add(key)
                result.append(row)

        return result
