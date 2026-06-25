"""
规则引擎 MCP 业务服务

职责：
- 处理规则引擎数据操纵的业务逻辑（select / update / delete）
- 调用 Repository 层进行 seekdb 数据操作
- 调用规则管理 Repository 层解析 rule_name -> collection_name
- 可被 FastMCP server、HTTP API 等多种入口复用

约束：
- 不直接初始化 Tortoise ORM，依赖 FastAPI 主应用生命周期已完成的初始化
- 不处理 MCP 协议细节，只返回可序列化的业务结果
"""
import json
from typing import Any, Dict, List, Optional

from tortoise.expressions import Q

from app.core.seekdb_client import seekdb_client
from app.log import logger
from app.repositories import rule_info_repository, rule_version_repository


class RuleEngineMCPService:
    """规则引擎 MCP 业务服务"""

    @staticmethod
    def _project_rows(rows: List[Dict[str, Any]], fields: Optional[List[str]]) -> List[Dict[str, Any]]:
        """对行数据进行字段投影。fields 为 None 或空时返回原行。"""
        if not fields:
            return rows
        return [{key: row.get(key) for key in fields if key in row} for row in rows]

    @staticmethod
    def _deduplicate_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对行数据按整行内容去重，保持顺序。"""
        seen = set()
        result = []
        for row in rows:
            key = json.dumps(row, sort_keys=True, ensure_ascii=False)
            if key not in seen:
                seen.add(key)
                result.append(row)
        return result

    async def _resolve_collection_name(self, rule_name: str) -> Optional[str]:
        """根据规则名称解析最新有效版本对应的 seekdb 集合名称。"""
        rule = await rule_info_repository.filter(Q(rule_name=rule_name)).first()
        if not rule:
            return None

        version = await rule_version_repository.filter(
            Q(rule_id=rule.id, status=1)
        ).order_by("-version_no").first()
        if not version or not version.seekdb_collection_name:
            return None

        return version.seekdb_collection_name

    async def manipulate(
        self,
        rule_name: str,
        op: str,
        filters: Dict[str, Any],
        update_values: Optional[Dict[str, Any]] = None,
        distinct: bool = True,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        对规则引擎数据进行查询、更新或删除操作。

        Args:
            rule_name: 规则名称，用于定位 seekdb 集合。
            op: 操作类型，可选 "select"、"update"、"delete"。
            filters: 字段过滤条件，例如 {"field_name": "xxx", "field_name2": "yyy"}。
            update_values: 更新操作时的字段值，仅在 op="update" 时有效。
            distinct: select 操作是否对结果去重，默认 True。
            fields: select 操作时返回的字段列表，用于字段投影。例如 ["level1_label", "level1_instruction"]。

        Returns:
            包含 success、op、rule_name 及操作结果的字典。
        """
        op = op.lower().strip()
        if op not in {"select", "update", "delete"}:
            return {"success": False, "error": f"不支持的操作类型: {op}"}

        collection_name = await self._resolve_collection_name(rule_name)
        if not collection_name:
            return {"success": False, "error": f"未找到规则或有效版本: {rule_name}"}

        seekdb_filter = {f"data.{key}": value for key, value in (filters or {}).items()}

        try:
            collection = seekdb_client.get_or_create_collection(collection_name)

            if op == "select":
                results = collection.get(where=seekdb_filter, limit=100000)
                rows = [metadata.get("data", {}) for metadata in results.get("metadatas", [])]
                # 先进行字段投影，再去重，确保按指定字段去重
                rows = self._project_rows(rows, fields)
                if distinct:
                    rows = self._deduplicate_rows(rows)
                return {
                    "success": True,
                    "op": op,
                    "rule_name": rule_name,
                    "count": len(rows),
                    "data": rows,
                }

            if op == "update":
                if not update_values:
                    return {"success": False, "error": "update 操作必须提供 update_values 参数"}

                results = collection.get(where=seekdb_filter, limit=100000)
                ids = results.get("ids", [])
                metadatas = results.get("metadatas", [])

                if not ids:
                    return {
                        "success": True,
                        "op": op,
                        "rule_name": rule_name,
                        "updated": 0,
                        "message": "没有匹配的数据",
                    }

                new_metadatas = []
                for metadata in metadatas:
                    new_metadata = dict(metadata)
                    data = dict(new_metadata.get("data", {}))
                    data.update(update_values)
                    new_metadata["data"] = data
                    new_metadatas.append(new_metadata)

                collection.update(ids=ids, metadatas=new_metadatas)
                return {
                    "success": True,
                    "op": op,
                    "rule_name": rule_name,
                    "updated": len(ids),
                }

            if op == "delete":
                if not seekdb_filter:
                    return {"success": False, "error": "delete 操作必须提供至少一个 filters 条件"}
                collection.delete(where=seekdb_filter)
                return {
                    "success": True,
                    "op": op,
                    "rule_name": rule_name,
                    "message": "删除请求已执行",
                }

        except Exception as e:
            logger.error(
                "规则引擎 MCP 操作失败",
                rule_name=rule_name,
                op=op,
                filters=filters,
                error=str(e),
            )
            return {"success": False, "error": f"操作失败: {e}"}


# 全局服务实例
rule_engine_mcp_service = RuleEngineMCPService()
