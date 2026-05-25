"""
Prompt 构建服务 - 提供统一的 Prompt 构建功能

设计原则：
1. 单一职责：每个方法只构建一种类型的 Prompt
2. 纯函数：无副作用，便于单元测试
3. 可复用：多处调用统一入口
"""

from typing import Any, Dict, List, Optional


class PromptBuilderService:
    """Prompt 构建服务 - 提供可复用的 Prompt 构建功能"""

    @staticmethod
    def build_choice_prompt_table(
        filtered_data: List[Dict[str, Any]],
        name_fields: List[str],
        rule_fields: List[str],
        name_separator: str = " - "
    ) -> str:
        """
        构建选择题 Prompt 的 Markdown 表格（去掉选项列，只保留选项名称和判定规则）

        Args:
            filtered_data: 筛选后的数据行
            name_fields: 名称字段列表
            rule_fields: 规则字段列表
            name_separator: 名称分隔符

        Returns:
            Markdown 格式的表格字符串

        Example:
            >>> data = [
            ...     {"name": "产品A", "price": "100", "stock": "10"},
            ...     {"name": "产品B", "price": "50", "stock": "5"}
            ... ]
            >>> table = PromptBuilderService.build_choice_prompt_table(
            ...     data, ["name"], ["price", "stock"], " - "
            ... )
            >>> print(table)
            | 选项名称 | 判定规则 |
            |----------|----------|
            | 产品A | 100; 10 |
            | 产品B | 50; 5 |
        """
        if not filtered_data:
            return "| 选项名称 | 判定规则 |\n|----------|----------|\n"

        # 表头（去掉选项列）
        md_table = "| 选项名称 | 判定规则 |\n"
        md_table += "|----------|----------|\n"

        for i, row in enumerate(filtered_data, 1):
            # 构建选项名称
            option_name = PromptBuilderService._build_name_from_fields(
                row, name_fields, name_separator
            )
            if not option_name:
                option_name = f"选项{i}"

            # 构建规则描述
            rule_desc = PromptBuilderService._build_name_from_fields(
                row, rule_fields, "; "
            )

            md_table += f"| {option_name} | {rule_desc} |\n"

        return md_table

    @staticmethod
    def _build_name_from_fields(
        row: Dict[str, Any],
        fields: List[str],
        separator: str = " - "
    ) -> str:
        """
        从字段构建名称

        Args:
            row: 数据行
            fields: 字段列表
            separator: 分隔符

        Returns:
            构建的名称字符串
        """
        if not fields:
            return ""

        parts = []
        for field in fields:
            val = row.get(field, "")
            if val is not None and str(val).strip():
                parts.append(str(val))

        return separator.join(parts) if parts else ""

    @staticmethod
    def build_multi_task_choice_prompt(
        task_num: int,
        rule_name: str,
        filtered_data: List[Dict[str, Any]],
        name_fields: List[str],
        rule_fields: List[str],
        name_separator: str = " - "
    ) -> str:
        """
        构建多任务场景下的选择题 Prompt 部分

        Args:
            task_num: 任务序号
            rule_name: 规则名称
            filtered_data: 筛选后的数据
            name_fields: 名称字段列表
            rule_fields: 规则字段列表
            name_separator: 名称分隔符

        Returns:
            任务提示词部分
        """
        lines = [f"=== 任务{task_num}：{rule_name} ==="]
        lines.append("请从以下选项中选择最匹配的一个：")

        # 构建 Markdown 表格
        md_table = PromptBuilderService.build_choice_prompt_table(
            filtered_data=filtered_data,
            name_fields=name_fields,
            rule_fields=rule_fields,
            name_separator=name_separator
        )
        lines.append(md_table)

        return "\n".join(lines)

    @staticmethod
    def build_multi_task_text_prompt(
        task_num: int,
        rule_name: str,
        filtered_data: List[Dict[str, Any]],
        rule_fields: List[str]
    ) -> str:
        """
        构建多任务场景下的填空题 Prompt 部分

        Args:
            task_num: 任务序号
            rule_name: 规则名称
            filtered_data: 筛选后的数据
            rule_fields: 规则字段列表

        Returns:
            任务提示词部分
        """
        lines = [f"=== 任务{task_num}：{rule_name} ==="]
        lines.append("请根据以下规则生成内容：")

        # 构建规则描述
        if filtered_data:
            for i, row in enumerate(filtered_data, 1):
                rule_desc = PromptBuilderService._build_name_from_fields(
                    row, rule_fields, "\n"
                )
                if rule_desc:
                    lines.append(f"{i}. {rule_desc}")

        return "\n".join(lines)
