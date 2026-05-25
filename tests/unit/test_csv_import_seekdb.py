"""
CsvImportSeekdbService 单元测试

测试范围:
- CSV 解析
- 表头合并
- 数据迁移
- 兼容性检测
- 全量导入
- 增量导入
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.rule_management.csv_import_seekdb import CsvImportSeekdbService


class TestCsvImportSeekdbService:
    """CsvImportSeekdbService 测试类"""

    def test_parse_csv(self):
        """测试 CSV 解析"""
        csv_content = "name,value,status\nitem1,100,active\nitem2,200,inactive"

        headers, data = CsvImportSeekdbService.parse_csv(csv_content)

        assert headers == ["name", "value", "status"]
        assert len(data) == 2
        assert data[0]["name"] == "item1"
        assert data[0]["value"] == "100"
        assert data[0]["status"] == "active"

    def test_merge_headers(self):
        """测试表头合并"""
        existing_headers = ["name", "value"]
        new_headers = ["name", "status", "value"]

        merged_headers, field_mapping = CsvImportSeekdbService.merge_headers(
            existing_headers, new_headers
        )

        assert merged_headers == ["name", "value", "status"]
        assert field_mapping == {"name": "name", "value": "value"}

    def test_migrate_row_data(self):
        """测试数据迁移"""
        row = {"name": "item1", "value": "100"}
        merged_headers = ["name", "value", "status"]
        existing_headers = ["name", "value"]

        migrated = CsvImportSeekdbService.migrate_row_data(
            row, merged_headers, existing_headers
        )

        assert migrated["name"] == "item1"
        assert migrated["value"] == "100"
        assert migrated["status"] == ""  # 新增字段为空

    def test_detect_header_compatibility_compatible(self):
        """测试兼容性检测 - 完全兼容"""
        existing_headers = ["name", "value", "status"]
        new_headers = ["name", "value", "status"]

        result = CsvImportSeekdbService.detect_header_compatibility(
            existing_headers, new_headers
        )

        assert result["level"] == "compatible"
        assert result["is_safe"] is True
        assert result["added_fields"] == []
        assert result["removed_fields"] == []

    def test_detect_header_compatibility_additive(self):
        """测试兼容性检测 - 向后兼容（新增字段）"""
        existing_headers = ["name", "value"]
        new_headers = ["name", "value", "status"]

        result = CsvImportSeekdbService.detect_header_compatibility(
            existing_headers, new_headers
        )

        assert result["level"] == "additive"
        assert result["is_safe"] is True
        assert result["added_fields"] == ["status"]
        assert result["removed_fields"] == []

    def test_detect_header_compatibility_destructive(self):
        """测试兼容性检测 - 破坏性变更（删除字段）"""
        existing_headers = ["name", "value", "status"]
        new_headers = ["name", "value"]

        result = CsvImportSeekdbService.detect_header_compatibility(
            existing_headers, new_headers
        )

        assert result["level"] == "destructive"
        assert result["is_safe"] is False
        assert result["added_fields"] == []
        assert result["removed_fields"] == ["status"]

    def test_detect_header_compatibility_mixed(self):
        """测试兼容性检测 - 混合变更"""
        existing_headers = ["name", "value", "status"]
        new_headers = ["name", "value", "category"]

        result = CsvImportSeekdbService.detect_header_compatibility(
            existing_headers, new_headers
        )

        assert result["level"] == "mixed"
        assert result["is_safe"] is False
        assert "status" in result["removed_fields"]
        assert "category" in result["added_fields"]

    @pytest.mark.asyncio
    async def test_full_import(self):
        """测试全量导入"""
        import tempfile
        from app.services.storage.seekdb_service import SeekDBService

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            seekdb_service = SeekDBService(db_path=db_path)

            csv_content = "name,value\nitem1,100\nitem2,200"
            collection_name = "test_full_import"

            result = await CsvImportSeekdbService.full_import(
                collection_name=collection_name,
                csv_content=csv_content,
                rule_id=1,
                version_no=1,
                tenant_id=1,
                app_name="test",
                rule_code="test_rule"
            )

            assert result["added_count"] == 2
            assert result["updated_count"] == 0
            assert result["total_count"] == 2
            assert result["headers"] == ["name", "value"]

    @pytest.mark.asyncio
    async def test_full_import_empty_csv(self):
        """测试全量导入空 CSV"""
        csv_content = ""
        collection_name = "test_empty"

        result = await CsvImportSeekdbService.full_import(
            collection_name=collection_name,
            csv_content=csv_content,
            rule_id=1,
            version_no=1,
            tenant_id=1,
            app_name="test",
            rule_code="test_rule"
        )

        assert "error" in result
        assert result["added_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
