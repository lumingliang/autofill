"""
AI填单服务层
处理 Dify 请求和异步任务处理
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi.exceptions import HTTPException

from app.controllers.autofill import fill_data_record_controller
from app.core.kafka import KafkaConfig, get_kafka_producer
from app.models.autofill import FillDataRecord
from app.models.enums import AIFillDataStatus
from app.settings.config import settings

logger = logging.getLogger(__name__)


class AIFillService:
    """AI填单服务"""

    # Kafka Topic 名称
    AI_FILL_TOPIC = "autofill.ai.requests"

    def __init__(self):
        self.dify_timeout = settings.DIFY_TIMEOUT
        self._kafka_config = None

    @property
    def kafka_config(self) -> KafkaConfig:
        """获取 Kafka 配置"""
        if self._kafka_config is None:
            self._kafka_config = KafkaConfig.from_toml()
        return self._kafka_config

    async def process_sync(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str,
        data: Dict[str, Any],
        dify_url: str,
        dify_api_key: str
    ) -> Dict[str, Any]:
        """
        同步处理 AI 填单请求

        Args:
            session_id: 会话ID
            tenant_id: 租户ID
            app_name: 应用名称
            data: 原始数据
            dify_url: Dify 服务地址
            dify_api_key: Dify API 密钥

        Returns:
            Dify 响应结果
        """
        # 1. 存储原始数据到数据库
        record = await fill_data_record_controller.save_original_data(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name,
            data=data
        )

        # 2. 更新状态为处理中
        record.status = AIFillDataStatus.PROCESSING.value
        await record.save()

        try:
            # 3. 调用 Dify 服务
            result = await self._call_dify(
                data=data,
                session_id=session_id,
                dify_url=dify_url,
                dify_api_key=dify_api_key
            )

            # 4. 更新记录状态为完成
            record.status = AIFillDataStatus.COMPLETED.value
            record.result = result
            record.processed_at = datetime.now()
            await record.save()

            return result

        except httpx.TimeoutException:
            record.status = AIFillDataStatus.TIMEOUT.value
            record.error_msg = "Dify service timeout"
            record.processed_at = datetime.now()
            await record.save()
            raise HTTPException(status_code=504, detail="Dify service timeout")

        except httpx.HTTPStatusError as e:
            record.status = AIFillDataStatus.FAILED.value
            record.error_msg = f"Dify service error: {e.response.status_code}"
            record.processed_at = datetime.now()
            await record.save()
            raise HTTPException(status_code=502, detail=f"Dify service error: {e.response.status_code}")

        except Exception as e:
            record.status = AIFillDataStatus.FAILED.value
            record.error_msg = f"Internal error: {str(e)}"
            record.processed_at = datetime.now()
            await record.save()
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def process_async(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str,
        data: Dict[str, Any],
        dify_url: str,
        dify_api_key: str
    ) -> Dict[str, Any]:
        """
        异步处理 AI 填单请求
        将任务发送到 Kafka，由消费者异步处理

        Args:
            session_id: 会话ID
            tenant_id: 租户ID
            app_name: 应用名称
            data: 原始数据
            dify_url: Dify 服务地址
            dify_api_key: Dify API 密钥

        Returns:
            包含任务状态的信息
        """
        # 1. 存储原始数据到数据库，状态为 pending
        record = await fill_data_record_controller.save_original_data(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name,
            data=data
        )

        # 更新状态为 pending
        record.status = AIFillDataStatus.PENDING.value
        await record.save()

        # 2. 构建 Kafka 消息
        message = {
            "session_id": session_id,
            "tenant_id": tenant_id,
            "app_name": app_name,
            "dify_config": {
                "url": dify_url,
                "api_key": dify_api_key,
            },
            "timestamp": datetime.now().isoformat(),
        }

        # 3. 发送到 Kafka
        producer = get_kafka_producer()
        success = producer.produce(
            topic=self.AI_FILL_TOPIC,
            value=message,
            key=session_id,
        )

        if success:
            # 更新状态为已入队
            record.status = AIFillDataStatus.QUEUED.value
            await record.save()

            return {
                "session_id": session_id,
                "status": AIFillDataStatus.QUEUED.value,
                "message": "Request has been queued for async processing",
            }
        else:
            # 发送失败，更新状态
            record.status = AIFillDataStatus.FAILED.value
            record.error_msg = "Failed to queue request to Kafka"
            await record.save()

            raise HTTPException(status_code=500, detail="Failed to queue request")

    async def _call_dify(
        self,
        data: Dict[str, Any],
        session_id: str,
        dify_url: str,
        dify_api_key: str
    ) -> Dict[str, Any]:
        """
        调用 Dify 服务

        Args:
            data: 输入数据
            session_id: 会话ID
            dify_url: Dify 服务地址
            dify_api_key: Dify API 密钥

        Returns:
            Dify 响应结果
        """
        headers = {
            "Authorization": f"Bearer {dify_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "inputs": {
                "data": data,
            },
            "response_mode": "blocking",
            "conversation_id": "",
            "user": session_id
        }

        async with httpx.AsyncClient(timeout=self.dify_timeout) as client:
            response = await client.post(
                dify_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def process_kafka_message(self, message: Dict[str, Any]):
        """
        处理 Kafka 消息（由消费者调用）

        Args:
            message: Kafka 消息内容
        """
        session_id = message.get("session_id")
        tenant_id = message.get("tenant_id")
        app_name = message.get("app_name")
        dify_config = message.get("dify_config", {})
        dify_url = dify_config.get("url")
        dify_api_key = dify_config.get("api_key")

        logger.info(f"[AI FILL SERVICE] Processing Kafka message for session: {session_id}")
        logger.info(f"[AI FILL SERVICE] tenant_id: {tenant_id}, app_name: {app_name}")
        logger.info(f"[AI FILL SERVICE] dify_url: {dify_url}")

        # 1. 查询记录
        logger.info(f"[AI FILL SERVICE] Querying database for session: {session_id}")
        record = await FillDataRecord.filter(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name
        ).first()

        if not record:
            logger.error(f"[AI FILL SERVICE] Record not found for session: {session_id}")
            return

        logger.info(f"[AI FILL SERVICE] Found record id: {record.id}, current status: {record.status}")

        # 2. 更新状态为处理中
        record.status = AIFillDataStatus.PROCESSING.value
        await record.save()
        logger.info(f"[AI FILL SERVICE] Updated status to PROCESSING for session: {session_id}")

        try:
            # 3. 从记录中获取原始数据
            record_data = record.data or {}
            original_data = record_data.get("original_data", {})

            logger.info(f"[AI FILL SERVICE] Original data keys: {list(original_data.keys()) if original_data else 'None'}")

            if not original_data:
                raise ValueError("No original data found in record")

            # 4. 调用 Dify
            logger.info(f"[AI FILL SERVICE] Calling Dify for session: {session_id}")
            result = await self._call_dify(
                data=original_data,
                session_id=session_id,
                dify_url=dify_url,
                dify_api_key=dify_api_key
            )
            logger.info(f"[AI FILL SERVICE] Dify call successful for session: {session_id}")

            # 5. 更新记录为完成状态
            record.status = AIFillDataStatus.COMPLETED.value
            record.result = result
            record.processed_at = datetime.now()
            await record.save()

            logger.info(f"[AI FILL SERVICE] Successfully processed session: {session_id}, status: COMPLETED")

        except httpx.TimeoutException:
            record.status = AIFillDataStatus.TIMEOUT.value
            record.error_msg = "Dify service timeout"
            record.processed_at = datetime.now()
            await record.save()
            logger.error(f"[AI FILL SERVICE] Timeout processing session: {session_id}")

        except Exception as e:
            record.status = AIFillDataStatus.FAILED.value
            record.error_msg = str(e)
            record.processed_at = datetime.now()
            await record.save()
            logger.error(f"[AI FILL SERVICE] Error processing session {session_id}: {e}", exc_info=True)

    async def get_result(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        查询异步处理结果

        Args:
            session_id: 会话ID
            tenant_id: 租户ID
            app_name: 应用名称

        Returns:
            处理结果或 None
        """
        record = await FillDataRecord.filter(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name
        ).first()

        if not record:
            return None

        return {
            "session_id": record.session_id,
            "status": record.status,
            "data": record.data,
            "result": record.result,
            "error_msg": record.error_msg,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "processed_at": record.processed_at.isoformat() if record.processed_at else None,
        }


# 全局服务实例
_ai_fill_service: Optional[AIFillService] = None


def get_ai_fill_service() -> AIFillService:
    """获取全局 AI 填单服务实例"""
    global _ai_fill_service
    if _ai_fill_service is None:
        _ai_fill_service = AIFillService()
    return _ai_fill_service