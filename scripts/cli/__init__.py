#!/usr/bin/env python3
"""
自动填单 CLI 工具包

提供以下命令行工具：
- get_form_fields.py: 获取表单待填字段列表
- get_field_options.py: 获取下拉字段的选项列表
- get_field_rules.py: 获取字段填写规则
- get_template.py: 获取服务记录模板
- submit_form.py: 提交表单数据

使用方法：
    python -m scripts.cli.get_form_fields --help
    python -m scripts.cli.get_field_options --field_id event_type_level1
    python -m scripts.cli.get_field_rules --field_id service_summary
    python -m scripts.cli.get_template --event_type_id EVT001001001
    python -m scripts.cli.submit_form --level1 EVT001 --level2 EVT001001 --level3 EVT001001001 --summary "..."
"""

__version__ = "1.0.0"
__all__ = [
    "get_form_fields",
    "get_field_options",
    "get_field_rules",
    "get_template",
    "submit_form",
]
