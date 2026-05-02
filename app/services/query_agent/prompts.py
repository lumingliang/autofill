"""
Prompt 模板
"""

# 参数提取 Prompt
EXTRACT_PARAMS_PROMPT = """你是一个智能参数提取专家。请根据用户的查询语句和系统提示词，从以下可用字段中选择合适的值来构建搜索参数。

可用字段: {placeholder_fields}

系统提示词（定义了查询目标和判断标准）:
{system_prompt}

用户查询:
{query}

要求：
1. 只使用提供的可用字段
2. 如果某个字段无法确定，可以留空或不包含
3. 考虑同义词、简称、可能的拼写变体
4. 返回格式必须是有效的 JSON

返回格式:
{{
    "parameters": {{
        "field_name": "extracted_value"
    }},
    "reasoning": "简要说明为什么选择这些参数"
}}"""

# 结果分析 Prompt
ANALYZE_RESULTS_PROMPT = """你是一个数据匹配专家。根据系统提示词中定义的目标，分析搜索结果，判断是否有满足条件的数据。

系统提示词:
{system_prompt}

用户原始查询:
{query}

当前搜索参数:
{current_parameters}

搜索结果（共 {result_count} 条）:
{results}

请按以下 JSON 格式返回分析结果:
{{
    "is_satisfied": true/false,
    "selected_indices": [0, 1],
    "reasoning": "详细说明为什么这些记录满足/不满足条件",
    "suggestion": "如果没找到，建议如何调整搜索参数"
}}"""

# 参数优化 Prompt
OPTIMIZE_PARAMS_PROMPT = """你是一个搜索优化专家。根据之前的搜索结果和分析反馈，优化搜索参数以获得更好的结果。

系统提示词:
{system_prompt}

用户查询:
{query}

搜索历史:
{search_history}

上次分析反馈:
{last_analysis}

可用字段:
{placeholder_fields}

优化策略：
1. 纠正可能的拼写错误
2. 使用同义词或相关词
3. 扩大或缩小搜索范围
4. 尝试不同的字段组合
5. 使用简称或全称

返回格式:
{{
    "parameters": {{
        "field_name": "new_value"
    }},
    "optimization_reasoning": "说明为什么这样优化",
    "expected_improvement": "预期能改善什么"
}}"""


def format_extract_params_prompt(
    query: str,
    system_prompt: str,
    placeholder_fields: list
) -> str:
    """格式化参数提取 Prompt"""
    return EXTRACT_PARAMS_PROMPT.format(
        query=query,
        system_prompt=system_prompt,
        placeholder_fields=", ".join(placeholder_fields) if placeholder_fields else "无"
    )


def format_analyze_results_prompt(
    query: str,
    system_prompt: str,
    current_parameters: dict,
    results: str,
    result_count: int
) -> str:
    """格式化结果分析 Prompt"""
    return ANALYZE_RESULTS_PROMPT.format(
        query=query,
        system_prompt=system_prompt,
        current_parameters=str(current_parameters),
        results=results,
        result_count=result_count
    )


def format_optimize_params_prompt(
    query: str,
    system_prompt: str,
    search_history: str,
    last_analysis: str,
    placeholder_fields: list
) -> str:
    """格式化参数优化 Prompt"""
    return OPTIMIZE_PARAMS_PROMPT.format(
        query=query,
        system_prompt=system_prompt,
        search_history=search_history,
        last_analysis=last_analysis,
        placeholder_fields=", ".join(placeholder_fields) if placeholder_fields else "无"
    )
