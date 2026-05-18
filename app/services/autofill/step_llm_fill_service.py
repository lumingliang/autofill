"""
分步LLM填单服务
处理分步填单流程，支持session管理和多轮数据存储
"""
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.redis import redis_client
from app.log import logger
from app.models.autofill import FillDataRecord
from app.models.enums import AIFillDataStatus


class StepLLMFillService:
    """分步LLM填单服务"""

    REDIS_KEY_PREFIX = "step_llm_fill"
    REDIS_EXPIRE_SECONDS = 3600  # 1小时过期

    def __init__(self):
        pass

    def _get_redis_key(self, session_id: str) -> str:
        """生成Redis key"""
        return f"{self.REDIS_KEY_PREFIX}:{session_id}"

    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """
        获取session信息

        Args:
            session_id: 会话ID

        Returns:
            session信息，包含调用次数、状态等
        """
        try:
            redis = redis_client.client
            key = self._get_redis_key(session_id)
            data = await redis.get(key)

            if data:
                return json.loads(data)
            else:
                # 新session，初始化
                return {
                    "session_id": session_id,
                    "call_count": 0,
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "steps": []
                }
        except Exception as e:
            logger.error(f"Failed to get session info for {session_id}: {e}")
            # 返回默认值
            return {
                "session_id": session_id,
                "call_count": 0,
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "steps": []
            }

    async def update_session_info(
        self,
        session_id: str,
        step_data: Dict[str, Any],
        is_last: bool = False
    ) -> Dict[str, Any]:
        """
        更新session信息

        Args:
            session_id: 会话ID
            step_data: 当前步骤的数据
            is_last: 是否为最后一步

        Returns:
            更新后的session信息
        """
        try:
            redis = redis_client.client
            key = self._get_redis_key(session_id)

            # 获取当前session信息
            session_info = await self.get_session_info(session_id)

            # 更新调用次数
            session_info["call_count"] += 1
            session_info["updated_at"] = datetime.now().isoformat()

            # 添加步骤数据
            step_record = {
                "step": session_info["call_count"],
                "timestamp": datetime.now().isoformat(),
                "data": step_data
            }
            session_info["steps"].append(step_record)

            # 如果是最后一步，更新状态
            if is_last:
                session_info["status"] = "completed"

            # 保存到Redis
            await redis.setex(
                key,
                self.REDIS_EXPIRE_SECONDS,
                json.dumps(session_info, ensure_ascii=False)
            )

            return session_info

        except Exception as e:
            logger.error(f"Failed to update session info for {session_id}: {e}")
            raise

    async def save_step_result(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str,
        page_name: str,
        step_result: Dict[str, Any],
        is_last: bool = False
    ) -> FillDataRecord:
        """
        保存步骤结果到数据库

        Args:
            session_id: 会话ID
            tenant_id: 租户ID
            app_name: 应用名称
            page_name: 页面名称
            step_result: 步骤结果
            is_last: 是否为最后一步

        Returns:
            FillDataRecord对象
        """
        try:
            # 查询是否已存在记录（请求数据应该已经存在）
            record = await FillDataRecord.filter(
                session_id=session_id,
                tenant_id=tenant_id,
                app_name=app_name
            ).first()

            if record:
                # 更新现有记录 - 只添加结果数据（请求数据已经提前保存）
                existing_result = record.result or []

                # 确保是列表格式
                if not isinstance(existing_result, list):
                    existing_result = [existing_result] if existing_result else []

                # 添加新步骤的结果（保存原始格式 raw_result）
                raw_result = step_result.get("raw_result", {})
                timing = step_result.get("timing", {})
                existing_result.append({
                    "step": len(existing_result) + 1,
                    "fields": raw_result,  # 保存包含 type 和 value 的原始格式
                    "timing": timing,
                    "timestamp": datetime.now().isoformat()
                })

                record.result = existing_result

                # 如果是最后一步，更新状态为完成
                if is_last:
                    record.status = AIFillDataStatus.COMPLETED.value
                    record.processed_at = datetime.now()

                await record.save()

            else:
                # 异常情况：请求数据应该已经保存，这里作为后备处理
                logger.warning(f"Record not found for session {session_id}, creating new record with both request and result")
                record = await FillDataRecord.create(
                    session_id=session_id,
                    tenant_id=tenant_id,
                    app_name=app_name,
                    data=[{
                        "step": 1,
                        "page_name": page_name,
                        "timestamp": datetime.now().isoformat(),
                        "request": step_result.get("request", {})
                    }],
                    result=[{
                        "step": 1,
                        "fields": step_result.get("raw_result", {}),  # 保存包含 type 和 value 的原始格式
                        "timing": step_result.get("timing", {}),
                        "timestamp": datetime.now().isoformat()
                    }],
                    status=AIFillDataStatus.PROCESSING.value if not is_last else AIFillDataStatus.COMPLETED.value,
                    processed_at=datetime.now() if is_last else None
                )

            return record

        except Exception as e:
            logger.error(f"Failed to save step result for {session_id}: {e}")
            raise

    async def save_step_request(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str,
        page_name: str,
        request_data: Dict[str, Any]
    ) -> FillDataRecord:
        """
        立即保存步骤请求数据（在LLM调用之前）

        Args:
            session_id: 会话ID
            tenant_id: 租户ID
            app_name: 应用名称
            page_name: 页面名称
            request_data: 请求数据

        Returns:
            FillDataRecord对象
        """
        try:
            # 记录query长度用于调试
            query = request_data.get("query", "")
            logger.info(f"save_step_request: session_id={session_id}, query_length={len(query)}")

            # 查询是否已存在记录
            record = await FillDataRecord.filter(
                session_id=session_id,
                tenant_id=tenant_id,
                app_name=app_name
            ).first()

            if record:
                # 更新现有记录
                existing_data = record.data or []
                if not isinstance(existing_data, list):
                    existing_data = [existing_data] if existing_data else []

                # 添加新步骤的请求数据
                existing_data.append({
                    "step": len(existing_data) + 1,
                    "page_name": page_name,
                    "timestamp": datetime.now().isoformat(),
                    "request": request_data
                })

                record.data = existing_data
                await record.save()
            else:
                # 创建新记录（只包含请求数据）
                record = await FillDataRecord.create(
                    session_id=session_id,
                    tenant_id=tenant_id,
                    app_name=app_name,
                    data=[{
                        "step": 1,
                        "page_name": page_name,
                        "timestamp": datetime.now().isoformat(),
                        "request": request_data
                    }],
                    result=[],  # 结果数据稍后更新
                    status=AIFillDataStatus.PROCESSING.value
                )

            return record

        except Exception as e:
            logger.error(f"Failed to save step request for {session_id}: {e}")
            raise

    async def save_step_error(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str,
        error_msg: str
    ) -> None:
        """
        保存步骤错误信息

        Args:
            session_id: 会话ID
            tenant_id: 租户ID
            app_name: 应用名称
            error_msg: 错误信息
        """
        try:
            record = await FillDataRecord.filter(
                session_id=session_id,
                tenant_id=tenant_id,
                app_name=app_name
            ).first()

            if record:
                record.status = AIFillDataStatus.FAILED.value
                record.error_msg = error_msg
                await record.save()

        except Exception as e:
            logger.error(f"Failed to save step error for {session_id}: {e}")

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
            填单结果，包含所有步骤的数据
        """
        try:
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

        except Exception as e:
            logger.error(f"Failed to get step result for {session_id}: {e}")
            raise

    async def prepare_llm_fill_context(
        self,
        tenant_id: int,
        app_name: str,
        page_name: str,
        group_fields: Dict[str, List[str]],
        query: str,
        additional_data: Dict[str, Any] = None,
        use_additional_data: bool = False,
        include_reason: bool = False,
        system_prompt: str = None
    ) -> Dict[str, Any]:
        """
        准备 LLM 填单的上下文数据（抽取自 handler 层）

        Args:
            tenant_id: 租户ID
            app_name: 应用名称
            page_name: 页面名称
            group_fields: 字段组与字段映射
            query: 查询内容
            additional_data: 附加数据
            use_additional_data: 是否使用附加数据
            include_reason: 是否包含理由
            system_prompt: 自定义系统提示词

        Returns:
            包含 result_data, config, full_system_prompt, field_specs,
            unified_function_schema, query 的字典
        """
        from app.services.llm.llm_config_service import llm_config_service
        from app.services.autofill.field_group_query_service import field_group_query_service
        from app.services.autofill.prompt_service import build_fields_instructions
        from app.services.autofill.constants import DEFAULT_PROMPT_TEMPLATE_BASE

        try:
            result_data = await field_group_query_service.fetch_field_groups(
                tenant_id=tenant_id,
                app_name=app_name,
                page_name=page_name,
                group_fields=group_fields,
                additional_data=additional_data or {},
                use_additional_data=use_additional_data,
                include_reason=include_reason
            )
        except ValueError as e:
            logger.warning(f"fetch_field_groups validation error: {e}")
            raise ValueError(f"获取字段配置失败: {str(e)}")
        except Exception as e:
            logger.error(f"fetch_field_groups error: {type(e).__name__}: {e}")
            raise ValueError(f"获取字段配置失败: {str(e)}")

        unified_function_schema = result_data.get("unified_function_schema")
        if not unified_function_schema:
            raise ValueError("未找到有效的字段配置，请检查字段组是否存在且包含有效字段")

        if not query:
            raise ValueError("query is required")

        # 通过 service 层获取默认配置
        config = await llm_config_service.get_default_config()
        if not config:
            raise ValueError("No LLM configuration found")

        field_specs = result_data.get("all_field_specs", [])

        base_prompt = system_prompt or result_data.get("combined_prompt") or DEFAULT_PROMPT_TEMPLATE_BASE

        # 构建字段指令
        if field_specs:
            fields_instructions = build_fields_instructions(field_specs)
        else:
            fields_instructions = ""

        # 拼接 field_instructions 到 system_prompt，生成 full_system_prompt
        if "{fields_instructions}" in base_prompt:
            full_system_prompt = base_prompt.replace("{fields_instructions}", fields_instructions)
        else:
            if fields_instructions:
                full_system_prompt = f"{base_prompt}\n\n{fields_instructions}"
            else:
                full_system_prompt = base_prompt

        return {
            "result_data": result_data,
            "config": config,
            "full_system_prompt": full_system_prompt,
            "field_specs": field_specs,
            "unified_function_schema": unified_function_schema,
            "query": query
        }

    async def execute_llm_fill_step(
        self,
        tenant_id: int,
        app_name: str,
        page_name: str,
        session_id: str,
        group_fields: Dict[str, List[str]],
        query: str,
        is_last: bool = True,
        method: str = None,
        system_prompt: str = None,
        additional_data: Dict[str, Any] = None,
        use_additional_data: bool = False,
        include_reason: bool = False,
        memory_rounds: int = 0
    ) -> Dict[str, Any]:
        """
        执行完整的 LLM 填单步骤（抽取自 handler 层）

        Args:
            tenant_id: 租户ID
            app_name: 应用名称
            page_name: 页面名称
            session_id: 会话ID
            group_fields: 字段组与字段映射
            query: 查询内容
            is_last: 是否为最后一步
            method: LLM调用方法
            system_prompt: 系统提示词
            additional_data: 附加数据
            use_additional_data: 是否使用附加数据
            include_reason: 是否包含理由
            memory_rounds: 记忆轮数

        Returns:
            包含 result, enriched_result, output_templates, elapsed_time 的字典
        """
        from app.services.llm.llm_proxy_service import llm_proxy_service

        start_time = time.time()

        # 1. 准备上下文
        context = await self.prepare_llm_fill_context(
            tenant_id=tenant_id,
            app_name=app_name,
            page_name=page_name,
            group_fields=group_fields,
            query=query,
            additional_data=additional_data,
            use_additional_data=use_additional_data,
            include_reason=include_reason,
            system_prompt=system_prompt
        )

        # 2. 保存请求
        await self.save_step_request(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name,
            page_name=page_name,
            request_data={
                "page_name": page_name,
                "group_fields": group_fields,
                "query": query,
                "method": method
            }
        )

        # 3. 执行 LLM 调用
        # plain 方法不需要 tools
        tools = [context["unified_function_schema"]] if method != "plain" and context["unified_function_schema"] else None

        llm_result = await llm_proxy_service.process_request(
            query=query,
            tools=tools,
            system_prompt=context["full_system_prompt"],
            tool_choice="auto",
            config=context["config"],
            method=method,
            memory_rounds=memory_rounds,
            session_id=session_id,
            full_system_prompt=context["full_system_prompt"]
        )

        # 4. 处理结果
        enriched_result = {}
        output_templates = {}

        if method == "plain":
            enriched_result = llm_result
        else:
            # 从 llm_result['data'] 获取提取的数据
            extracted_data = llm_result.get("data", {}) or {}

            if use_additional_data and additional_data:
                extracted_data = {**extracted_data, **additional_data}

            # 使用 llm_handlers 中的辅助函数处理 enriched
            from app.api.public.handlers.llm_handlers import _enrich_extracted_data, _process_output_templates

            enriched_result = _enrich_extracted_data(extracted_data, context["field_specs"])
            field_groups = context["result_data"].get("field_groups", [])
            output_templates = _process_output_templates(field_groups, enriched_result)

        # 5. 保存结果
        from app.api.public.handlers.llm_handlers import _extract_field_value

        elapsed_time = time.time() - start_time
        llm_meta = llm_result.get("_meta", {})

        step_result = {
            "request": {
                "page_name": page_name,
                "group_fields": group_fields,
                "query": query,
                "method": method
            },
            "response": {
                "fields": list(enriched_result.keys()) if enriched_result else [],
                "fields_count": len(enriched_result) if enriched_result else 0
            },
            "raw_result": enriched_result if method != "plain" else llm_result,
            "extracted_fields": {k: _extract_field_value(v) for k, v in enriched_result.items()},
            "timing": {
                "elapsed_time": elapsed_time,
                "llm_elapsed_time": llm_meta.get("elapsed_time"),
                "total_tokens": llm_meta.get("total_tokens"),
                "prompt_tokens": llm_meta.get("prompt_tokens"),
                "completion_tokens": llm_meta.get("completion_tokens")
            }
        }

        await self.save_step_result(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name,
            page_name=page_name,
            step_result=step_result,
            is_last=is_last
        )

        await self.update_session_info(
            session_id=session_id,
            step_data={"method": method, "fields_count": len(enriched_result) if enriched_result else 0, "elapsed_time": elapsed_time},
            is_last=is_last
        )

        return {
            "result": enriched_result,
            "output_templates": output_templates,
            "elapsed_time": elapsed_time,
            "session_id": session_id,
            "step": (await self.get_session_info(session_id))["call_count"],
            "is_last": is_last,
            "status": "completed" if is_last else "processing",
            "page_name": page_name,
            "merged_fields": enriched_result if is_last else {}
        }

    async def execute_llm_fill(
        self,
        tenant_id: int,
        app_name: str,
        page_name: str,
        group_fields: Dict[str, List[str]],
        query: str,
        method: str = None,
        system_prompt: str = None,
        additional_data: Dict[str, Any] = None,
        use_additional_data: bool = False,
        include_reason: bool = False,
        memory_rounds: int = 0
    ) -> Dict[str, Any]:
        """
        执行非分步的 LLM 填单（直接填单，不保存步骤）

        Args:
            tenant_id: 租户ID
            app_name: 应用名称
            page_name: 页面名称
            group_fields: 字段组与字段映射
            query: 查询内容
            method: LLM调用方法
            system_prompt: 系统提示词
            additional_data: 附加数据
            use_additional_data: 是否使用附加数据
            include_reason: 是否包含理由
            memory_rounds: 记忆轮数

        Returns:
            包含 result, enriched_result, output_templates, elapsed_time, full_system_prompt, config 的字典
        """
        from app.services.llm.llm_proxy_service import llm_proxy_service

        start_time = time.time()

        # 1. 准备上下文
        context = await self.prepare_llm_fill_context(
            tenant_id=tenant_id,
            app_name=app_name,
            page_name=page_name,
            group_fields=group_fields,
            query=query,
            additional_data=additional_data,
            use_additional_data=use_additional_data,
            include_reason=include_reason,
            system_prompt=system_prompt
        )

        # 2. 执行 LLM 调用
        tools = [context["unified_function_schema"]] if method != "plain" and context["unified_function_schema"] else None

        llm_result = await llm_proxy_service.process_request(
            query=query,
            tools=tools,
            system_prompt=context["full_system_prompt"],
            tool_choice="auto",
            config=context["config"],
            method=method,
            memory_rounds=memory_rounds,
            session_id=None,
            full_system_prompt=context["full_system_prompt"]
        )

        # 3. 处理结果
        enriched_result = {}
        output_templates = {}

        if method == "plain":
            enriched_result = llm_result
        else:
            extracted_data = llm_result.get("data", {}) or {}

            if use_additional_data and additional_data:
                extracted_data = {**extracted_data, **additional_data}

            from app.api.public.handlers.llm_handlers import _enrich_extracted_data, _process_output_templates

            enriched_result = _enrich_extracted_data(extracted_data, context["field_specs"])
            field_groups = context["result_data"].get("field_groups", [])
            output_templates = _process_output_templates(field_groups, enriched_result)

        elapsed_time = time.time() - start_time

        return {
            "result": enriched_result,
            "output_templates": output_templates,
            "elapsed_time": elapsed_time,
            "full_system_prompt": context["full_system_prompt"],
            "unified_function_schema": context["unified_function_schema"],
            "method": method,
            "page_name": page_name,
            "_meta": llm_result.get("_meta", {})
        }


# 全局服务实例
step_llm_fill_service = StepLLMFillService()
