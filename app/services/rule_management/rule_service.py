"""
规则管理服务层 - 使用 seekdb 存储 CSV 数据（重构版）

严格遵循技术约束文档：
- 处理业务逻辑
- 调用 Repository 层进行数据操作
- 使用 @atomic() 装饰器控制事务
- 禁止直接查询 Model 层
- 禁止将 tenant_id 传递给 Repository 方法
"""
import csv
import hashlib
import io
import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from pypinyin import lazy_pinyin
except ImportError:
    lazy_pinyin = None

from tortoise.transactions import atomic

from app.core.ctx import Ctx
from app.log import logger
from app.models.rule_management import RuleInfo, RuleVersion
from app.repositories import rule_info_repository, rule_version_repository, rule_data_repository
from app.services.storage.seekdb_service import seekdb_service


class VersionConflictException(Exception):
    """版本冲突异常"""
    pass


class NoChangeException(Exception):
    """内容未变化异常"""
    pass


class RuleService:
    """
    规则管理业务服务 - 使用 seekdb 存储

    职责：
    - 处理规则管理的业务逻辑
    - 调用 Repository 层进行数据操作
    - 管理事务控制

    约束：
    - 写操作使用 @atomic() 装饰器
    - 不直接查询 Model 层
    - 不将 tenant_id 传递给 Repository 方法
    """

    @staticmethod
    def generate_rule_code(rule_name: str = None) -> str:
        """自动生成规则编码"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = uuid.uuid4().hex[:4]

        if rule_name:
            prefix = RuleService._to_pinyin(rule_name)[:20]
            prefix = RuleService._sanitize_code(prefix)
            if prefix:
                return f"{prefix}_{timestamp}_{random_suffix}"

        return f"rule_{timestamp}_{random_suffix}"

    @staticmethod
    def _to_pinyin(text: str) -> str:
        """中文转拼音"""
        if lazy_pinyin is None:
            return "rule"
        return '_'.join(lazy_pinyin(text))

    @staticmethod
    def _sanitize_code(text: str) -> str:
        """清理编码字符串"""
        text = re.sub(r'[^a-zA-Z0-9_]', '_', text).lower()
        return text.strip('_')

    @staticmethod
    def calculate_md5(content_json: Dict[str, Any]) -> str:
        """计算内容MD5"""
        return hashlib.md5(
            json.dumps(content_json, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

    @staticmethod
    def _generate_collection_name(rule_id: int, rule_code: str, version_no: int) -> str:
        """生成 seekdb 集合名称"""
        return f"rule_{rule_id}_{rule_code}_v{version_no}"

    async def get_rule_by_code(
        self,
        rule_code: str,
        app_name: str = ""
    ) -> Optional[RuleInfo]:
        """根据编码获取规则"""
        return await rule_info_repository.get_by_code(
            rule_code=rule_code,
            app_name=app_name
        )

    async def get_rule_by_id(
        self,
        rule_id: int
    ) -> Optional[RuleInfo]:
        """根据ID获取规则"""
        return await rule_info_repository.get_by_id(rule_id=rule_id)

    async def list_rules(
        self,
        app_name: str = "",
        keyword: str = "",
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[int, List[RuleInfo]]:
        """获取规则列表"""
        return await rule_info_repository.list_rules(
            app_name=app_name,
            keyword=keyword,
            status=status,
            page=page,
            page_size=page_size
        )

    async def get_rule_detail(
        self,
        rule_code: str,
        app_name: str = ""
    ) -> Optional[Dict[str, Any]]:
        """获取规则详情（包含最新版本）"""
        rule = await self.get_rule_by_code(rule_code, app_name)
        if not rule:
            return None

        result = {
            "rule_info": await rule.to_dict(),
            "current_version": None
        }

        if rule.latest_version_id:
            # 使用 Repository 获取版本
            version = await rule_version_repository.get_by_id(
                version_id=rule.latest_version_id
            )
            if version:
                result["current_version"] = await self.version_to_dict(version)

        return result

    async def version_to_dict(self, version: RuleVersion) -> Dict[str, Any]:
        """转换版本对象为字典"""
        content_json = await self.get_content_json(version)

        return {
            "id": version.id,
            "tenant_id": version.tenant_id,
            "app_name": version.app_name,
            "rule_id": version.rule_id,
            "rule_code": version.rule_code,
            "version_no": version.version_no,
            "content_md5": version.content_md5,
            "seekdb_collection_name": version.seekdb_collection_name,
            "doc_count": version.doc_count,
            "headers": version.headers,
            "content_json": content_json,
            "remark": version.remark,
            "status": version.status,
            "created_at": version.created_at.strftime("%Y-%m-%d %H:%M:%S") if version.created_at else ""
        }

    async def get_content_json(self, version: RuleVersion) -> Optional[Dict[str, Any]]:
        """从 seekdb 获取版本内容"""
        if not version.seekdb_collection_name:
            return None

        # 使用 Repository 层获取数据
        return await rule_data_repository.get_by_collection(version.seekdb_collection_name)

    async def _save_content(
        self,
        rule_id: int,
        rule_code: str,
        version_no: int,
        content_json: Dict[str, Any],
        tenant_id: int,
        app_name: str
    ) -> Dict[str, Any]:
        """保存内容到 seekdb"""
        headers = content_json.get("headers", [])
        data = content_json.get("data", [])

        # 生成集合名称
        collection_name = self._generate_collection_name(rule_id, rule_code, version_no)

        # 转换数据格式
        dict_data = []
        for row in data:
            row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            dict_data.append(row_dict)

        # 保存到 seekdb
        doc_count = await seekdb_service.save_rule_data(
            collection_name=collection_name,
            headers=headers,
            data=dict_data,
            rule_id=rule_id,
            version_no=version_no,
            tenant_id=tenant_id,
            app_name=app_name,
            rule_code=rule_code
        )

        return {
            "collection_name": collection_name,
            "doc_count": doc_count,
            "headers": headers
        }

    @atomic()
    async def create_rule(
        self,
        rule_name: str,
        desc: str = "",
        rule_code: str = None,
        app_name: str = ""
    ) -> RuleInfo:
        """
        创建新规则

        使用 @atomic() 装饰器控制事务
        """
        if not rule_code:
            rule_code = self.generate_rule_code(rule_name)

        # 使用 Repository 检查编码是否已存在
        if await rule_info_repository.check_code_exists(
            rule_code=rule_code,
            app_name=app_name
        ):
            raise ValueError(f"规则编码已存在: {rule_code}")

        # 检查规则名称是否已存在
        if await rule_info_repository.check_name_exists(
            rule_name=rule_name,
            app_name=app_name
        ):
            raise ValueError(f"规则名称已存在: {rule_name}")

        # 创建规则（tenant_id 由 Repository 自动注入）
        create_data = {
            "app_name": app_name,
            "rule_code": rule_code,
            "rule_name": rule_name,
            "desc": desc,
            "status": 1
        }

        rule = await rule_info_repository.create(create_data)
        logger.info("创建规则成功", rule_id=rule.id, rule_code=rule_code)
        return rule

    @atomic()
    async def save_version(
        self,
        rule: RuleInfo,
        content_json: Dict[str, Any],
        current_md5: str,
        remark: str = ""
    ) -> RuleVersion:
        """
        保存新版本（带乐观锁）

        使用 @atomic() 装饰器控制事务
        """
        if not rule:
            raise ValueError("规则不存在")

        # 使用 Repository 获取最新版本
        latest_version = await rule_version_repository.get_latest(rule_id=rule.id)

        logger.info(
            "save_version debug",
            rule_id=rule.id,
            current_md5=current_md5,
            latest_version_md5=latest_version.content_md5 if latest_version else None,
            latest_version_no=latest_version.version_no if latest_version else None,
            content_json_keys=list(content_json.keys()) if content_json else None,
            content_json_data_count=len(content_json.get("data", [])) if content_json else 0,
            remark=remark
        )

        new_md5 = self.calculate_md5(content_json)

        logger.info(
            "MD5 comparison",
            new_md5=new_md5,
            current_md5=current_md5,
            is_same=new_md5 == current_md5
        )

        version_no = (latest_version.version_no + 1) if latest_version else 1

        storage_result = await self._save_content(
            rule_id=rule.id,
            rule_code=rule.rule_code,
            version_no=version_no,
            content_json=content_json,
            tenant_id=rule.tenant_id,
            app_name=rule.app_name
        )

        # 创建版本（tenant_id 由 Repository 自动注入）
        create_data = {
            "app_name": rule.app_name,
            "rule_id": rule.id,
            "rule_code": rule.rule_code,
            "version_no": version_no,
            "content_md5": new_md5,
            "seekdb_collection_name": storage_result["collection_name"],
            "doc_count": storage_result["doc_count"],
            "headers": storage_result["headers"],
            "remark": remark or "",
            "status": 1
        }

        new_version = await rule_version_repository.create(create_data)

        # 更新规则的最新版本ID（使用 Repository 层）
        await rule_info_repository.update(
            rule.id,
            {"latest_version_id": new_version.id}
        )

        logger.info(
            "保存版本成功",
            rule_id=rule.id,
            version_no=version_no,
            collection_name=storage_result["collection_name"],
            doc_count=storage_result["doc_count"]
        )
        return new_version

    @atomic()
    async def create_version_record(
        self,
        rule: RuleInfo,
        collection_name: str,
        headers: List[str],
        doc_count: int,
        remark: str = ""
    ) -> RuleVersion:
        """
        直接创建版本记录（用于CSV导入场景）

        使用 @atomic() 装饰器控制事务

        注意：此方法不保存数据到seekdb，因为数据已经通过CSV导入保存过了。
        """
        if not rule:
            raise ValueError("规则不存在")

        # 使用 Repository 获取最新版本
        latest_version = await rule_version_repository.get_latest(rule_id=rule.id)

        version_no = (latest_version.version_no + 1) if latest_version else 1
        content_json = {"headers": headers, "data": []}
        new_md5 = self.calculate_md5(content_json)

        # 创建版本（tenant_id 由 Repository 自动注入）
        create_data = {
            "app_name": rule.app_name,
            "rule_id": rule.id,
            "rule_code": rule.rule_code,
            "version_no": version_no,
            "content_md5": new_md5,
            "seekdb_collection_name": collection_name,
            "doc_count": doc_count,
            "headers": headers,
            "remark": remark or "",
            "status": 1
        }

        new_version = await rule_version_repository.create(create_data)

        # 更新规则的最新版本ID（使用 Repository 层）
        await rule_info_repository.update(
            rule.id,
            {"latest_version_id": new_version.id}
        )

        logger.info(
            "创建版本记录成功（CSV导入）",
            rule_id=rule.id,
            version_no=version_no,
            collection_name=collection_name,
            doc_count=doc_count
        )

        return new_version

    async def get_version_history(
        self,
        rule_code: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """获取版本历史"""
        # 使用 Repository 获取规则
        rule = await rule_info_repository.get_by_code(rule_code=rule_code)
        if not rule:
            raise ValueError(f"规则不存在: {rule_code}")

        # 使用 Repository 获取版本列表
        total, versions = await rule_version_repository.list_versions(
            rule_id=rule.id,
            page=page,
            page_size=page_size
        )

        version_list = []
        for v in versions:
            version_list.append({
                "id": v.id,
                "version_no": v.version_no,
                "content_md5": v.content_md5,
                "seekdb_collection_name": v.seekdb_collection_name,
                "doc_count": v.doc_count,
                "headers": v.headers,
                "remark": v.remark,
                "status": v.status,
                "created_at": v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else ""
            })

        return total, version_list

    async def get_version_by_no(
        self,
        rule_code: str,
        version_no: int
    ) -> Optional[Dict[str, Any]]:
        """获取指定版本"""
        # 使用 Repository 获取规则
        rule = await rule_info_repository.get_by_code(rule_code=rule_code)
        if not rule:
            return None

        # 直接根据 rule_id 和 version_no 查询版本
        version = await rule_version_repository.get_by_rule_id_and_version_no(
            rule_id=rule.id,
            version_no=version_no
        )

        if not version:
            return None

        return await self.version_to_dict(version)

    async def get_version_by_id(
        self,
        version_id: int
    ) -> Optional[RuleVersion]:
        """根据ID获取版本"""
        return await rule_version_repository.get_by_id(version_id=version_id)

    @atomic()
    async def rollback_version(
        self,
        rule_code: str,
        version_no: int
    ) -> RuleVersion:
        """
        回滚到指定版本

        使用 @atomic() 装饰器控制事务
        """
        rule = await self.get_rule_by_code(rule_code)
        if not rule:
            raise ValueError(f"规则不存在: {rule_code}")

        # 直接根据 rule_id 和 version_no 查询版本
        target_version = await rule_version_repository.get_by_rule_id_and_version_no(
            rule_id=rule.id,
            version_no=version_no
        )

        if not target_version:
            raise ValueError(f"版本不存在: {version_no}")

        content_json = await self.get_content_json(target_version)
        if not content_json:
            raise ValueError("无法获取版本内容")

        # 使用 Repository 获取最新版本
        latest_version = await rule_version_repository.get_latest(rule_id=rule.id)

        current_md5 = latest_version.content_md5 if latest_version else ""

        return await self.save_version(
            rule=rule,
            content_json=content_json,
            current_md5=current_md5,
            remark=f"回滚到版本 {version_no}"
        )

    @atomic()
    async def update_rule(
        self,
        rule_id: int,
        rule_name: str = None,
        desc: str = None,
        status: int = None
    ) -> RuleInfo:
        """
        更新规则信息

        使用 @atomic() 装饰器控制事务
        """
        # 使用 Repository 获取规则
        rule = await rule_info_repository.get_by_id(rule_id=rule_id)
        if not rule:
            raise ValueError(f"规则不存在: {rule_id}")

        # 检查新名称是否与其他规则冲突（排除自身）
        update_data = {}
        if rule_name is not None and rule_name != rule.rule_name:
            if await rule_info_repository.check_name_exists(
                rule_name=rule_name,
                app_name=rule.app_name,
                exclude_id=rule_id
            ):
                raise ValueError(f"规则名称已存在: {rule_name}")
            update_data["rule_name"] = rule_name

        if desc is not None:
            update_data["desc"] = desc
        if status is not None:
            update_data["status"] = status

        if update_data:
            rule = await rule_info_repository.update(rule_id, update_data)

        logger.info("更新规则成功", rule_id=rule.id, rule_code=rule.rule_code)
        return rule

    @atomic()
    async def delete_rule(
        self,
        rule_code: str,
        app_name: str = ""
    ) -> None:
        """
        删除规则（物理删除）

        使用 @atomic() 装饰器控制事务
        """
        rule = await self.get_rule_by_code(rule_code, app_name)
        if not rule:
            raise ValueError(f"规则不存在: {rule_code}")

        # 获取所有版本并删除 seekdb 集合
        _, versions = await rule_version_repository.list_versions(
            rule_id=rule.id,
            page=1,
            page_size=10000
        )
        for version in versions:
            # 删除 seekdb 集合
            if version.seekdb_collection_name:
                seekdb_service.delete_collection(version.seekdb_collection_name)

        # 物理删除所有版本
        await rule_version_repository.delete_by_rule_id(rule.id)

        # 物理删除规则
        await rule_info_repository.delete(rule.id)

        logger.info("删除规则成功", rule_id=rule.id, rule_code=rule_code)

    @atomic()
    async def update_rule_config(
        self,
        rule_id: int,
        config: Dict[str, Any]
    ) -> RuleInfo:
        """
        更新规则配置

        使用 @atomic() 装饰器控制事务
        """
        rule = await rule_info_repository.get_by_id(rule_id=rule_id)
        if not rule:
            raise ValueError(f"规则不存在: {rule_id}")

        # 更新规则配置（使用 Repository 层）
        rule = await rule_info_repository.update(
            rule_id,
            {"config": json.dumps(config, indent=2, ensure_ascii=False)}
        )

        logger.info("更新规则配置成功", rule_id=rule.id, rule_code=rule.rule_code)
        return rule

    async def parse_csv_to_json(self, csv_content: str) -> Dict[str, Any]:
        """解析CSV内容为JSON格式"""
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        if not rows:
            return {"headers": [], "data": []}

        headers = rows[0]
        data = rows[1:]

        return {
            "headers": headers,
            "data": data
        }

    async def convert_json_to_csv(self, content_json: Dict[str, Any]) -> str:
        """将JSON内容转换为CSV格式"""
        headers = content_json.get("headers", [])
        data = content_json.get("data", [])

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow(headers)

        # 写入数据
        for row in data:
            writer.writerow(row)

        return output.getvalue()


# 创建全局服务实例
rule_service = RuleService()
