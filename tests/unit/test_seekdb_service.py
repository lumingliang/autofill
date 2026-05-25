"""
SeekDBService 单元测试

测试范围:
- 集合创建和删除
- 规则数据保存和读取
- 字段查询
- CSV 导出
"""

import pytest
import tempfile
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.storage.seekdb_service import SeekDBService


class TestSeekDBService:
    """SeekDBService 测试类"""

    @pytest.fixture
    async def seekdb_service(self):
        """创建测试用的 seekdb 服务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_seekdb.db")
            service = SeekDBService(db_path=db_path)
            yield service

    @pytest.mark.asyncio
    async def test_create_and_delete_collection(self, seekdb_service):
        """测试创建和删除集合"""
        collection_name = "test_collection"

        # 创建集合
        collection = seekdb_service.get_or_create_collection(collection_name)
        assert collection is not None

        # 删除集合
        result = seekdb_service.delete_collection(collection_name)
        assert result is True

    @pytest.mark.asyncio
    async def test_save_and_get_rule_data(self, seekdb_service):
        """测试保存和读取规则数据"""
        collection_name = "test_rule_data"
        headers = ["name", "value", "status"]
        data = [
            {"name": "item1", "value": "100", "status": "active"},
            {"name": "item2", "value": "200", "status": "inactive"},
            {"name": "item3", "value": "300", "status": "active"}
        ]

        # 保存数据
        doc_count = await seekdb_service.save_rule_data(
            collection_name=collection_name,
            headers=headers,
            data=data,
            rule_id=1,
            version_no=1,
            tenant_id=1,
            app_name="test",
            rule_code="test_rule"
        )

        assert doc_count == 3

        # 读取数据
        result = await seekdb_service.get_rule_data(collection_name)
        assert result is not None
        assert result["headers"] == headers
        assert len(result["data"]) == 3

    @pytest.mark.asyncio
    async def test_query_by_field(self, seekdb_service):
        """测试按字段查询"""
        collection_name = "test_query"
        headers = ["name", "value", "status"]
        data = [
            {"name": "item1", "value": "100", "status": "active"},
            {"name": "item2", "value": "200", "status": "inactive"},
            {"name": "item3", "value": "300", "status": "active"}
        ]

        # 保存数据
        await seekdb_service.save_rule_data(
            collection_name=collection_name,
            headers=headers,
            data=data,
            rule_id=1,
            version_no=1,
            tenant_id=1,
            app_name="test",
            rule_code="test_rule"
        )

        # 按字段查询
        results = await seekdb_service.query_by_field(
            collection_name=collection_name,
            field="status",
            value="active"
        )

        assert len(results) == 2
        assert all(r["status"] == "active" for r in results)

    @pytest.mark.asyncio
    async def test_export_to_csv(self, seekdb_service):
        """测试导出 CSV"""
        collection_name = "test_export"
        headers = ["name", "value"]
        data = [
            {"name": "item1", "value": "100"},
            {"name": "item2", "value": "200"}
        ]

        # 保存数据
        await seekdb_service.save_rule_data(
            collection_name=collection_name,
            headers=headers,
            data=data,
            rule_id=1,
            version_no=1,
            tenant_id=1,
            app_name="test",
            rule_code="test_rule"
        )

        # 导出 CSV
        csv_content, export_headers, export_data = await seekdb_service.export_to_csv(collection_name)

        assert csv_content is not None
        assert len(csv_content) > 0
        assert export_headers == headers
        assert len(export_data) == 2

    @pytest.mark.asyncio
    async def test_get_doc_count(self, seekdb_service):
        """测试获取文档数量"""
        collection_name = "test_count"
        headers = ["name"]
        data = [
            {"name": "item1"},
            {"name": "item2"},
            {"name": "item3"}
        ]

        # 保存数据
        await seekdb_service.save_rule_data(
            collection_name=collection_name,
            headers=headers,
            data=data,
            rule_id=1,
            version_no=1,
            tenant_id=1,
            app_name="test",
            rule_code="test_rule"
        )

        # 获取数量
        count = await seekdb_service.get_doc_count(collection_name)
        assert count == 3

    @pytest.mark.asyncio
    async def test_empty_data(self, seekdb_service):
        """测试空数据处理"""
        collection_name = "test_empty"

        # 保存空数据
        doc_count = await seekdb_service.save_rule_data(
            collection_name=collection_name,
            headers=[],
            data=[],
            rule_id=1,
            version_no=1,
            tenant_id=1,
            app_name="test",
            rule_code="test_rule"
        )

        assert doc_count == 0

        # 读取空数据
        result = await seekdb_service.get_rule_data(collection_name)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
