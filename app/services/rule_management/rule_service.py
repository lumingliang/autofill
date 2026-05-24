"""
规则管理服务层
"""
import base64
import csv
import gzip
import hashlib
import io
import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.log import logger
from app.models.rule_management import RuleInfo, RuleVersion
from app.services.storage.file_service import file_service
from tortoise.expressions import Q


class VersionConflictException(Exception):
    """版本冲突异常"""
    pass


class NoChangeException(Exception):
    """内容未变化异常"""
    pass


class RuleService:
    """规则管理业务服务"""

    SIZE_THRESHOLD = 1024 * 1024  # 1MB

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
        try:
            from pypinyin import lazy_pinyin
            return '_'.join(lazy_pinyin(text))
        except ImportError:
            return "rule"

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

    async def create_rule(
        self,
        rule_name: str,
        desc: str = "",
        rule_code: str = None,
        tenant_id: int = 0,
        app_name: str = ""
    ) -> RuleInfo:
        """创建新规则"""
        if not rule_code:
            rule_code = self.generate_rule_code(rule_name)

        existing = await RuleInfo.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            rule_code=rule_code,
            deleted=0
        ).first()

        if existing:
            raise ValueError(f"规则编码已存在: {rule_code}")

        rule = await RuleInfo.create(
            tenant_id=tenant_id,
            app_name=app_name,
            rule_code=rule_code,
            rule_name=rule_name,
            desc=desc,
            status=1,
            deleted=0
        )
        logger.info("创建规则成功", rule_id=rule.id, rule_code=rule_code)
        return rule

    async def get_rule_by_code(
        self,
        rule_code: str,
        tenant_id: int = 0,
        app_name: str = ""
    ) -> Optional[RuleInfo]:
        """根据编码获取规则"""
        # 只使用 tenant_id 和 rule_code 查询，不使用 app_name
        query = RuleInfo.filter(
            tenant_id=tenant_id,
            rule_code=rule_code,
            deleted=0
        )
        # 如果提供了 app_name，则作为可选条件
        if app_name:
            query = query.filter(app_name=app_name)
        return await query.first()

    async def list_rules(
        self,
        tenant_id: int = 0,
        app_name: str = "",
        keyword: str = "",
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[int, List[RuleInfo]]:
        """获取规则列表"""
        query = RuleInfo.filter(deleted=0)

        # 只有指定了 tenant_id 才进行过滤
        if tenant_id > 0:
            query = query.filter(tenant_id=tenant_id)

        # 只有指定了 app_name 才进行过滤
        if app_name:
            query = query.filter(app_name=app_name)

        if keyword:
            query = query.filter(
                Q(rule_code__contains=keyword) | Q(rule_name__contains=keyword)
            )

        if status is not None:
            query = query.filter(status=status)

        total = await query.count()
        rules = await query.order_by("-updated_at").offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return total, rules

    async def get_rule_detail(
        self,
        rule_code: str,
        tenant_id: int = 0,
        app_name: str = ""
    ) -> Optional[Dict[str, Any]]:
        """获取规则详情（包含最新版本）"""
        rule = await self.get_rule_by_code(rule_code, tenant_id, app_name)
        if not rule:
            return None

        result = {
            "rule_info": await rule.to_dict(),
            "current_version": None
        }

        if rule.latest_version_id:
            version = await RuleVersion.filter(
                id=rule.latest_version_id,
                deleted=0
            ).first()
            if version:
                result["current_version"] = await self._version_to_dict(version)

        return result

    async def _version_to_dict(self, version: RuleVersion) -> Dict[str, Any]:
        """转换版本对象为字典"""
        content_json = await self._get_content_json(version)

        return {
            "id": version.id,
            "tenant_id": version.tenant_id,
            "app_name": version.app_name,
            "version_no": version.version_no,
            "content_md5": version.content_md5,
            "storage_type": version.storage_type,
            "content_json": content_json,
            "file_size": version.file_size,
            "remark": version.remark,
            "status": version.status,
            "created_at": version.created_at.strftime("%Y-%m-%d %H:%M:%S") if version.created_at else ""
        }

    async def _get_content_json(self, version: RuleVersion) -> Optional[Dict[str, Any]]:
        """获取版本内容"""
        if version.storage_type == 1:
            if version.content_json:
                try:
                    compressed = base64.b64decode(version.content_json)
                    json_str = gzip.decompress(compressed).decode('utf-8')
                    return json.loads(json_str)
                except Exception as e:
                    logger.error("解析内容失败", error=str(e))
                    return None
            return None
        else:
            if version.file_path:
                try:
                    content = await file_service.read_file(version.file_path)
                    return json.loads(content)
                except Exception as e:
                    logger.error("读取文件失败", error=str(e))
                    return None
            return None

    async def _save_content(
        self,
        rule_code: str,
        version_no: int,
        content_json: Dict[str, Any],
        tenant_id: int,
        app_name: str
    ) -> Dict[str, Any]:
        """保存内容，自动选择存储方式"""
        json_str = json.dumps(content_json, ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')

        compressed = gzip.compress(json_bytes)
        file_size = len(compressed)

        if file_size < self.SIZE_THRESHOLD:
            return {
                "storage_type": 1,
                "content_json": base64.b64encode(compressed).decode('utf-8'),
                "file_path": "",
                "file_size": file_size
            }
        else:
            file_name = f"{rule_code}_v{version_no}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json.gz"
            relative_path = f"rules/{tenant_id}/{app_name}/{file_name}"
            file_path = await file_service.save_file(relative_path, compressed)

            return {
                "storage_type": 2,
                "content_json": None,
                "file_path": file_path,
                "file_size": file_size
            }

    async def save_version(
        self,
        rule: RuleInfo,
        content_json: Dict[str, Any],
        current_md5: str,
        remark: str = ""
    ) -> RuleVersion:
        """保存新版本（带乐观锁）"""
        if not rule:
            raise ValueError("规则不存在")

        latest_version = await RuleVersion.filter(
            rule_id=rule.id,
            deleted=0
        ).order_by("-version_no").first()

        # 添加详细日志用于调试
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

        if latest_version and latest_version.content_md5 != current_md5:
            logger.warning(
                "VersionConflictException triggered",
                latest_md5=latest_version.content_md5,
                current_md5=current_md5
            )
            latest_version_dict = await self._version_to_dict(latest_version)
            raise VersionConflictException(
                "规则已被他人修改，请刷新后重试",
                {"latest_version": latest_version_dict}
            )

        new_md5 = self.calculate_md5(content_json)

        logger.info(
            "MD5 comparison",
            new_md5=new_md5,
            current_md5=current_md5,
            is_same=new_md5 == current_md5
        )

        if latest_version and new_md5 == current_md5:
            logger.warning(
                "NoChangeException triggered - content not changed",
                new_md5=new_md5,
                current_md5=current_md5
            )
            raise NoChangeException("内容未发生变化")

        version_no = (latest_version.version_no + 1) if latest_version else 1

        storage_result = await self._save_content(
            rule.rule_code, version_no, content_json, rule.tenant_id, rule.app_name
        )

        new_version = await RuleVersion.create(
            tenant_id=rule.tenant_id,
            app_name=rule.app_name,
            rule_id=rule.id,
            version_no=version_no,
            content_md5=new_md5,
            storage_type=storage_result["storage_type"],
            content_json=storage_result.get("content_json"),
            file_path=storage_result.get("file_path", ""),
            file_size=storage_result["file_size"],
            remark=remark or "",
            status=1,
            deleted=0
        )

        rule.latest_version_id = new_version.id
        await rule.save()

        logger.info(
            "保存版本成功",
            rule_id=rule.id,
            version_no=version_no,
            storage_type=storage_result["storage_type"]
        )
        return new_version

    async def get_version_history(
        self,
        rule_code: str,
        tenant_id: int = 0,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """获取版本历史"""
        # 使用 tenant_id + rule_code 查询规则
        query = RuleInfo.filter(
            rule_code=rule_code,
            deleted=0
        )
        if tenant_id > 0:
            query = query.filter(tenant_id=tenant_id)
        rule = await query.first()
        if not rule:
            raise ValueError(f"规则不存在: {rule_code}")

        query = RuleVersion.filter(
            rule_id=rule.id,
            deleted=0
        )

        total = await query.count()
        versions = await query.order_by("-version_no").offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        version_list = []
        for v in versions:
            version_list.append({
                "id": v.id,
                "version_no": v.version_no,
                "content_md5": v.content_md5,
                "file_size": v.file_size,
                "remark": v.remark,
                "status": v.status,
                "created_at": v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else ""
            })

        return total, version_list

    async def get_version_by_no(
        self,
        rule_code: str,
        version_no: int,
        tenant_id: int = 0
    ) -> Optional[Dict[str, Any]]:
        """获取指定版本"""
        # 使用 tenant_id + rule_code 查询规则
        query = RuleInfo.filter(
            rule_code=rule_code,
            deleted=0
        )
        if tenant_id > 0:
            query = query.filter(tenant_id=tenant_id)
        rule = await query.first()
        if not rule:
            return None

        version = await RuleVersion.filter(
            rule_id=rule.id,
            version_no=version_no,
            deleted=0
        ).first()

        if not version:
            return None

        return await self._version_to_dict(version)

    async def rollback_version(
        self,
        rule_code: str,
        version_no: int,
        tenant_id: int = 0,
        app_name: str = ""
    ) -> RuleVersion:
        """回滚到指定版本"""
        rule = await self.get_rule_by_code(rule_code, tenant_id, app_name)
        if not rule:
            raise ValueError(f"规则不存在: {rule_code}")

        target_version = await RuleVersion.filter(
            rule_id=rule.id,
            version_no=version_no,
            deleted=0
        ).first()

        if not target_version:
            raise ValueError(f"版本不存在: {version_no}")

        content_json = await self._get_content_json(target_version)
        if not content_json:
            raise ValueError("无法获取版本内容")

        latest_version = await RuleVersion.filter(
            rule_id=rule.id,
            deleted=0
        ).order_by("-version_no").first()

        current_md5 = latest_version.content_md5 if latest_version else ""

        return await self.save_version(
            rule=rule,
            content_json=content_json,
            current_md5=current_md5,
            remark=f"回滚到版本 {version_no}"
        )

    async def update_rule(
        self,
        rule_id: int,
        rule_name: str = None,
        desc: str = None,
        status: int = None,
        tenant_id: int = 0
    ) -> RuleInfo:
        """更新规则信息"""
        # 使用 id + tenant_id 查询规则
        rule = await RuleInfo.filter(
            id=rule_id,
            tenant_id=tenant_id,
            deleted=0
        ).first()
        if not rule:
            raise ValueError(f"规则不存在: {rule_id}")

        if rule_name is not None:
            rule.rule_name = rule_name
        if desc is not None:
            rule.desc = desc
        if status is not None:
            rule.status = status

        await rule.save()

        logger.info("更新规则成功", rule_id=rule.id, rule_code=rule.rule_code)
        return rule

    async def delete_rule(
        self,
        rule_code: str,
        tenant_id: int = 0,
        app_name: str = ""
    ) -> None:
        """删除规则（软删除）"""
        rule = await self.get_rule_by_code(rule_code, tenant_id, app_name)
        if not rule:
            raise ValueError(f"规则不存在: {rule_code}")

        rule.deleted = 1
        rule.deleted_at = datetime.now()
        await rule.save()

        await RuleVersion.filter(
            rule_id=rule.id
        ).update(deleted=1)

        logger.info("删除规则成功", rule_id=rule.id, rule_code=rule_code)

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
        """将JSON转换为CSV格式"""
        output = io.StringIO()
        writer = csv.writer(output)

        headers = content_json.get("headers", [])
        data = content_json.get("data", [])

        writer.writerow(headers)
        writer.writerows(data)

        return output.getvalue()


rule_service = RuleService()
