"""
CSV导入服务 - 提供统一的CSV导入功能入口

设计原则：
1. 外观模式：统一入口，简化调用
2. 组合复用：组合使用各个子服务
3. 类型安全：完整的类型注解
"""
from typing import Any, Dict, List, Tuple

from app.services.rule_management.csv_import_core import CsvImportCore, ImportConfig
from app.services.rule_management.csv_import_strategy import CsvImportStrategy
from app.services.rule_management.csv_normalizer_service import CsvNormalizerService


class CsvImportService:
    """
    CSV导入服务 - 统一入口
    
    整合以下功能：
    - CsvNormalizerService: 数据标准化
    - CsvImportStrategy: 导入策略
    - CsvImportCore: 核心导入逻辑
    """

    @staticmethod
    def normalize_csv_headers(headers: List[str]) -> List[str]:
        """
        标准化CSV表头
        
        Args:
            headers: 原始表头列表
            
        Returns:
            标准化后的表头列表
        """
        return CsvNormalizerService.normalize_headers(headers)

    @staticmethod
    def deduplicate_csv_data(
        data: List[Dict[str, Any]],
        primary_keys: List[str]
    ) -> List[Dict[str, Any]]:
        """
        对CSV数据按主键去重
        
        Args:
            data: CSV数据列表
            primary_keys: 主键字段列表
            
        Returns:
            去重后的数据列表
        """
        return CsvNormalizerService.deduplicate_by_primary_key(data, primary_keys)

    @staticmethod
    def merge_csv_headers(
        existing_headers: List[str],
        new_headers: List[str]
    ) -> List[str]:
        """
        合并CSV表头
        
        Args:
            existing_headers: 现有表头列表
            new_headers: 新表头列表
            
        Returns:
            合并后的表头列表
        """
        return CsvImportStrategy.merge_headers(
            existing_headers,
            set(new_headers)
        )

    @staticmethod
    def execute_csv_import(
        csv_content: str,
        existing_data: List[Dict[str, Any]],
        existing_headers: List[str],
        primary_keys: List[str],
        sync_fields: List[str],
        is_first_import: bool = False,
        allow_add_new: bool = True
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int], List[str]]:
        """
        执行CSV导入

        这是统一的导入入口，整合所有子服务的功能

        Args:
            csv_content: CSV文件内容
            existing_data: 现有数据
            existing_headers: 现有表头
            primary_keys: 主键字段列表
            sync_fields: 同步字段列表
            is_first_import: 是否为首次导入
            allow_add_new: 是否允许新增数据

        Returns:
            (合并后的数据, 统计信息, 合并后的表头)
        """
        config = ImportConfig(
            primary_keys=primary_keys,
            sync_fields=sync_fields
        )

        merged_data, stats, all_headers = CsvImportCore.execute_import(
            csv_content=csv_content,
            existing_data=existing_data,
            existing_headers=existing_headers,
            config=config,
            is_first_import=is_first_import,
            allow_add_new=allow_add_new
        )

        # 转换统计信息为字典
        stats_dict = {
            "total_rows": stats.total_count,
            "imported_rows": stats.added_count + stats.updated_count,
            "updated_rows": stats.updated_count,
            "skipped_rows": stats.skipped_count,
            "added_rows": stats.added_count
        }

        return merged_data, stats_dict, all_headers

    @staticmethod
    def parse_and_validate_csv(
        csv_content: str,
        expected_headers: List[str] = None
    ) -> Tuple[List[str], List[List[str]], List[str]]:
        """
        解析并验证CSV
        
        Args:
            csv_content: CSV内容
            expected_headers: 期望的表头（可选）
            
        Returns:
            (表头, 数据行, 错误列表)
        """
        errors = []
        
        try:
            headers, rows = CsvImportCore.parse_csv(csv_content)
            
            # 标准化表头
            headers = CsvNormalizerService.normalize_headers(headers)
            
            # 验证表头
            if expected_headers:
                missing = set(expected_headers) - set(headers)
                if missing:
                    errors.append(f"缺少必需字段: {', '.join(missing)}")
            
            return headers, rows, errors
            
        except Exception as e:
            errors.append(f"CSV解析失败: {str(e)}")
            return [], [], errors
