"""
分步LLM填单服务
处理分步填单流程，支持session管理和多轮数据存储
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.controllers.autofill import fill_data_record_controller
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


# 全局服务实例
step_llm_fill_service = StepLLMFillService()
