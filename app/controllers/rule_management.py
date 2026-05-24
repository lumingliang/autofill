"""
规则管理控制器
"""
from typing import Any, Dict, List, Optional, Tuple

from app.core.crud import CRUDBase
from app.models.rule_management import RuleInfo, RuleVersion
from app.schemas.rule_management import RuleCreate, RuleUpdate
from app.services.rule_management.rule_service import rule_service


class RuleInfoController(CRUDBase[RuleInfo, RuleCreate, RuleUpdate]):
    """规则信息控制器"""

    def __init__(self):
        super().__init__(model=RuleInfo)

    async def create_rule(
        self,
        obj_in: RuleCreate,
        tenant_id: int = 0,
        app_name: str = ""
    ) -> RuleInfo:
        """创建规则"""
        return await rule_service.create_rule(
            rule_name=obj_in.rule_name,
            desc=obj_in.desc,
            rule_code=obj_in.rule_code,
            tenant_id=tenant_id,
            app_name=app_name
        )

    async def update_rule(
        self,
        rule_id: int,
        obj_in: RuleUpdate,
        tenant_id: int = 0
    ) -> RuleInfo:
        """更新规则"""
        return await rule_service.update_rule(
            rule_id=rule_id,
            rule_name=obj_in.rule_name,
            desc=obj_in.desc,
            status=obj_in.status,
            tenant_id=tenant_id
        )

    async def delete_rule(
        self,
        rule_code: str,
        tenant_id: int = 0,
        app_name: str = ""
    ) -> None:
        """删除规则"""
        await rule_service.delete_rule(
            rule_code=rule_code,
            tenant_id=tenant_id,
            app_name=app_name
        )

    async def get_rule_by_code(
        self,
        rule_code: str,
        tenant_id: int = 0,
        app_name: str = ""
    ) -> Optional[RuleInfo]:
        """根据编码获取规则"""
        return await rule_service.get_rule_by_code(
            rule_code=rule_code,
            tenant_id=tenant_id,
            app_name=app_name
        )

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
        return await rule_service.list_rules(
            tenant_id=tenant_id,
            app_name=app_name,
            keyword=keyword,
            status=status,
            page=page,
            page_size=page_size
        )

    async def get_rule_detail(
        self,
        rule_code: str,
        tenant_id: int = 0,
        app_name: str = ""
    ) -> Optional[Dict[str, Any]]:
        """获取规则详情"""
        return await rule_service.get_rule_detail(
            rule_code=rule_code,
            tenant_id=tenant_id,
            app_name=app_name
        )


class RuleVersionController:
    """规则版本控制器"""

    async def save_version(
        self,
        rule: RuleInfo,
        content_json: Dict[str, Any],
        current_md5: str,
        remark: str = ""
    ) -> RuleVersion:
        """保存版本"""
        return await rule_service.save_version(
            rule=rule,
            content_json=content_json,
            current_md5=current_md5,
            remark=remark
        )

    async def get_version_history(
        self,
        rule_code: str,
        tenant_id: int = 0,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """获取版本历史"""
        return await rule_service.get_version_history(
            rule_code=rule_code,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size
        )

    async def get_version_by_no(
        self,
        rule_code: str,
        version_no: int,
        tenant_id: int = 0
    ) -> Optional[Dict[str, Any]]:
        """获取指定版本"""
        return await rule_service.get_version_by_no(
            rule_code=rule_code,
            version_no=version_no,
            tenant_id=tenant_id
        )

    async def rollback_version(
        self,
        rule_code: str,
        version_no: int,
        tenant_id: int = 0,
        app_name: str = ""
    ) -> RuleVersion:
        """回滚版本"""
        return await rule_service.rollback_version(
            rule_code=rule_code,
            version_no=version_no,
            tenant_id=tenant_id,
            app_name=app_name
        )


# 创建控制器实例
rule_info_controller = RuleInfoController()
rule_version_controller = RuleVersionController()
