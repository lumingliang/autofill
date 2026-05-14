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
    def _flatten_with_paths(
        data: Any,
        level1_path: str,
        level2_path: str,
        level3_path: str,
        separator: str = "-"
    ) -> List[str]:
        """
        使用三级路径配置展平数据

        Args:
            data: 原始数据
            level1_path: 第一级路径
            level2_path: 第二级路径
            level3_path: 第三级路径
            separator: 拼接符

        Returns:
            展平后的字符串列表
        """
        if not data:
            return []
        
        result: List[str] = []
        
        # 第一级
        level1_values = FieldFlattener._apply_jsonpath(data, level1_path) if level1_path else []
        if not level1_values:
            return result
        
        # 只有第一级的情况
        if not level2_path:
            result = [str(v) for v in level1_values if v is not None]
            return result
        
        # 处理第一级和第二级
        for level1_val in level1_values:
            level1_str = str(level1_val) if level1_val is not None else ""
            
            # 第二级提取
            level2_values = FieldFlattener._apply_jsonpath(level1_val, level2_path) if level2_path else []
            
            if not level2_values and level1_val:
                # 没有第二级数据，直接使用第一级
                result.append(level1_str)
                continue
            
            # 只有第二级的情况
            if not level3_path:
                for level2_val in level2_values:
                    level2_str = str(level2_val) if level2_val is not None else ""
                    combined = f"{level1_str}{separator}{level2_str}"
                    result.append(combined)
                continue
            
            # 处理第三级
            for level2_val in level2_values:
                level2_str = str(level2_val) if level2_val is not None else ""
                
                # 第三级提取
                level3_values = FieldFlattener._apply_jsonpath(level2_val, level3_path) if level3_path else []
                
                if not level3_values:
                    # 没有第三级数据，使用前两级
                    combined = f"{level1_str}{separator}{level2_str}"
                    result.append(combined)
                    continue
                
                for level3_val in level3_values:
                    level3_str = str(level3_val) if level3_val is not None else ""
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
                    "value_path_level1": "...",
                    "value_path_level2": "...",
                    "value_path_level3": "...",
                    "value_separator": "-"
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
                flatten_config.get("label_separator", "-")
            )
            
            # 提取值
            value_list = FieldFlattener._flatten_with_paths(
                data,
                flatten_config.get("value_path_level1", ""),
                flatten_config.get("value_path_level2", ""),
                flatten_config.get("value_path_level3", ""),
                flatten_config.get("value_separator", "-")
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
