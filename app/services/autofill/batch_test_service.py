"""
批量测试任务服务层

严格遵循技术约束文档：
- 处理业务逻辑
- 调用 Repository 层进行数据操作
- 使用 @atomic() 装饰器控制事务
- 禁止直接查询 Model 层
- 禁止将 tenant_id 传递给 Repository 方法
"""
import io
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import HTTPException, UploadFile
from tortoise.transactions import atomic

from app.core.ctx import Ctx, CTX_USER_ID
from app.core.kafka.producer import get_kafka_producer
from app.log import logger
from app.models.batch_test import BatchTestTask
from app.models.dify_agent import DifyAgent
from app.core.seekdb_client import seekdb_client
from app.repositories.autofill import batch_test_repository, dify_agent_repository
from app.settings import settings
from app.utils.file_parser import decode_content, parse_csv_content


class BatchTestService:
    """
    批量测试任务业务服务

    职责：
    - 处理批量测试任务的业务逻辑
    - 调用 Repository 层进行数据操作
    - 管理事务控制
    - 与 SeekDB 和 Kafka 交互

    约束：
    - 写操作使用 @atomic() 装饰器
    - 不直接查询 Model 层
    - 不将 tenant_id 传递给 Repository 方法
    """

    # Kafka Topic 名称
    KAFKA_TOPIC = "batch-test-execute"

    async def preview_file(self, file: UploadFile) -> Dict[str, Any]:
        """
        预览文件内容

        Args:
            file: 上传的文件

        Returns:
            文件预览信息
        """
        content = await file.read()
        file_size = len(content)

        # 检查文件大小（最大 50MB）
        if file_size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小超过 50MB 限制")

        # 获取文件名
        file_name = file.filename or "unknown"

        # 解码文件内容
        decoded_content, encoding = decode_content(content)

        # 解析文件
        headers, data = self._parse_file(file_name, decoded_content)

        # 检查是否包含 query 列
        has_query_column = "query" in headers

        # 返回前5行样本数据
        sample_data = data[:5] if data else []

        return {
            "file_name": file_name,
            "file_size": file_size,
            "row_count": len(data),
            "headers": headers,
            "sample_data": sample_data,
            "has_query_column": has_query_column
        }

    def _parse_file(self, file_name: str, content: str) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        解析文件内容

        Args:
            file_name: 文件名
            content: 文件内容

        Returns:
            (表头列表, 数据行列表)
        """
        if file_name.lower().endswith('.csv'):
            return parse_csv_content(content)
        elif file_name.lower().endswith(('.xlsx', '.xls')):
            return self._parse_excel(content)
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式，请上传 CSV 或 Excel 文件")

    def _parse_excel(self, content: str) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        解析 Excel 内容

        Args:
            content: 文件字节内容（base64 编码）

        Returns:
            (表头列表, 数据行列表)
        """
        try:
            import base64
            # 将字符串内容转为字节
            content_bytes = content.encode('utf-8') if isinstance(content, str) else content
            df = pd.read_excel(io.BytesIO(content_bytes))
            headers = df.columns.tolist()
            data = df.to_dict('records')
            # 将数据转换为字符串格式
            data = [{k: str(v) if v is not None else "" for k, v in row.items()} for row in data]
            return headers, data
        except Exception as e:
            logger.error(f"解析 Excel 文件失败: {e}")
            raise HTTPException(status_code=400, detail=f"解析 Excel 文件失败: {str(e)}")

    @atomic()
    async def import_file(
        self,
        file: UploadFile,
        dify_agent_id: int,
        task_name: Optional[str] = None,
        remark: str = ""
    ) -> Dict[str, Any]:
        """
        导入文件创建批量测试任务

        Args:
            file: 上传的文件
            dify_agent_id: Dify Agent ID
            task_name: 任务名称（可选）
            remark: 备注

        Returns:
            任务信息
        """
        # 检查 Agent 是否存在
        agent = await dify_agent_repository.get_by_id(dify_agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Dify Agent 不存在")

        if not agent.is_active:
            raise HTTPException(status_code=400, detail="Dify Agent 已禁用")

        content = await file.read()
        file_size = len(content)
        file_name = file.filename or "unknown"

        # 检查文件大小
        if file_size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小超过 50MB 限制")

        # 解码并解析文件
        decoded_content, encoding = decode_content(content)
        headers, data = self._parse_file(file_name, decoded_content)

        # 检查是否包含 query 列
        if "query" not in headers:
            raise HTTPException(status_code=400, detail="文件必须包含 'query' 列")

        # 生成任务名称
        if not task_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
            task_name = f"{base_name}_{timestamp}"

        # 获取当前用户ID
        user_id = CTX_USER_ID.get() or 0

        # 创建任务记录
        task = await batch_test_repository.create({
            "task_name": task_name,
            "version_no": 1,
            "dify_agent_id": dify_agent_id,
            "file_name": file_name,
            "file_size": file_size,
            "row_count": len(data),
            "collection_name": "",  # 稍后更新
            "status": 0,  # 待执行
            "success_count": 0,
            "fail_count": 0,
            "remark": remark,
            "created_by": user_id
        })

        # 生成集合名称
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        collection_name = f"batch_test_{task.id}_v1_{timestamp}"

        # 更新任务记录
        await batch_test_repository.update(task.id, {"collection_name": collection_name})
        task.collection_name = collection_name

        # 写入 SeekDB
        await self._write_to_seekdb(collection_name, task.id, 1, dify_agent_id, data)

        # 发送 Kafka 消息触发执行
        await self._send_kafka_message(
            task_id=task.id,
            version_no=1,
            collection_name=collection_name,
            dify_agent_id=dify_agent_id,
            total_rows=len(data)
        )

        # 更新任务状态为执行中
        await batch_test_repository.update(task.id, {"status": 1})
        task.status = 1

        return {
            "task_id": task.id,
            "task_name": task.task_name,
            "version_no": task.version_no,
            "row_count": task.row_count,
            "status": task.status,
            "collection_name": collection_name
        }

    async def _write_to_seekdb(
        self,
        collection_name: str,
        task_id: int,
        version_no: int,
        dify_agent_id: int,
        data: List[Dict[str, str]]
    ):
        """
        将数据写入 SeekDB

        Args:
            collection_name: 集合名称
            task_id: 任务ID
            version_no: 版本号
            dify_agent_id: Dify Agent ID
            data: 数据列表
        """
        if not data:
            return

        ids = []
        metadatas = []

        for row_index, row in enumerate(data):
            doc_id = f"{task_id}_{row_index}"
            ids.append(doc_id)

            metadata = {
                "task_id": task_id,
                "row_index": row_index,
                "version_no": version_no,
                "query": row.get("query", ""),
                "dify_agent_id": dify_agent_id,
                "status": 0,  # 待执行
                "started_at": None,
                "completed_at": None,
                "execution_time_ms": 0,
                "error_msg": "",
                # 存储原始行数据
                **{f"col_{k}": v for k, v in row.items()}
            }
            metadatas.append(metadata)

        # 批量写入 SeekDB
        collection = seekdb_client.get_or_create_collection(collection_name, embedding_function=None)
        embeddings = [[0.0] * 384 for _ in range(len(ids))]
        collection.add(ids=ids, metadatas=metadatas, embeddings=embeddings)

        logger.info(f"写入 SeekDB 集合 {collection_name}: {len(data)} 条记录")

    async def _send_kafka_message(
        self,
        task_id: int,
        version_no: int,
        collection_name: str,
        dify_agent_id: int,
        total_rows: int
    ):
        """
        发送 Kafka 消息触发测试执行

        Args:
            task_id: 任务ID
            version_no: 版本号
            collection_name: 集合名称
            dify_agent_id: Dify Agent ID
            total_rows: 总行数
        """
        message = {
            "task_id": task_id,
            "version_no": version_no,
            "collection_name": collection_name,
            "dify_agent_id": dify_agent_id,
            "total_rows": total_rows,
            "created_at": datetime.now().strftime(settings.DATETIME_FORMAT)
        }

        producer = get_kafka_producer()
        producer.produce(
            topic=self.KAFKA_TOPIC,
            value=message,
            key=str(task_id)
        )

        logger.info(f"发送 Kafka 消息: task_id={task_id}, topic={self.KAFKA_TOPIC}")

    async def list_tasks(
        self,
        keyword: str = "",
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        获取任务列表

        Args:
            keyword: 关键词搜索
            page: 页码
            page_size: 每页数量

        Returns:
            (总数, 任务列表)
        """
        total, tasks = await batch_test_repository.list_tasks(
            keyword=keyword,
            page=page,
            page_size=page_size
        )

        # 获取 Agent 名称
        agent_ids = [task.dify_agent_id for task in tasks]
        agents = await dify_agent_repository.get_by_ids(agent_ids)
        agent_map = {agent.id: agent for agent in agents}

        data = []
        for task in tasks:
            agent = agent_map.get(task.dify_agent_id)
            task_dict = await task.to_dict()
            task_dict["dify_agent_name"] = agent.name if agent else ""
            data.append(task_dict)

        return total, data

    async def get_task_detail(self, task_id: int) -> Dict[str, Any]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            任务详情
        """
        task = await batch_test_repository.get_by_id_with_tenant(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 获取 Agent 信息
        agent = await dify_agent_repository.get_by_id(task.dify_agent_id)

        task_dict = await task.to_dict()
        task_dict["dify_agent_name"] = agent.name if agent else ""

        return task_dict

    @atomic()
    async def stop_task(self, task_id: int) -> Dict[str, Any]:
        """
        停止执行任务

        Args:
            task_id: 任务ID

        Returns:
            停止结果
        """
        task = await batch_test_repository.get_by_id_with_tenant(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        if task.status != 1:  # 不是执行中状态
            raise HTTPException(status_code=400, detail="只有执行中的任务可以停止")

        # 更新任务状态为已停止
        await batch_test_repository.update(task_id, {"status": 4})

        return {
            "task_id": task_id,
            "status": 4,
            "message": "任务已停止"
        }

    @atomic()
    async def delete_task(self, task_id: int):
        """
        删除任务

        Args:
            task_id: 任务ID
        """
        task = await batch_test_repository.get_by_id_with_tenant(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        if task.status == 1:  # 执行中
            raise HTTPException(status_code=400, detail="执行中的任务不能删除，请先停止")

        # 删除所有版本的 SeekDB 集合
        for version_no in range(1, task.version_no + 1):
            # 根据 task_id 和 version_no 查找集合名称
            collection_prefix = f"batch_test_{task_id}_v{version_no}_"
            try:
                seekdb_client.delete_collection_by_prefix(collection_prefix)
            except Exception as e:
                logger.warning(f"删除 SeekDB 集合失败: {collection_prefix}, error: {e}")

        # 删除任务记录
        await batch_test_repository.delete(task_id)

    @atomic()
    async def retry_task(self, task_id: int, user_id: int = 0) -> Dict[str, Any]:
        """
        重新执行任务（创建新版本，版本号递增）

        Args:
            task_id: 原任务ID
            user_id: 用户ID

        Returns:
            新版本任务信息
        """
        task = await batch_test_repository.get_by_id_with_tenant(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 检查 Agent
        agent = await dify_agent_repository.get_by_id(task.dify_agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Dify Agent 不存在")

        if not agent.is_active:
            raise HTTPException(status_code=400, detail="Dify Agent 已禁用")

        # 从旧版本集合中复制基础数据
        old_data = await self._get_seekdb_data(task.collection_name)

        if not old_data:
            raise HTTPException(status_code=400, detail="原任务没有可执行的数据")

        # 创建新版本数据（只保留基础字段）
        new_data = []
        for item in old_data:
            new_data.append({
                "query": item.get("query", ""),
                # 保留原始列数据
                **{k: v for k, v in item.items() if k.startswith("col_")}
            })

        # 新版本号 = 当前版本号 + 1
        new_version_no = task.version_no + 1

        # 生成新任务名称：原任务名_v2, _v3, _v4...
        # 先去掉可能存在的旧版本后缀
        base_task_name = task.task_name
        if '_v' in base_task_name:
            # 找到最后一个 _v 并去掉后面的内容
            base_task_name = base_task_name.rsplit('_v', 1)[0]
        new_task_name = f"{base_task_name}_v{new_version_no}"

        # 生成新集合名称
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_collection_name = f"batch_test_{task_id}_v{new_version_no}_{timestamp}"

        # 创建新任务记录
        new_task = await batch_test_repository.create({
            "tenant_id": task.tenant_id,
            "task_name": new_task_name,
            "version_no": new_version_no,
            "dify_agent_id": task.dify_agent_id,
            "file_name": task.file_name,
            "file_size": task.file_size,
            "row_count": len(new_data),
            "collection_name": new_collection_name,
            "status": 1,  # 执行中
            "success_count": 0,
            "fail_count": 0,
            "remark": f"从任务 {task.task_name}(ID:{task_id}) 重试创建",
            "created_by": user_id
        })

        # 写入新集合
        await self._write_to_seekdb(
            collection_name=new_collection_name,
            task_id=new_task.id,
            version_no=new_version_no,
            dify_agent_id=task.dify_agent_id,
            data=new_data
        )

        # 发送 Kafka 消息
        await self._send_kafka_message(
            task_id=new_task.id,
            version_no=new_version_no,
            collection_name=new_collection_name,
            dify_agent_id=task.dify_agent_id,
            total_rows=len(new_data)
        )

        return {
            "task_id": new_task.id,
            "task_name": new_task_name,
            "version_no": new_version_no,
            "collection_name": new_collection_name,
            "status": 1
        }

    async def _get_seekdb_data(self, collection_name: str) -> List[Dict[str, Any]]:
        """
        从 SeekDB 获取数据

        Args:
            collection_name: 集合名称

        Returns:
            数据列表
        """
        try:
            collection = seekdb_client.get_or_create_collection(collection_name, embedding_function=None)
            results = collection.get()

            data = []
            for i, metadata in enumerate(results.get("metadatas", [])):
                data.append(metadata)

            return data
        except Exception as e:
            logger.error(f"从 SeekDB 获取数据失败: {collection_name}, error: {e}")
            return []

    async def get_results(
        self,
        task_id: int,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取测试结果列表

        Args:
            task_id: 任务ID
            status: 状态筛选
            page: 页码
            page_size: 每页数量

        Returns:
            结果列表
        """
        task = await batch_test_repository.get_by_id_with_tenant(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 从 SeekDB 查询数据
        try:
            collection = seekdb_client.get_or_create_collection(
                task.collection_name,
                embedding_function=None
            )

            # 获取所有数据
            results = collection.get()

            items = []
            for i, metadata in enumerate(results.get("metadatas", [])):
                # 如果指定了状态筛选
                if status is not None and metadata.get("status") != status:
                    continue

                item = {
                    "id": results.get("ids", [])[i] if i < len(results.get("ids", [])) else f"{task_id}_{i}",
                    "row_index": metadata.get("row_index", i),
                    "query": metadata.get("query", ""),
                    "status": metadata.get("status", 0),
                    "execution_time_ms": metadata.get("execution_time_ms", 0),
                    "started_at": metadata.get("started_at"),
                    "completed_at": metadata.get("completed_at"),
                    "error_msg": metadata.get("error_msg", ""),
                }

                # 添加 Dify 返回的字段（排除内部字段）
                for key, value in metadata.items():
                    if key not in ["task_id", "row_index", "version_no", "dify_agent_id", "status",
                                   "started_at", "completed_at", "execution_time_ms", "error_msg"] \
                       and not key.startswith("col_"):
                        item[key] = value

                items.append(item)

            # 分页
            total = len(items)
            start = (page - 1) * page_size
            end = start + page_size
            items = items[start:end]

            return {
                "total": total,
                "items": items
            }

        except Exception as e:
            logger.error(f"查询 SeekDB 失败: {task.collection_name}, error: {e}")
            raise HTTPException(status_code=500, detail=f"查询结果失败: {str(e)}")

    async def export_results(self, task_id: int) -> io.BytesIO:
        """
        导出测试结果

        Args:
            task_id: 任务ID

        Returns:
            CSV 文件字节流
        """
        task = await batch_test_repository.get_by_id_with_tenant(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 从 SeekDB 获取所有数据
        try:
            collection = seekdb_client.get_or_create_collection(
                task.collection_name,
                embedding_function=None
            )
            results = collection.get()

            if not results.get("metadatas"):
                raise HTTPException(status_code=404, detail="没有可导出的数据")

            # 构建 CSV 数据
            all_data = []
            for metadata in results.get("metadatas", []):
                row = {
                    "query": metadata.get("query", ""),
                    "status": metadata.get("status", 0),
                    "execution_time_ms": metadata.get("execution_time_ms", 0),
                    "error_msg": metadata.get("error_msg", ""),
                    "started_at": metadata.get("started_at", ""),
                    "completed_at": metadata.get("completed_at", ""),
                }

                # 添加原始列数据
                for key, value in metadata.items():
                    if key.startswith("col_"):
                        col_name = key[4:]  # 去掉 col_ 前缀
                        row[col_name] = value

                # 添加 Dify 返回的字段
                for key, value in metadata.items():
                    if key not in ["task_id", "row_index", "version_no", "dify_agent_id",
                                   "status", "started_at", "completed_at", "execution_time_ms",
                                   "error_msg", "query"] and not key.startswith("col_"):
                        # 处理时间戳字段，转换为可读格式
                        if key in ["created_at"] and isinstance(value, (int, float)):
                            try:
                                value = datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")
                            except (ValueError, OSError):
                                pass  # 转换失败保持原值
                        row[key] = value

                all_data.append(row)

            # 生成 CSV
            if all_data:
                df = pd.DataFrame(all_data)
                output = io.BytesIO()
                df.to_csv(output, index=False, encoding='utf-8-sig')
                output.seek(0)
                return output
            else:
                raise HTTPException(status_code=404, detail="没有可导出的数据")

        except Exception as e:
            logger.error(f"导出结果失败: {task.collection_name}, error: {e}")
            raise HTTPException(status_code=500, detail=f"导出结果失败: {str(e)}")


# 服务实例
batch_test_service = BatchTestService()
