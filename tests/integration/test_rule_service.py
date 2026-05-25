"""
RuleService 集成测试

测试范围:
- 规则创建
- 版本保存（使用 seekdb）
- 版本读取
- 版本历史
- 规则删除
"""

import pytest
import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.rule_management.rule_service import rule_service, VersionConflictException, NoChangeException


class TestRuleService:
    """RuleService 集成测试类"""

    @pytest.fixture(scope="class")
    def event_loop(self):
        """创建事件循环"""
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    @pytest.fixture(scope="class")
    async def init_tortoise(self):
        """初始化数据库"""
        from tortoise import Tortoise
        from app.settings.config import settings

        await Tortoise.init(config=settings.TORTOISE_ORM)
        yield
        await Tortoise.close_connections()

    @pytest.mark.asyncio
    async def test_create_rule(self, init_tortoise):
        """测试创建规则"""
        import uuid
        rule_code = f"test_rule_{uuid.uuid4().hex[:8]}"

        rule = await rule_service.create_rule(
            rule_name="测试规则",
            desc="测试描述",
            rule_code=rule_code,
            tenant_id=1,
            app_name="test"
        )

        assert rule is not None
        assert rule.rule_code == rule_code
        assert rule.rule_name == "测试规则"

        # 清理
        await rule.delete()

    @pytest.mark.asyncio
    async def test_save_version_to_seekdb(self, init_tortoise):
        """测试保存版本到 seekdb"""
        import uuid
        from app.models.rule_management import RuleInfo

        rule_code = f"test_version_{uuid.uuid4().hex[:8]}"

        # 创建规则
        rule = await rule_service.create_rule(
            rule_name="版本测试规则",
            rule_code=rule_code,
            tenant_id=1,
            app_name="test"
        )

        # 准备 CSV 数据
        content_json = {
            "headers": ["name", "value", "status"],
            "data": [
                ["item1", "100", "active"],
                ["item2", "200", "inactive"]
            ]
        }

        # 保存版本
        version = await rule_service.save_version(
            rule=rule,
            content_json=content_json,
            current_md5="",
            remark="初始版本"
        )

        assert version is not None
        assert version.version_no == 1
        assert version.seekdb_collection_name != ""
        assert version.doc_count == 2
        assert version.headers == ["name", "value", "status"]

        # 清理
        await version.delete()
        await rule.delete()

    @pytest.mark.asyncio
    async def test_get_version_content(self, init_tortoise):
        """测试获取版本内容"""
        import uuid
        from app.models.rule_management import RuleInfo

        rule_code = f"test_get_{uuid.uuid4().hex[:8]}"

        # 创建规则和版本
        rule = await rule_service.create_rule(
            rule_name="获取测试规则",
            rule_code=rule_code,
            tenant_id=1,
            app_name="test"
        )

        content_json = {
            "headers": ["name", "value"],
            "data": [
                ["item1", "100"],
                ["item2", "200"]
            ]
        }

        version = await rule_service.save_version(
            rule=rule,
            content_json=content_json,
            current_md5="",
            remark="测试版本"
        )

        # 获取内容
        content = await rule_service._get_content_json(version)

        assert content is not None
        assert content["headers"] == ["name", "value"]
        assert len(content["data"]) == 2

        # 清理
        await version.delete()
        await rule.delete()

    @pytest.mark.asyncio
    async def test_version_conflict(self, init_tortoise):
        """测试版本冲突"""
        import uuid
        from app.models.rule_management import RuleInfo

        rule_code = f"test_conflict_{uuid.uuid4().hex[:8]}"

        # 创建规则和第一个版本
        rule = await rule_service.create_rule(
            rule_name="冲突测试规则",
            rule_code=rule_code,
            tenant_id=1,
            app_name="test"
        )

        content_json = {
            "headers": ["name"],
            "data": [["item1"]]
        }

        version1 = await rule_service.save_version(
            rule=rule,
            content_json=content_json,
            current_md5="",
            remark="版本1"
        )

        # 尝试用错误的 MD5 保存新版本
        with pytest.raises(VersionConflictException):
            await rule_service.save_version(
                rule=rule,
                content_json={"headers": ["name"], "data": [["item2"]]},
                current_md5="wrong_md5",
                remark="版本2"
            )

        # 清理
        await version1.delete()
        await rule.delete()

    @pytest.mark.asyncio
    async def test_no_change_exception(self, init_tortoise):
        """测试无变化异常"""
        import uuid
        from app.models.rule_management import RuleInfo

        rule_code = f"test_no_change_{uuid.uuid4().hex[:8]}"

        # 创建规则和版本
        rule = await rule_service.create_rule(
            rule_name="无变化测试规则",
            rule_code=rule_code,
            tenant_id=1,
            app_name="test"
        )

        content_json = {
            "headers": ["name"],
            "data": [["item1"]]
        }

        version = await rule_service.save_version(
            rule=rule,
            content_json=content_json,
            current_md5="",
            remark="版本1"
        )

        # 尝试保存相同内容
        with pytest.raises(NoChangeException):
            await rule_service.save_version(
                rule=rule,
                content_json=content_json,
                current_md5=version.content_md5,
                remark="版本2"
            )

        # 清理
        await version.delete()
        await rule.delete()

    @pytest.mark.asyncio
    async def test_get_version_history(self, init_tortoise):
        """测试获取版本历史"""
        import uuid
        from app.models.rule_management import RuleInfo

        rule_code = f"test_history_{uuid.uuid4().hex[:8]}"

        # 创建规则和多个版本
        rule = await rule_service.create_rule(
            rule_name="历史测试规则",
            rule_code=rule_code,
            tenant_id=1,
            app_name="test"
        )

        # 保存两个版本
        content1 = {"headers": ["name"], "data": [["v1"]]}
        content2 = {"headers": ["name"], "data": [["v2"]]}

        version1 = await rule_service.save_version(
            rule=rule,
            content_json=content1,
            current_md5="",
            remark="版本1"
        )

        version2 = await rule_service.save_version(
            rule=rule,
            content_json=content2,
            current_md5=version1.content_md5,
            remark="版本2"
        )

        # 获取历史
        total, history = await rule_service.get_version_history(
            rule_code=rule_code,
            tenant_id=1
        )

        assert total == 2
        assert len(history) == 2
        assert history[0]["version_no"] == 2
        assert history[1]["version_no"] == 1

        # 清理
        await version2.delete()
        await version1.delete()
        await rule.delete()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
