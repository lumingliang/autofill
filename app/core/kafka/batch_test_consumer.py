"""
批量测试 Kafka 消费者

处理批量测试任务的执行：
1. 接收 Kafka 消息
2. 从 SeekDB 获取待执行数据
3. 调用 Dify Agent 接口
4. 更新执行结果到 SeekDB
5. 更新任务统计信息
"""
import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.ctx import Ctx
from app.settings import settings
from app.log import logger
from app.models.batch_test import BatchTestTask
from app.core.seekdb_client import seekdb_client
from app.repositories.autofill import batch_test_repository, dify_agent_repository
from app.services.autofill.dify_agent_service import dify_agent_service


class BatchTestConsumer:
    """
    批量测试任务消费者

    处理流程：
    1. 接收消息，解析 collection_name、version_no 和 dify_agent_id
    2. 查询 SeekDB 获取所有 status=0 的数据
    3. 遍历每一行数据执行测试
    4. 更新执行结果到 SeekDB
    5. 更新任务统计信息
    """

    TOPIC = "batch-test-execute"

    async def process_message(self, message: Dict[str, Any]):
        """
        处理 Kafka 消息

        Args:
            message: Kafka 消息内容
        """
        task_id = message.get("task_id")
        version_no = message.get("version_no")
        collection_name = message.get("collection_name")
        dify_agent_id = message.get("dify_agent_id")
        total_rows = message.get("total_rows", 0)

        logger.info(f"[BatchTestConsumer] 开始处理任务: task_id={task_id}, version_no={version_no}")

        try:
            # 设置租户上下文（从任务中获取）
            task = await batch_test_repository.get_by_id(task_id)
            if not task:
                logger.error(f"[BatchTestConsumer] 任务不存在: task_id={task_id}")
                return

            # 检查任务状态
            if task.status != 1:  # 不是执行中状态
                logger.info(f"[BatchTestConsumer] 任务状态不是执行中，跳过: task_id={task_id}, status={task.status}")
                return

            # 获取 Agent 信息
            agent = await dify_agent_repository.get_by_id(dify_agent_id)
            if not agent:
                logger.error(f"[BatchTestConsumer] Agent 不存在: dify_agent_id={dify_agent_id}")
                await self._update_task_status(task_id, 3, 0, total_rows)  # 标记为失败
                return

            # 从 SeekDB 获取待执行数据
            collection = seekdb_client.get_or_create_collection(collection_name, embedding_function=None)

            # 查询所有 status=0 的数据
            results = collection.get(
                where={"status": 0},
                limit=100000  # 最大查询限制
            )

            if not results or not results.get("ids"):
                logger.info(f"[BatchTestConsumer] 没有待执行的数据: task_id={task_id}")
                await self._update_task_status(task_id, 2, 0, 0)  # 标记为完成
                return

            ids = results["ids"]
            metadatas = results["metadatas"]

            logger.info(f"[BatchTestConsumer] 待执行数据: {len(ids)} 条")

            # 执行测试
            success_count = 0
            fail_count = 0

            for i, (doc_id, metadata) in enumerate(zip(ids, metadatas)):
                try:
                    # 检查任务是否已被停止
                    task = await batch_test_repository.get_by_id(task_id)
                    if task.status == 4:  # 已停止
                        logger.info(f"[BatchTestConsumer] 任务已停止: task_id={task_id}")
                        break

                    # 执行单条测试
                    result = await self._execute_single_test(
                        collection=collection,
                        doc_id=doc_id,
                        metadata=metadata,
                        agent=agent
                    )

                    if result:
                        success_count += 1
                    else:
                        fail_count += 1

                    # 每10条更新一次任务统计
                    if (i + 1) % 10 == 0:
                        await self._update_task_stats(task_id, success_count, fail_count)

                except Exception as e:
                    logger.error(f"[BatchTestConsumer] 执行单条测试失败: doc_id={doc_id}, error={e}")
                    fail_count += 1

            # 最终更新任务状态
            final_status = 2 if task.status != 4 else 4  # 已完成或已停止
            await self._update_task_status(task_id, final_status, success_count, fail_count)

            logger.info(f"[BatchTestConsumer] 任务处理完成: task_id={task_id}, success={success_count}, fail={fail_count}")

        except Exception as e:
            logger.error(f"[BatchTestConsumer] 处理任务失败: task_id={task_id}, error={e}", exc_info=True)
            # 更新任务状态为失败
            await self._update_task_status(task_id, 3, 0, total_rows)

    async def _execute_single_test(
        self,
        collection: Any,
        doc_id: str,
        metadata: Dict[str, Any],
        agent: Any
    ) -> bool:
        """
        执行单条测试

        Args:
            collection: SeekDB 集合
            doc_id: 文档ID
            metadata: 文档元数据
            agent: Dify Agent 配置

        Returns:
            是否执行成功
        """
        query = metadata.get("query", "")
        if not query:
            logger.warning(f"[BatchTestConsumer] query 为空，跳过: doc_id={doc_id}")
            return False

        # 更新状态为执行中
        started_at = datetime.now().isoformat()
        collection.update(
            ids=[doc_id],
            metadatas=[{
                **metadata,
                "status": 1,  # 执行中
                "started_at": started_at
            }]
        )

        try:
            # 调用 Dify Agent
            start_time = time.time()

            # 使用 Dify Agent Service 转发请求
            result = await dify_agent_service.forward_to_dify(
                agent_id=agent.id,
                query=query,
                session_id=f"batch_test_{doc_id}",
                inputs={},
                conversation_id=None,
                response_mode="blocking"
            )

            execution_time_ms = int((time.time() - start_time) * 1000)
            completed_at = datetime.now().strftime(settings.DATETIME_FORMAT)

            # 展平 Dify 返回的 data 字段
            flattened_result = self._flatten_dify_result(result)

            # 更新 SeekDB
            update_metadata = {
                **metadata,
                "status": 2,  # 成功
                "started_at": started_at,
                "completed_at": completed_at,
                "execution_time_ms": execution_time_ms,
                "error_msg": "",
                **flattened_result  # 展平后的 Dify 返回字段
            }

            collection.update(
                ids=[doc_id],
                metadatas=[update_metadata]
            )

            logger.debug(f"[BatchTestConsumer] 单条测试成功: doc_id={doc_id}, time={execution_time_ms}ms")
            return True

        except Exception as e:
            completed_at = datetime.now().strftime(settings.DATETIME_FORMAT)
            execution_time_ms = int((time.time() - start_time) * 1000)

            # 更新 SeekDB 为失败状态
            collection.update(
                ids=[doc_id],
                metadatas=[{
                    **metadata,
                    "status": 3,  # 失败
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "execution_time_ms": execution_time_ms,
                    "error_msg": str(e)[:500]  # 限制错误信息长度
                }]
            )

            logger.error(f"[BatchTestConsumer] 单条测试失败: doc_id={doc_id}, error={e}")
            return False

    def _flatten_dify_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        展平 Dify 返回的结果

        将 data 字段展平到顶层
        例如：{"code": 200, "data": {"answer": "xxx"}} -> {"code": 200, "answer": "xxx"}

        Args:
            result: Dify 返回的原始结果

        Returns:
            展平后的结果
        """
        if not result:
            return {}

        flattened = dict(result)

        # 展平 data 字段
        if "data" in flattened and isinstance(flattened["data"], dict):
            data = flattened.pop("data")
            flattened.update(data)

        return flattened

    async def _update_task_stats(self, task_id: int, success_count: int, fail_count: int):
        """
        更新任务统计信息

        Args:
            task_id: 任务ID
            success_count: 成功数
            fail_count: 失败数
        """
        try:
            await batch_test_repository.update(task_id, {
                "success_count": success_count,
                "fail_count": fail_count
            })
        except Exception as e:
            logger.error(f"[BatchTestConsumer] 更新任务统计失败: task_id={task_id}, error={e}")

    async def _update_task_status(self, task_id: int, status: int, success_count: int, fail_count: int):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 状态
            success_count: 成功数
            fail_count: 失败数
        """
        try:
            await batch_test_repository.update(task_id, {
                "status": status,
                "success_count": success_count,
                "fail_count": fail_count
            })
        except Exception as e:
            logger.error(f"[BatchTestConsumer] 更新任务状态失败: task_id={task_id}, error={e}")


# 消费者实例
batch_test_consumer = BatchTestConsumer()


async def handle_batch_test_message(message: Dict[str, Any]):
    """
    Kafka 消息处理器

    Args:
        message: Kafka 消息
    """
    await batch_test_consumer.process_message(message)
