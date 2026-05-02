"""
工具函数
"""
import re
from typing import Any, Dict, Optional


def replace_placeholders(template: Any, parameters: Dict[str, str]) -> Any:
    """
    递归替换模板中的占位符

    Args:
        template: 可能包含占位符的数据结构
        parameters: 参数键值对

    Returns:
        替换后的数据结构
    """
    if isinstance(template, dict):
        result = {}
        for k, v in template.items():
            if isinstance(v, str):
                result[k] = replace_placeholder_in_string(v, parameters)
            else:
                result[k] = replace_placeholders(v, parameters)
        return result
    elif isinstance(template, list):
        return [replace_placeholders(item, parameters) for item in template]
    elif isinstance(template, str):
        return replace_placeholder_in_string(template, parameters)
    else:
        return template


def replace_placeholder_in_string(s: str, parameters: Dict[str, str]) -> str:
    """替换字符串中的 {{field}} 占位符"""
    pattern = r'\{\{(\w+)\}\}'

    def replacer(match):
        field = match.group(1)
        return parameters.get(field, match.group(0))  # 找不到保留原样

    return re.sub(pattern, replacer, s)


def replace_placeholders_in_curl(curl_template: str, parameters: Dict[str, str]) -> str:
    """
    替换 curl 命令模板中的占位符

    Args:
        curl_template: curl 命令模板字符串
        parameters: 参数键值对

    Returns:
        替换后的 curl 命令字符串
    """
    return replace_placeholder_in_string(curl_template, parameters)


def extract_by_selector(data: Any, selector: str) -> Any:
    """
    根据选择器提取数据

    支持格式：
    - JSONPath: $.data.items[0]
    - 点号路径: data.items.0

    Args:
        data: 原始数据
        selector: 选择器字符串

    Returns:
        提取的数据
    """
    if not selector or not data:
        return data

    try:
        if selector.startswith("$."):
            # JSONPath 格式
            try:
                import jsonpath_ng
                jsonpath_expr = jsonpath_ng.parse(selector)
                matches = jsonpath_expr.find(data)
                if not matches:
                    return None
                if len(matches) == 1:
                    return matches[0].value
                return [match.value for match in matches]
            except ImportError:
                # 如果没有安装 jsonpath_ng，回退到点号路径
                selector = selector[2:]  # 移除 $. 前缀
                return _extract_by_dot_path(data, selector)
        else:
            # 点号路径格式
            return _extract_by_dot_path(data, selector)
    except Exception:
        return data


def _extract_by_dot_path(data: Any, path: str) -> Any:
    """使用点号路径提取数据"""
    keys = path.split(".")
    result = data

    for key in keys:
        if result is None:
            return None

        # 处理数组索引，如 items[0] 或 items.0
        array_match = re.match(r'(\w+)\[(\d+)\]', key)
        if array_match:
            # 格式: items[0]
            field_name = array_match.group(1)
            index = int(array_match.group(2))
            if isinstance(result, dict) and field_name in result:
                result = result[field_name]
                if isinstance(result, list) and index < len(result):
                    result = result[index]
                else:
                    return None
            else:
                return None
        elif key.isdigit():
            # 格式: 0 (数组索引)
            index = int(key)
            if isinstance(result, list) and index < len(result):
                result = result[index]
            else:
                return None
        elif isinstance(result, dict):
            result = result.get(key)
        else:
            return None

    return result


def clean_json_response(content: str) -> str:
    """
    清理 LLM 返回的 JSON 字符串

    移除 markdown 代码块标记等
    """
    # 移除 markdown 代码块标记
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    return content.strip()


def truncate_data_for_llm(data: Any, max_length: int = 4000) -> str:
    """
    截断数据以适应 LLM 上下文限制

    Args:
        data: 原始数据
        max_length: 最大长度

    Returns:
        截断后的字符串表示
    """
    import json

    try:
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        if len(json_str) <= max_length:
            return json_str

        # 截断并添加提示
        truncated = json_str[:max_length]
        return truncated + f"\n... (数据已截断，原始长度: {len(json_str)})"
    except Exception:
        str_repr = str(data)
        if len(str_repr) <= max_length:
            return str_repr
        return str_repr[:max_length] + f"\n... (数据已截断)"


def select_results(data: Any, selector: Optional[str] = None) -> Any:
    """
    根据选择器从数据中选择结果

    Args:
        data: 原始数据
        selector: 选择器字符串（JSONPath 或点号路径），为 None 则返回完整数据

    Returns:
        选择后的数据
    """
    if not selector:
        return data

    return extract_by_selector(data, selector)
