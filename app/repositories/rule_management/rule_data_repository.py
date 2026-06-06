"""
RuleData Repository - 规则数据（seekdb）访问层
"""
from typing import Any, Dict, List, Optional

from app.core.seekdb_client import seekdb_client
from app.log import logger


class RuleDataRepository:
    """规则数据仓库（seekdb 操作）"""

    async def get_by_collection(
        self,
        collection_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        从 seekdb 获取规则数据

        Args:
            collection_name: seekdb 集合名称

        Returns:
            规则数据或 None
        """
        try:
            return await seekdb_client.get_rule_data(collection_name)
        except Exception as e:
            logger.error(
                "从 seekdb 获取规则数据失败",
                collection=collection_name,
                error=str(e)
            )
            return None

    async def query_with_filter(
        self,
        collection_name: str,
        filter_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        使用过滤条件查询 seekdb

        Args:
            collection_name: seekdb 集合名称
            filter_config: 过滤配置 {字段名: 值}

        Returns:
            数据列表
        """
        try:
            if filter_config:
                seekdb_filter = {f"data.{key}": value for key, value in filter_config.items()}
                return await seekdb_client.query_with_filter(collection_name, seekdb_filter)
            else:
                return await seekdb_client.query_with_filter(collection_name, {})
        except Exception as e:
            logger.error(
                "从 seekdb 查询规则数据失败",
                collection=collection_name,
                filter=filter_config,
                error=str(e)
            )
            return []

    async def search_similar(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 10,
        filter_config: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        在 seekdb 中搜索相似内容

        Args:
            collection_name: seekdb 集合名称
            query_text: 查询文本
            top_k: 返回数量
            filter_config: 过滤配置

        Returns:
            相似数据列表
        """
        try:
            return await seekdb_client.search_similar(
                collection_name=collection_name,
                query_text=query_text,
                top_k=top_k,
                filter_config=filter_config
            )
        except Exception as e:
            logger.error(
                "从 seekdb 搜索相似数据失败",
                collection=collection_name,
                query=query_text,
                error=str(e)
            )
            return []


# 创建全局仓库实例
rule_data_repository = RuleDataRepository()
