"""
字段展平服务 - 支持多级嵌套数据的展平处理
"""
import json
from typing import Any, Dict, List, Tuple
from jsonpath_ng import parse as jsonpath_parse

from app.log import logger


class FieldFlattener:
    """字段展平工具类 - 支持三级展平"""

    @staticmethod
    def _apply_jsonpath(data: Any, json_path: str) -> List[Any]:
        """
        使用JSONPath提取数据

        Args:
            data: 原始数据
            json_path: JSONPath表达式

        Returns:
            提取结果列表
        """
        if not json_path or not data:
            return []
        
        try:
            jsonpath_expr = jsonpath_parse(json_path)
            results = [match.value for match in jsonpath_expr.find(data)]
            return results if results else []
        except Exception as e:
            logger.warning(f"[FieldFlattener] JSONPath解析失败: {e}")
            return []

    @staticmethod
    def _extract_value(obj: Any, field: str = None) -> str:
        """
        从对象中提取值
        
        Args:
            obj: 对象或基本类型值
            field: 字段名，如果为None则直接转字符串
            
        Returns:
            提取的字符串值
        """
        if obj is None:
            return ""
        
        if field and isinstance(obj, dict):
            return str(obj.get(field, ""))
        
        return str(obj)

    @staticmethod
    def _is_absolute_path(json_path: str) -> bool:
        """
        判断JSONPath是否为绝对路径（从根开始）
        
        Args:
            json_path: JSONPath表达式
            
        Returns:
            是否为绝对路径
        """
        return json_path.startswith("$.") if json_path else False

    @staticmethod
    def _flatten_with_paths(
        data: Any,
        level1_path: str,
        level2_path: str,
        level3_path: str,
        separator: str = "-",
        level1_field: str = None,
        level2_field: str = None,
        level3_field: str = None
    ) -> List[str]:
        """
        使用三级路径配置展平数据
        
        支持两种模式：
        1. 相对路径模式：level2_path 是相对于 level1_val 的路径（不以 $. 开头）
        2. 绝对路径模式：level2_path 是从根开始的完整路径（以 $. 开头）

        Args:
            data: 原始数据
            level1_path: 第一级路径
            level2_path: 第二级路径
            level3_path: 第三级路径
            separator: 拼接符
            level1_field: 第一级字段名（用于从对象中提取）
            level2_field: 第二级字段名
            level3_field: 第三级字段名

        Returns:
            展平后的字符串列表
        """
        if not data:
            return []
        
        result: List[str] = []
        
        # 判断路径模式
        level2_is_absolute = FieldFlattener._is_absolute_path(level2_path)
        level3_is_absolute = FieldFlattener._is_absolute_path(level3_path)
        
        # 第一级 - 总是从根数据提取
        level1_values = FieldFlattener._apply_jsonpath(data, level1_path) if level1_path else []
        if not level1_values:
            return result
        
        # 只有第一级的情况
        if not level2_path:
            result = [FieldFlattener._extract_value(v, level1_field) for v in level1_values if v is not None]
            return result
        
        # 绝对路径模式：所有级别都从根数据提取
        if level2_is_absolute:
            return FieldFlattener._flatten_with_absolute_paths(
                data, level1_path, level2_path, level3_path, separator,
                level1_field, level2_field, level3_field
            )
        
        # 相对路径模式（原有逻辑）
        return FieldFlattener._flatten_with_relative_paths(
            data, level1_values, level1_path, level2_path, level3_path, separator,
            level1_field, level2_field, level3_field
        )

    @staticmethod
    def _flatten_with_absolute_paths(
        data: Any,
        level1_path: str,
        level2_path: str,
        level3_path: str,
        separator: str = "-",
        level1_field: str = None,
        level2_field: str = None,
        level3_field: str = None
    ) -> List[str]:
        """
        使用绝对路径模式展平数据
        
        适用于配置如：
        - level1_path: $.data.children[*].summary
        - level2_path: $.data.children[*].children[*].summary
        
        实现思路：
        1. 从level1_path提取父级对象（不是字段值）
        2. 对每个父级对象，使用相对路径提取子级
        """
        result: List[str] = []
        
        # 从level1_path推断父级对象路径（去掉最后的字段访问）
        # 例如：$.data.children[*].summary -> $.data.children[*]
        level1_obj_path = level1_path.rsplit('.', 1)[0] if '.' in level1_path else level1_path
        
        # 提取父级对象
        parent_objects = FieldFlattener._apply_jsonpath(data, level1_obj_path) if level1_obj_path else []
        if not parent_objects:
            return result
        
        # 从level2_path推断子级字段名和路径
        # 例如：$.data.children[*].children[*].summary -> children[*].summary
        if level2_path:
            # 移除共同前缀，得到相对路径
            level2_relative = level2_path
            if level2_path.startswith(level1_obj_path):
                level2_relative = level2_path[len(level1_obj_path):].lstrip('.')
            
            # 处理每个父级对象
            for parent_obj in parent_objects:
                # 提取父级字段值
                parent_field = level1_path.rsplit('.', 1)[-1] if '.' in level1_path else None
                parent_str = FieldFlattener._extract_value(parent_obj, parent_field)
                
                # 从父级对象中提取子级
                child_values = FieldFlattener._apply_jsonpath(parent_obj, level2_relative) if level2_relative else []
                
                # 提取子级字段名
                child_field = level2_path.rsplit('.', 1)[-1] if '.' in level2_path else None
                
                for child_val in child_values:
                    child_str = FieldFlattener._extract_value(child_val, child_field)
                    combined = f"{parent_str}{separator}{child_str}"
                    result.append(combined)
        
        return list(dict.fromkeys(result))

    @staticmethod
    def _flatten_with_relative_paths(
        data: Any,
        level1_values: List[Any],
        level1_path: str,
        level2_path: str,
        level3_path: str,
        separator: str = "-",
        level1_field: str = None,
        level2_field: str = None,
        level3_field: str = None
    ) -> List[str]:
        """
        使用相对路径模式展平数据（原有逻辑）
        
        适用于配置如：
        - level1_path: $.data.children[*]
        - level2_path: $.children[*].summary
        """
        result: List[str] = []
        
        # 处理第一级和第二级
        for level1_val in level1_values:
            level1_str = FieldFlattener._extract_value(level1_val, level1_field)
            
            # 第二级提取（相对于level1_val）
            level2_values = FieldFlattener._apply_jsonpath(level1_val, level2_path) if level2_path else []
            
            if not level2_values and level1_val:
                # 没有第二级数据，直接使用第一级
                result.append(level1_str)
                continue
            
            # 只有第二级的情况
            if not level3_path:
                for level2_val in level2_values:
                    level2_str = FieldFlattener._extract_value(level2_val, level2_field)
                    combined = f"{level1_str}{separator}{level2_str}"
                    result.append(combined)
                continue
            
            # 处理第三级
            for level2_val in level2_values:
                level2_str = FieldFlattener._extract_value(level2_val, level2_field)
                
                # 第三级提取（相对于level2_val）
                level3_values = FieldFlattener._apply_jsonpath(level2_val, level3_path) if level3_path else []
                
                if not level3_values:
                    # 没有第三级数据，使用前两级
                    combined = f"{level1_str}{separator}{level2_str}"
                    result.append(combined)
                    continue
                
                for level3_val in level3_values:
                    level3_str = FieldFlattener._extract_value(level3_val, level3_field)
                    combined = f"{level1_str}{separator}{level2_str}{separator}{level3_str}"
                    result.append(combined)
        
        # 去重
        return list(dict.fromkeys(result))

    @staticmethod
    def flatten_field_options(
        data: Any,
        flatten_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        展平字段选项

        Args:
            data: 原始API数据
            flatten_config: 展平配置，结构:
                {
                    "label_path_level1": "...",
                    "label_path_level2": "...", 
                    "label_path_level3": "...",
                    "label_separator": "-",
                    "label_field_level1": "...",  # 可选，从对象中提取的字段名
                    "label_field_level2": "...",
                    "label_field_level3": "...",
                    "value_path_level1": "...",
                    "value_path_level2": "...",
                    "value_path_level3": "...",
                    "value_separator": "-",
                    "value_field_level1": "...",  # 可选
                    "value_field_level2": "...",
                    "value_field_level3": "..."
                }

        Returns:
            展平后的选项列表，格式: [{"label": "...", "value": "..."}]
        """
        if not data or not flatten_config:
            return []
        
        try:
            # 提取标签
            label_list = FieldFlattener._flatten_with_paths(
                data,
                flatten_config.get("label_path_level1", ""),
                flatten_config.get("label_path_level2", ""),
                flatten_config.get("label_path_level3", ""),
                flatten_config.get("label_separator", "-"),
                flatten_config.get("label_field_level1"),
                flatten_config.get("label_field_level2"),
                flatten_config.get("label_field_level3")
            )
            
            # 提取值
            value_list = FieldFlattener._flatten_with_paths(
                data,
                flatten_config.get("value_path_level1", ""),
                flatten_config.get("value_path_level2", ""),
                flatten_config.get("value_path_level3", ""),
                flatten_config.get("value_separator", "-"),
                flatten_config.get("value_field_level1"),
                flatten_config.get("value_field_level2"),
                flatten_config.get("value_field_level3")
            )
            
            # 组合标签和值
            min_len = min(len(label_list), len(value_list))
            options = []
            for i in range(min_len):
                options.append({
                    "label": label_list[i],
                    "value": value_list[i],
                    "is_deleted": False
                })
            
            logger.info(f"[FieldFlattener] 展平完成: 生成 {len(options)} 个选项")
            return options
            
        except Exception as e:
            logger.error(f"[FieldFlattener] 展平失败: {e}")
            return []

    @staticmethod
    def merge_flatten_config(
        config1: Dict[str, Any],
        config2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并两个展平配置，config2会覆盖config1

        Args:
            config1: 配置1
            config2: 配置2

        Returns:
            合并后的配置
        """
        merged = {**config1, **config2}
        # 过滤掉空值
        return {k: v for k, v in merged.items() if v is not None}
