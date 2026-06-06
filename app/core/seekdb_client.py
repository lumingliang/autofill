"""
seekdb 客户端 - 基础设施层

设计原则：
1. 封装 pyseekdb 客户端，提供统一接口
2. 支持嵌入式模式和远程服务器模式
3. JSON 结构存储，支持按字段查询
4. 不使用向量搜索

注意：这是基础设施层，可以被 Repository 层直接依赖
"""

import csv
import io
from typing import Any, Dict, List, Optional, Tuple

import pyseekdb

from app.log import logger
from app.settings.config import settings

# 查询结果数量限制（pyseekdb 默认只返回 100 条）
DEFAULT_QUERY_LIMIT = 100000


class SeekDBClient:
    """seekdb 客户端"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化 seekdb 客户端

        Args:
            db_path: seekdb 数据库文件路径（仅在嵌入式模式下使用），默认从配置读取
        """
        self._mode = settings.SEEKDB_MODE
        self.db_path = db_path or settings.SEEKDB_PATH
        self._admin_client = None
        self._client = None
        self._database = settings.SEEKDB_DATABASE if self._mode == "remote" else settings.SEEKDB_DEFAULT_DATABASE

        # 远程模式配置
        self._host = settings.SEEKDB_HOST
        self._port = settings.SEEKDB_PORT
        self._user = settings.SEEKDB_USER
        self._password = settings.SEEKDB_PASSWORD

        # 确保数据库存在
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        if self._mode == "remote":
            # 远程模式下，数据库应该在服务器端已创建
            # 这里只做连接测试
            try:
                client = self._get_client()
                logger.info(f"seekdb 远程连接成功: {self._host}:{self._port}/{self._database}")
            except Exception as e:
                logger.error(f"seekdb 远程连接失败: {e}")
                raise
        else:
            # 嵌入式模式：确保本地数据库存在
            try:
                admin = self._get_admin_client()
                # 检查数据库是否存在，不存在则创建
                try:
                    admin.create_database(self._database)
                    logger.info(f"创建 seekdb 数据库: {self._database}")
                except Exception:
                    # 数据库已存在
                    pass
            except Exception as e:
                logger.error(f"初始化 seekdb 数据库失败: {e}")
                raise

    def _get_admin_client(self) -> pyseekdb.AdminClient:
        """获取 AdminClient"""
        if not self._admin_client:
            if self._mode == "remote":
                self._admin_client = pyseekdb.AdminClient(
                    host=self._host,
                    port=self._port,
                    user=self._user,
                    password=self._password
                )
            else:
                self._admin_client = pyseekdb.AdminClient(path=self.db_path)
        return self._admin_client

    def _get_client(self) -> pyseekdb.Client:
        """获取 Client"""
        if not self._client:
            if self._mode == "remote":
                self._client = pyseekdb.Client(
                    host=self._host,
                    port=self._port,
                    database=self._database,
                    user=self._user,
                    password=self._password
                )
            else:
                self._client = pyseekdb.Client(
                    path=self.db_path,
                    database=self._database
                )
        return self._client

    def get_or_create_collection(self, name: str, embedding_function=None):
        """
        获取或创建集合

        Args:
            name: 集合名称
            embedding_function: 嵌入函数，默认None表示不使用嵌入（提高性能）

        Returns:
            Collection 对象
        """
        client = self._get_client()
        return client.get_or_create_collection(name, embedding_function=embedding_function)

    def delete_collection(self, name: str) -> bool:
        """
        删除集合

        Args:
            name: 集合名称

        Returns:
            是否删除成功
        """
        try:
            client = self._get_client()
            client.delete_collection(name)
            logger.info(f"删除 seekdb 集合: {name}")
            return True
        except Exception as e:
            logger.error(f"删除 seekdb 集合失败: {name}, error: {e}")
            return False

    async def save_rule_data(
        self,
        collection_name: str,
        headers: List[str],
        data: List[Dict[str, str]],
        rule_id: int,
        version_no: int,
        tenant_id: int,
        app_name: str,
        rule_code: str
    ) -> int:
        """
        保存规则数据到 seekdb

        Args:
            collection_name: 集合名称
            headers: 表头列表
            data: CSV 数据（字典列表）
            rule_id: 规则ID
            version_no: 版本号
            tenant_id: 租户ID
            app_name: 应用名称
            rule_code: 规则编码

        Returns:
            保存的文档数量
        """
        if not data:
            return 0

        # 构建 seekdb 文档列表
        ids = []
        metadatas = []

        for row_index, row in enumerate(data):
            doc_id = f"{rule_id}_v{version_no}_{row_index}"
            ids.append(doc_id)

            # 构建 JSON 结构数据
            row_data = {header: row.get(header, "") for header in headers}

            metadata = {
                "rule_id": rule_id,
                "version_no": version_no,
                "row_index": row_index,
                "tenant_id": tenant_id,
                "app_name": app_name,
                "rule_code": rule_code,
                "data": row_data,  # JSON 结构存储
                "headers": headers
            }
            metadatas.append(metadata)

        # 批量写入 seekdb（不使用向量嵌入）
        collection = self.get_or_create_collection(collection_name, embedding_function=None)
        # 数据存储在 metadatas 中，不使用嵌入向量以节省空间
        # 使用标准384维零向量作为占位符
        embeddings = [[0.0] * 384 for _ in range(len(ids))]
        collection.add(ids=ids, metadatas=metadatas, embeddings=embeddings)

        logger.info(
            f"保存规则数据到 seekdb",
            collection_name=collection_name,
            doc_count=len(ids),
            rule_id=rule_id,
            version_no=version_no
        )

        return len(ids)

    async def get_rule_data(
        self,
        collection_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取规则数据

        Args:
            collection_name: 集合名称

        Returns:
            {headers, data} 或 None
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            results = collection.get(limit=DEFAULT_QUERY_LIMIT)

            if not results or not results.get("metadatas"):
                return None

            # 提取表头和数据
            headers = []
            data = []

            for metadata in results["metadatas"]:
                if not headers and metadata.get("headers"):
                    headers = metadata["headers"]

                row_data = metadata.get("data", {})
                # 转换为列表格式，保持顺序
                row_list = [row_data.get(header, "") for header in headers]
                data.append(row_list)

            return {
                "headers": headers,
                "data": data
            }

        except Exception as e:
            logger.error(f"获取规则数据失败: {collection_name}, error: {e}")
            return None

    async def query_by_field(
        self,
        collection_name: str,
        field: str,
        value: Any
    ) -> List[Dict[str, str]]:
        """
        按字段查询

        Args:
            collection_name: 集合名称
            field: 字段名
            value: 字段值

        Returns:
            匹配的数据列表
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            results = collection.get(where={f"data.{field}": value}, limit=DEFAULT_QUERY_LIMIT)

            data = []
            for metadata in results.get("metadatas", []):
                row_data = metadata.get("data", {})
                data.append(row_data)

            return data

        except Exception as e:
            logger.error(f"按字段查询失败: {collection_name}, field={field}, error: {e}")
            return []

    async def query_with_filter(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        使用过滤条件查询

        Args:
            collection_name: 集合名称
            filter_dict: 过滤条件，如 {"data.字段1": "值1"}

        Returns:
            匹配的数据列表
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            results = collection.get(where=filter_dict, limit=DEFAULT_QUERY_LIMIT)

            data = []
            for metadata in results.get("metadatas", []):
                row_data = metadata.get("data", {})
                data.append(row_data)

            return data

        except Exception as e:
            logger.error(f"条件查询失败: {collection_name}, filter={filter_dict}, error: {e}")
            return []

    async def export_to_csv(
        self,
        collection_name: str
    ) -> Tuple[str, List[str], List[Dict[str, str]]]:
        """
        导出为 CSV 格式

        Args:
            collection_name: 集合名称

        Returns:
            (csv_content, headers, data)
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            results = collection.get(limit=DEFAULT_QUERY_LIMIT)

            if not results or not results.get("metadatas"):
                return "", [], []

            # 提取表头和数据
            headers = []
            data = []

            for metadata in results["metadatas"]:
                if not headers and metadata.get("headers"):
                    headers = metadata["headers"]
                row_data = metadata.get("data", {})
                data.append(row_data)

            # 生成 CSV 内容
            if not headers or not data:
                return "", headers, data

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

            return output.getvalue(), headers, data

        except Exception as e:
            logger.error(f"导出 CSV 失败: {collection_name}, error: {e}")
            return "", [], []

    async def get_doc_count(self, collection_name: str) -> int:
        """
        获取文档数量

        Args:
            collection_name: 集合名称

        Returns:
            文档数量
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            results = collection.get(limit=DEFAULT_QUERY_LIMIT)
            return len(results.get("ids", []))
        except Exception as e:
            logger.error(f"获取文档数量失败: {collection_name}, error: {e}")
            return 0

    def delete_collection_by_prefix(self, prefix: str) -> int:
        """
        根据前缀删除集合

        Args:
            prefix: 集合名称前缀

        Returns:
            删除的集合数量
        """
        try:
            client = self._get_client()
            # 获取所有集合
            collections = client.list_collections()
            deleted_count = 0

            for collection_name in collections:
                if collection_name.startswith(prefix):
                    try:
                        client.delete_collection(collection_name)
                        logger.info(f"删除 seekdb 集合: {collection_name}")
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"删除 seekdb 集合失败: {collection_name}, error: {e}")

            return deleted_count
        except Exception as e:
            logger.error(f"根据前缀删除集合失败: {prefix}, error: {e}")
            return 0


# 全局客户端实例
seekdb_client = SeekDBClient()
