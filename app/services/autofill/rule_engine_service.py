"""
规则执行引擎服务
实现基于CSV规则的选择题(choice)和填空题(text)处理
"""
import json
import time
from typing import Any, Dict, List, Optional, Tuple

from app.log import logger
from app.models.autofill import FillDataRecord
from app.models.enums import AIFillDataStatus
from app.models.rule_management import RuleInfo, RuleVersion
from app.services.autofill.prompt_builder_service import PromptBuilderService
from app.services.autofill.system_prompt_service import system_prompt_service
from app.services.llm.llm_config_service import llm_config_service
from app.services.llm.llm_proxy_service import llm_proxy_service
from app.services.rule_management.rule_service import rule_service


class RuleEngineService:
    """规则执行引擎服务"""

    async def execute_rule(
        self,
        tenant_id: int,
        app_name: str,
        session_id: str,
        query: str,
        method: str,
        temperature: float,
        params: List[Dict[str, Any]],
        step: int = 1,
        is_last: bool = False,
        system_prompt: Optional[str] = None,
        system_prompt_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行规则引擎

        Args:
            tenant_id: 租户ID
            app_name: 应用名称
            session_id: 会话ID
            query: 用户输入文本
            method: LLM调用方法
            temperature: 温度参数
            params: 规则执行参数列表
            step: 当前步骤
            is_last: 是否为最后一步
            system_prompt: 自定义系统提示词（可选）
            system_prompt_name: 系统提示词名称（可选）

        Returns:
            执行结果
        """
        start_time = time.time()
        results = {}

        # 保存请求数据（如果是第一步）
        if step == 1:
            await self._save_step_request(
                session_id=session_id,
                tenant_id=tenant_id,
                app_name=app_name,
                query=query,
                method=method,
                params=params,
                step=step
            )

        # 根据方法类型选择处理方式
        if method == "json_parser" and len(params) > 1:
            # json_parser 多任务场景：一次性调用LLM，生成包含所有任务的提示词
            try:
                results = await self._execute_multi_task_json_parser(
                    tenant_id=tenant_id,
                    app_name=app_name,
                    query=query,
                    method=method,
                    temperature=temperature,
                    params=params,
                    system_prompt=system_prompt,
                    system_prompt_name=system_prompt_name
                )
            except Exception as e:
                logger.error(f"执行多任务json_parser失败: {e}")
                # 初始化所有任务为失败状态
                for param in params:
                    rule_name = param.get("rule_name")
                    if rule_name:
                        results[rule_name] = {"llm_res": "", "error": str(e)}
        else:
            # plain 方法或单任务场景：逐个处理每个规则参数
            for param in params:
                rule_name = param.get("rule_name")
                prompt_config = param.get("prompt", {})

                if not rule_name or not prompt_config:
                    continue

                # 从 prompt_config 中获取该规则特定的 system_prompt_name（如果存在）
                param_system_prompt_name = prompt_config.get("system_prompt_name") or system_prompt_name

                try:
                    rule_result = await self._execute_single_rule(
                        tenant_id=tenant_id,
                        app_name=app_name,
                        query=query,
                        method=method,
                        temperature=temperature,
                        rule_name=rule_name,
                        prompt_config=prompt_config,
                        system_prompt=system_prompt,
                        system_prompt_name=param_system_prompt_name
                    )
                    results[rule_name] = rule_result
                except Exception as e:
                    logger.error(f"执行规则失败: {rule_name}, error: {e}")
                    results[rule_name] = {
                        "llm_res": "",
                        "error": str(e)
                    }

        elapsed_time = time.time() - start_time

        # 保存步骤结果
        await self._save_step_result(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name,
            step=step,
            results=results,
            elapsed_time=elapsed_time,
            is_last=is_last
        )

        return {
            "session_id": session_id,
            "step": step,
            "is_last": is_last,
            "status": "completed" if is_last else "processing",
            "elapsed_time": elapsed_time,
            "results": results
        }

    async def _execute_single_rule(
        self,
        tenant_id: int,
        app_name: str,
        query: str,
        method: str,
        temperature: float,
        rule_name: str,
        prompt_config: Dict[str, Any],
        system_prompt: Optional[str] = None,
        system_prompt_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行单个规则

        Args:
            tenant_id: 租户ID
            app_name: 应用名称
            query: 用户输入
            method: LLM方法
            temperature: 温度
            rule_name: 规则名称
            prompt_config: Prompt配置
            system_prompt: 自定义系统提示词（可选）
            system_prompt_name: 系统提示词名称（可选）

        Returns:
            规则执行结果
        """
        # 1. 获取规则数据
        rule_data = await self._get_rule_data(
            tenant_id=tenant_id,
            app_name=app_name,
            rule_name=rule_name
        )

        if not rule_data:
            raise ValueError(f"规则不存在: {rule_name}")

        # 3. 获取任务类型和配置
        task_type = prompt_config.get("type", "choice")
        select_fields = prompt_config.get("select_fields", [])
        name_fields = prompt_config.get("name_fields", [])
        rule_fields = prompt_config.get("rule_fields", [])
        name_separator = prompt_config.get("name_separator", " - ")

        # 2. 根据filter筛选数据（传入name_fields用于去重）
        filtered_data = self._apply_filter(
            rule_data=rule_data,
            filter_config=prompt_config.get("filter", {}),
            name_fields=name_fields
        )

        if not filtered_data:
            raise ValueError(f"规则数据为空: {rule_name}")

        # 4. 生成Prompt
        if task_type == "choice":
            system_prompt, full_prompt = await self._build_choice_prompt(
                tenant_id=tenant_id,
                query=query,
                filtered_data=filtered_data,
                name_fields=name_fields,
                rule_fields=rule_fields,
                name_separator=name_separator,
                method=method,
                system_prompt=system_prompt,
                system_prompt_name=system_prompt_name
            )
        else:  # text
            system_prompt, full_prompt = await self._build_text_prompt(
                tenant_id=tenant_id,
                query=query,
                filtered_data=filtered_data,
                rule_fields=rule_fields,
                method=method,
                rule_name=rule_name,
                system_prompt=system_prompt,
                system_prompt_name=system_prompt_name
            )

        # 5. 调用LLM
        llm_result = await self._call_llm(
            query=query,
            system_prompt=system_prompt,
            full_prompt=full_prompt,
            method=method,
            temperature=temperature,
            task_type=task_type,
            rule_name=rule_name
        )

        # 6. 处理结果
        # 如果返回的是字典（json_parser方法），提取对应rule_name的字段值
        if isinstance(llm_result, dict):
            llm_result = llm_result.get(rule_name, "")

        if task_type == "choice":
            result = self._process_choice_result(
                llm_result=llm_result,
                filtered_data=filtered_data,
                select_fields=select_fields,
                name_fields=name_fields,
                name_separator=name_separator
            )
        else:  # text
            result = self._process_text_result(
                llm_result=llm_result,
                filtered_data=filtered_data,
                select_fields=select_fields
            )

        return result

    async def _execute_multi_task_json_parser(
        self,
        tenant_id: int,
        app_name: str,
        query: str,
        method: str,
        temperature: float,
        params: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        system_prompt_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行多任务json_parser方法
        一次性调用LLM，生成包含所有任务的提示词，解析返回的JSON结果

        Args:
            tenant_id: 租户ID
            app_name: 应用名称
            query: 用户输入
            method: LLM方法（json_parser）
            temperature: 温度
            params: 多个规则参数列表
            system_prompt: 自定义系统提示词（可选）
            system_prompt_name: 系统提示词名称（可选）

        Returns:
            所有任务的执行结果
        """
        results = {}
        task_prompts = []
        task_infos = []  # 存储每个任务的信息，用于后续匹配

        # 1. 准备所有任务的数据和提示词
        for idx, param in enumerate(params, 1):
            rule_name = param.get("rule_name")
            prompt_config = param.get("prompt", {})

            if not rule_name or not prompt_config:
                continue

            # 获取规则数据
            rule_data = await self._get_rule_data(
                tenant_id=tenant_id,
                app_name=app_name,
                rule_name=rule_name
            )

            if not rule_data:
                results[rule_name] = {"llm_res": "", "error": f"规则不存在: {rule_name}"}
                continue

            # 获取任务配置
            task_type = prompt_config.get("type", "choice")
            select_fields = prompt_config.get("select_fields", [])
            name_fields = prompt_config.get("name_fields", [])
            rule_fields = prompt_config.get("rule_fields", [])
            name_separator = prompt_config.get("name_separator", " - ")

            # 筛选数据（传入name_fields用于去重）
            filtered_data = self._apply_filter(
                rule_data=rule_data,
                filter_config=prompt_config.get("filter", {}),
                name_fields=name_fields
            )

            if not filtered_data:
                results[rule_name] = {"llm_res": "", "error": f"规则数据为空: {rule_name}"}
                continue

            # 构建任务提示词
            task_prompt = self._build_multi_task_prompt_section(
                task_num=idx,
                rule_name=rule_name,
                task_type=task_type,
                filtered_data=filtered_data,
                name_fields=name_fields,
                rule_fields=rule_fields,
                name_separator=name_separator
            )
            task_prompts.append(task_prompt)

            # 保存任务信息用于后续处理
            task_infos.append({
                "rule_name": rule_name,
                "task_type": task_type,
                "filtered_data": filtered_data,
                "select_fields": select_fields,
                "name_fields": name_fields,
                "name_separator": name_separator
            })

        if not task_prompts:
            return results

        # 2. 构建返回格式说明
        response_format = "{\n" + ",\n".join([f'  "{info["rule_name"]}": ""' for info in task_infos]) + "\n}"

        # 3. 获取系统提示词（支持动态配置，已包含兜底逻辑和变量替换）
        final_system_prompt = await system_prompt_service.get_system_prompt_for_execution(
            tenant_id=tenant_id,
            system_prompt=system_prompt,
            system_prompt_name=system_prompt_name,
            category="multi_task",
            variables={
                "task_prompts": task_prompts,
                "query": query,
                "response_format": response_format
            }
        )

        # 4. 调用LLM
        llm_result = await self._call_llm(
            query=query,
            system_prompt=final_system_prompt,
            full_prompt=final_system_prompt,
            method=method,
            temperature=temperature,
            task_type="multi_task",
            rule_name="multi_task"
        )

        # 7. 解析LLM返回的JSON
        try:
            # 如果已经是字典，直接使用；否则尝试解析JSON字符串
            if isinstance(llm_result, dict):
                parsed_result = llm_result
            else:
                parsed_result = json.loads(llm_result)
            if not isinstance(parsed_result, dict):
                raise ValueError("LLM返回的不是JSON对象")
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"解析LLM返回的JSON失败: {e}, 原始结果: {llm_result}")
            # 如果解析失败，为所有任务返回错误
            for info in task_infos:
                results[info["rule_name"]] = {
                    "llm_res": str(llm_result),
                    "error": f"JSON解析失败: {e}"
                }
            return results

        # 8. 处理每个任务的结果
        for info in task_infos:
            rule_name = info["rule_name"]
            task_type = info["task_type"]
            filtered_data = info["filtered_data"]
            select_fields = info["select_fields"]
            name_fields = info["name_fields"]
            name_separator = info["name_separator"]

            # 获取LLM返回的该任务结果
            task_llm_result = parsed_result.get(rule_name, "")

            # 处理结果
            if task_type == "choice":
                result = self._process_choice_result(
                    llm_result=task_llm_result,
                    filtered_data=filtered_data,
                    select_fields=select_fields,
                    name_fields=name_fields,
                    name_separator=name_separator
                )
            else:  # text
                result = self._process_text_result(
                    llm_result=task_llm_result,
                    filtered_data=filtered_data,
                    select_fields=select_fields
                )

            results[rule_name] = result

        return results

    def _build_multi_task_prompt_section(
        self,
        task_num: int,
        rule_name: str,
        task_type: str,
        filtered_data: List[Dict[str, Any]],
        name_fields: List[str],
        rule_fields: List[str],
        name_separator: str
    ) -> str:
        """
        构建多任务提示词的单个任务部分
        使用 PromptBuilderService 统一构建

        Args:
            task_num: 任务序号
            rule_name: 规则名称
            task_type: 任务类型（choice/text）
            filtered_data: 筛选后的数据
            name_fields: 名称字段列表
            rule_fields: 规则字段列表
            name_separator: 名称分隔符

        Returns:
            任务提示词部分
        """
        if task_type == "choice":
            # 使用 PromptBuilderService 统一构建选择题 Prompt
            return PromptBuilderService.build_multi_task_choice_prompt(
                task_num=task_num,
                rule_name=rule_name,
                filtered_data=filtered_data,
                name_fields=name_fields,
                rule_fields=rule_fields,
                name_separator=name_separator
            )
        else:  # text
            # 使用 PromptBuilderService 统一构建填空题 Prompt
            return PromptBuilderService.build_multi_task_text_prompt(
                task_num=task_num,
                rule_name=rule_name,
                filtered_data=filtered_data,
                rule_fields=rule_fields
            )

    async def _get_rule_data(
        self,
        tenant_id: int,
        app_name: str,
        rule_name: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取规则数据

        Args:
            tenant_id: 租户ID
            app_name: 应用名称
            rule_name: 规则名称（即rule_code）

        Returns:
            规则数据列表
        """
        # 查询规则
        rule = await RuleInfo.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            rule_code=rule_name,
            deleted=0,
            status=1
        ).first()

        if not rule or not rule.latest_version_id:
            return None

        # 获取最新版本
        version = await RuleVersion.filter(
            id=rule.latest_version_id,
            deleted=0
        ).first()

        if not version:
            return None

        # 获取内容
        content_json = await rule_service._get_content_json(version)
        if not content_json:
            return None

        # 转换为字典列表
        headers = content_json.get("headers", [])
        data = content_json.get("data", [])

        result = []
        for row in data:
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    row_dict[header] = row[i]
                else:
                    row_dict[header] = ""
            result.append(row_dict)

        return result

    def _apply_filter(
        self,
        rule_data: List[Dict[str, Any]],
        filter_config: Dict[str, Any],
        name_fields: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        应用filter筛选数据，并根据name_fields去重

        Args:
            rule_data: 规则数据
            filter_config: 筛选配置
            name_fields: 名称字段列表，用于去重

        Returns:
            筛选并去重后的数据
        """
        # 先进行filter筛选
        if filter_config:
            result = []
            for row in rule_data:
                match = True
                for key, value in filter_config.items():
                    if row.get(key) != value:
                        match = False
                        break
                if match:
                    result.append(row)
        else:
            result = rule_data

        # 根据name_fields去重
        if name_fields:
            seen = set()
            deduplicated = []
            for row in result:
                # 构建唯一键：根据name_fields的值组合
                key_parts = []
                for field in name_fields:
                    value = row.get(field)
                    if value is not None:
                        key_parts.append(str(value))
                key = tuple(key_parts) if key_parts else None

                if key and key not in seen:
                    seen.add(key)
                    deduplicated.append(row)
                elif not key:
                    # 如果无法构建key，保留数据
                    deduplicated.append(row)
            return deduplicated

        return result

    async def _build_choice_prompt(
        self,
        tenant_id: int,
        query: str,
        filtered_data: List[Dict[str, Any]],
        name_fields: List[str],
        rule_fields: List[str],
        name_separator: str,
        method: str = "plain",
        system_prompt: Optional[str] = None,
        system_prompt_name: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        构建选择题Prompt

        Args:
            tenant_id: 租户ID
            query: 用户输入
            filtered_data: 筛选后的数据
            name_fields: 名称字段列表
            rule_fields: 规则字段列表
            name_separator: 名称分隔符
            method: LLM调用方法
            system_prompt: 自定义系统提示词（可选）
            system_prompt_name: 系统提示词名称（可选）

        Returns:
            (system_prompt, full_prompt)
        """
        # 使用 PromptBuilderService 构建 Markdown 表格
        md_table = PromptBuilderService.build_choice_prompt_table(
            filtered_data=filtered_data,
            name_fields=name_fields,
            rule_fields=rule_fields,
            name_separator=name_separator
        )

        # 获取系统提示词（支持动态配置，已包含兜底逻辑和变量替换）
        final_system_prompt = await system_prompt_service.get_system_prompt_for_execution(
            tenant_id=tenant_id,
            system_prompt=system_prompt,
            system_prompt_name=system_prompt_name,
            category="choice",
            variables={
                "task_prompts": md_table,
                "query": query
            }
        )

        # 直接使用获取的提示词
        return final_system_prompt, final_system_prompt

    async def _build_text_prompt(
        self,
        tenant_id: int,
        query: str,
        filtered_data: List[Dict[str, Any]],
        rule_fields: List[str],
        method: str = "plain",
        rule_name: str = "",
        system_prompt: Optional[str] = None,
        system_prompt_name: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        构建填空题Prompt

        Args:
            tenant_id: 租户ID
            query: 用户输入
            filtered_data: 筛选后的数据（应该只有一条）
            rule_fields: 规则字段列表
            method: LLM调用方法
            rule_name: 规则名称（用于json_parser方法生成JSON key）
            system_prompt: 自定义系统提示词（可选）
            system_prompt_name: 系统提示词名称（可选）

        Returns:
            (system_prompt, full_prompt)
        """
        if not filtered_data:
            raise ValueError("填空题必须匹配且仅匹配一条规则")

        row = filtered_data[0]

        # 构建规则描述
        rule_desc = self._build_name_from_fields(row, rule_fields, "\n")

        # 获取系统提示词（支持动态配置，已包含兜底逻辑和变量替换）
        final_system_prompt = await system_prompt_service.get_system_prompt_for_execution(
            tenant_id=tenant_id,
            system_prompt=system_prompt,
            system_prompt_name=system_prompt_name,
            category="text",
            variables={
                "task_prompts": rule_desc,
                "query": query
            }
        )

        # 直接使用获取的提示词
        return final_system_prompt, final_system_prompt

    async def _call_llm(
        self,
        query: str,
        system_prompt: str,
        full_prompt: str,
        method: str,
        temperature: float,
        task_type: str,
        rule_name: str
    ) -> str:
        """
        调用LLM

        Args:
            query: 用户输入
            system_prompt: 系统提示词
            full_prompt: 完整提示词
            method: 调用方法
            temperature: 温度
            task_type: 任务类型
            rule_name: 规则名称

        Returns:
            LLM返回结果
        """
        # 获取默认配置
        config = await llm_config_service.get_default_config()
        if not config:
            raise ValueError("未找到LLM配置")

        # 构建工具schema（用于结构化输出方法）
        tools = [{
            "type": "function",
            "function": {
                "name": "process_rule",
                "description": f"处理{task_type}任务",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "result": {
                            "type": "string",
                            "description": "处理结果"
                        }
                    },
                    "required": ["result"]
                }
            }
        }]

        # 记录系统提示词日志
        logger.info(f"[RuleEngine] 规则: {rule_name}, 方法: {method}, 类型: {task_type}")
        logger.info(f"[RuleEngine] System Prompt: {system_prompt[:200]}...")
        logger.info(f"[RuleEngine] Full Prompt: {full_prompt[:500]}...")

        # 调用LLM代理服务
        result = await llm_proxy_service.process_request(
            query=query,
            tools=tools,
            system_prompt=system_prompt,
            method=method,
            config=config,
            temperature=temperature,
            full_system_prompt=full_prompt
        )

        if not result.get("success"):
            raise ValueError(f"LLM调用失败: {result.get('error')}")

        # 直接原封不动返回结果，让上层自己判断处理
        data = result.get("data", "")
        logger.info(f"[RuleEngine] LLM返回: {str(data)[:200]}...")
        return data

    def _build_name_from_fields(
        self,
        row: Dict[str, Any],
        fields: List[str],
        separator: str = " - "
    ) -> str:
        """
        从行数据中根据字段列表构建名称

        Args:
            row: 行数据
            fields: 字段列表
            separator: 分隔符

        Returns:
            构建的名称
        """
        name_parts = [str(row[field]) for field in fields if field in row and row[field]]
        return separator.join(name_parts) if name_parts else ""

    def _process_choice_result(
        self,
        llm_result: str,
        filtered_data: List[Dict[str, Any]],
        select_fields: List[str],
        name_fields: List[str],
        name_separator: str
    ) -> Dict[str, Any]:
        """
        处理选择题结果

        Args:
            llm_result: LLM返回结果
            filtered_data: 筛选后的数据
            select_fields: 选择字段
            name_fields: 名称字段
            name_separator: 名称分隔符

        Returns:
            处理后的结果
        """
        result = {"llm_res": llm_result}

        # 根据 name_fields 和 name_separator 构建选项名称，直接匹配行数据
        matched_row = None
        for row in filtered_data:
            option_name = self._build_name_from_fields(row, name_fields, name_separator)

            # 直接精确匹配（LLM 返回的应该与构建的选项名称完全一致）
            if option_name and option_name == llm_result:
                matched_row = row
                break

        # 提取字段
        if matched_row:
            result.update({field: matched_row[field] for field in select_fields if field in matched_row})

        return result

    def _process_text_result(
        self,
        llm_result: str,
        filtered_data: List[Dict[str, Any]],
        select_fields: List[str]
    ) -> Dict[str, Any]:
        """
        处理填空题结果

        Args:
            llm_result: LLM返回结果
            filtered_data: 筛选后的数据
            select_fields: 选择字段

        Returns:
            处理后的结果
        """
        result = {"llm_res": llm_result}

        # 提取字段（从匹配的规则行）
        if filtered_data:
            row = filtered_data[0]
            for field in select_fields:
                if field in row:
                    result[field] = row[field]

        return result

    async def _save_step_request(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str,
        query: str,
        method: str,
        params: List[Dict[str, Any]],
        step: int
    ) -> None:
        """保存步骤请求数据"""
        try:
            record = await FillDataRecord.filter(
                session_id=session_id,
                tenant_id=tenant_id,
                app_name=app_name
            ).first()

            request_data = {
                "query": query,
                "method": method,
                "params": params,
                "step": step
            }

            if record:
                existing_data = record.data or []
                if not isinstance(existing_data, list):
                    existing_data = [existing_data] if existing_data else []

                existing_data.append({
                    "step": step,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "request": request_data
                })

                record.data = existing_data
                await record.save()
            else:
                await FillDataRecord.create(
                    session_id=session_id,
                    tenant_id=tenant_id,
                    app_name=app_name,
                    data=[{
                        "step": step,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "request": request_data
                    }],
                    result=[],
                    status=AIFillDataStatus.PROCESSING.value
                )
        except Exception as e:
            logger.error(f"保存步骤请求失败: {e}")

    async def _save_step_result(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str,
        step: int,
        results: Dict[str, Any],
        elapsed_time: float,
        is_last: bool
    ) -> None:
        """保存步骤结果"""
        try:
            record = await FillDataRecord.filter(
                session_id=session_id,
                tenant_id=tenant_id,
                app_name=app_name
            ).first()

            if record:
                existing_result = record.result or []
                if not isinstance(existing_result, list):
                    existing_result = [existing_result] if existing_result else []

                existing_result.append({
                    "step": step,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "fields": results,
                    "timing": {"elapsed_time": elapsed_time}
                })

                record.result = existing_result

                if is_last:
                    record.status = AIFillDataStatus.COMPLETED.value
                    record.processed_at = time.strftime("%Y-%m-%d %H:%M:%S")

                await record.save()
        except Exception as e:
            logger.error(f"保存步骤结果失败: {e}")

    async def get_step_result(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取分步填单结果

        Args:
            session_id: 会话ID
            tenant_id: 租户ID
            app_name: 应用名称

        Returns:
            填单结果
        """
        record = await FillDataRecord.filter(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name
        ).first()

        if not record:
            return None

        # 合并所有步骤的结果
        merged_fields = {}
        if isinstance(record.result, list):
            for step_result in record.result:
                if isinstance(step_result, dict) and "fields" in step_result:
                    merged_fields.update(step_result["fields"])

        return {
            "session_id": session_id,
            "status": record.status,
            "total_steps": len(record.result) if isinstance(record.result, list) else 1,
            "data": record.data,
            "result": record.result,
            "merged_fields": merged_fields,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "processed_at": record.processed_at.isoformat() if record.processed_at else None
        }


rule_engine_service = RuleEngineService()
