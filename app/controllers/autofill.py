import logging
from typing import Any, Dict, List, Optional

from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.core.crud import CRUDBase

logger = logging.getLogger(__name__)
from app.models.autofill import (AppManagement, DropdownOption, FieldGroupConfig,
                                 FieldGroupFieldSpec, FieldSpec, FillDataRecord, FillPage,
                                 generate_field_group_code, generate_page_code, SummaryTemplate)
from app.schemas.autofill import (AppCreate, AppUpdate, DropdownOptionCreate,
                                  DropdownOptionUpdate, FillDataRecordCreate,
                                  FillDataRecordUpdate, SummaryTemplateCreate,
                                  SummaryTemplateUpdate)
from app.schemas.fill_page import (FieldGroupConfigCreate, FieldGroupConfigUpdate,
                                   FieldSpecCreate, FieldSpecUpdate, FillPageCreate,
                                   FillPageUpdate, FieldOptions)
from app.services.autofill.field_spec_service import upsert_field_spec


def _convert_corrections_to_list(options: Optional[Dict]) -> Optional[Dict]:
    """将选项中的 corrections 字符串转换为列表格式"""
    if not options or not options.get('items'):
        return options

    for item in options['items']:
        corrections = item.get('corrections')
        if isinstance(corrections, str):
            corrections_str = corrections.strip()
            if corrections_str:
                # 将字符串按换行+*分割转换为列表
                item['corrections'] = [
                    {"text": text.strip()}
                    for text in corrections_str.split('\n*')
                    if text.strip()
                ]
            else:
                item['corrections'] = []
    return options


class AppManagementController(CRUDBase[AppManagement, AppCreate, AppUpdate]):
    def __init__(self):
        super().__init__(model=AppManagement)

    async def create_app(self, obj_in: AppCreate) -> AppManagement:
        # 检查同一租户下应用名称是否已存在
        existing = await self.model.filter(
            tenant_id=obj_in.tenant_id,
            app_name=obj_in.app_name
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该租户下已存在同名应用")
        return await self.create(obj_in)

    async def update_app(self, id: int, obj_in: AppUpdate) -> AppManagement:
        app = await self.get(id=id)
        # 如果修改了 app_name，需要检查唯一性
        if obj_in.app_name and obj_in.app_name != app.app_name:
            existing = await self.model.filter(
                tenant_id=app.tenant_id,
                app_name=obj_in.app_name
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="该租户下已存在同名应用")
        return await self.update(id=id, obj_in=obj_in)


class SummaryTemplateController(CRUDBase[SummaryTemplate, SummaryTemplateCreate, SummaryTemplateUpdate]):
    def __init__(self):
        super().__init__(model=SummaryTemplate)

    async def create_template(self, obj_in: SummaryTemplateCreate) -> SummaryTemplate:
        # 检查唯一性
        existing = await self.model.filter(
            tenant_id=obj_in.tenant_id,
            app_name=obj_in.app_name,
            class_name=obj_in.class_name,
            name=obj_in.name
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该分类下已存在同名模板")
        return await self.create(obj_in)

    async def update_template(self, id: int, obj_in: SummaryTemplateUpdate) -> SummaryTemplate:
        template = await self.get(id=id)
        # 如果修改了关键字段，需要检查唯一性
        if (obj_in.name or obj_in.app_name or obj_in.class_name):
            new_name = obj_in.name or template.name
            new_app_name = obj_in.app_name or template.app_name
            new_class_name = obj_in.class_name or template.class_name

            existing = await self.model.filter(
                tenant_id=template.tenant_id,
                app_name=new_app_name,
                class_name=new_class_name,
                name=new_name
            ).exclude(id=id).first()
            if existing:
                raise HTTPException(status_code=400, detail="该分类下已存在同名模板")
        return await self.update(id=id, obj_in=obj_in)


class DropdownOptionController(CRUDBase[DropdownOption, DropdownOptionCreate, DropdownOptionUpdate]):
    def __init__(self):
        super().__init__(model=DropdownOption)

    async def create_option(self, obj_in: DropdownOptionCreate) -> DropdownOption:
        # 检查唯一性
        existing = await self.model.filter(
            tenant_id=obj_in.tenant_id,
            app_name=obj_in.app_name,
            class_name=obj_in.class_name,
            parent_id=obj_in.parent_id,
            option_value=obj_in.option_value
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该父选项下已存在同名选项值")
        return await self.create(obj_in)

    async def update_option(self, id: int, obj_in: DropdownOptionUpdate) -> DropdownOption:
        option = await self.get(id=id)
        # 如果修改了关键字段，需要检查唯一性
        if (obj_in.option_value or obj_in.app_name or obj_in.class_name or obj_in.parent_id is not None):
            new_option_value = obj_in.option_value or option.option_value
            new_app_name = obj_in.app_name or option.app_name
            new_class_name = obj_in.class_name or option.class_name
            new_parent_id = obj_in.parent_id if obj_in.parent_id is not None else option.parent_id

            existing = await self.model.filter(
                tenant_id=option.tenant_id,
                app_name=new_app_name,
                class_name=new_class_name,
                parent_id=new_parent_id,
                option_value=new_option_value
            ).exclude(id=id).first()
            if existing:
                raise HTTPException(status_code=400, detail="该父选项下已存在同名选项值")
        return await self.update(id=id, obj_in=obj_in)

    async def get_tree(self, tenant_id: int, app_name: str, parent_id: int = 0, class_name: str = "", is_superuser: bool = False) -> List[Dict[str, Any]]:
        """获取树形结构的下拉选项"""
        query = Q(
            app_name=app_name,
            parent_id=parent_id
        )
        # 非超级用户只能查看指定租户的数据
        if not is_superuser:
            query &= Q(tenant_id=tenant_id)
        elif tenant_id > 0:
            # 超级用户指定了租户ID，优先使用该租户
            query &= Q(tenant_id=tenant_id)
        # 超级用户未指定租户ID，查询所有租户

        if class_name:
            query &= Q(class_name=class_name)

        options = await self.model.filter(query).all()

        result = []
        for opt in options:
            opt_dict = await opt.to_dict()
            # 递归获取子选项
            children = await self.get_tree(tenant_id, app_name, opt.id, class_name, is_superuser)
            if children:
                opt_dict["children"] = children
            result.append(opt_dict)
        return result


class FillDataRecordController(CRUDBase[FillDataRecord, FillDataRecordCreate, FillDataRecordUpdate]):
    def __init__(self):
        super().__init__(model=FillDataRecord)

    async def record_fill_data(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str,
        data: Optional[Dict[str, Any]] = None,
        phone: Optional[str] = None,
        user_unique_id: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> FillDataRecord:
        """记录填单数据，支持数据合并"""
        # 查询现有记录
        record = await self.model.filter(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name
        ).first()

        if record:
            # 合并数据: 传入数据覆盖旧数据
            existing_data = record.data or {}
            new_data = data or {}
            merged_data = {**existing_data, **new_data}

            record.data = merged_data
            if phone:
                record.phone = phone
            if user_unique_id:
                record.user_unique_id = user_unique_id
            if user_name:
                record.user_name = user_name
            await record.save()
        else:
            # 创建新记录
            record = await self.model.create(
                session_id=session_id,
                phone=phone or "",
                user_unique_id=user_unique_id or "",
                user_name=user_name or "",
                app_name=app_name,
                tenant_id=tenant_id,
                data=data or {}
            )

        return record

    async def save_original_data(
        self,
        session_id: str,
        tenant_id: int,
        app_name: str,
        data: Dict[str, Any]
    ) -> FillDataRecord:
        """存储原始数据，包装为 {original_data: {...}}"""
        record = await self.model.filter(
            session_id=session_id,
            tenant_id=tenant_id,
            app_name=app_name
        ).first()

        wrapped_data = {"original_data": data}

        if record:
            existing = record.data or {}
            existing["original_data"] = data
            record.data = existing
            await record.save()
        else:
            record = await self.model.create(
                session_id=session_id,
                app_name=app_name,
                tenant_id=tenant_id,
                data=wrapped_data
            )

        return record


# ==================== 新增控制器 ====================

class FillPageController(CRUDBase[FillPage, FillPageCreate, FillPageUpdate]):
    """填单页面控制器"""
    def __init__(self):
        super().__init__(model=FillPage)

    async def create_page(self, obj_in: FillPageCreate) -> FillPage:
        """创建页面，检查同一应用下页面编码唯一性"""
        # 如果 page_code 为空，则自动生成
        if not obj_in.page_code:
            obj_in.page_code = generate_page_code()

        existing = await self.model.filter(
            app_id=obj_in.app_id,
            page_code=obj_in.page_code
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该应用下已存在同编码页面")
        return await self.create(obj_in)

    async def update_page(self, id: int, obj_in: FillPageUpdate) -> FillPage:
        """更新页面，检查编码唯一性"""
        page = await self.get(id=id)
        if obj_in.page_code and obj_in.page_code != page.page_code:
            existing = await self.model.filter(
                app_id=page.app_id,
                page_code=obj_in.page_code
            ).exclude(id=id).first()
            if existing:
                raise HTTPException(status_code=400, detail="该应用下已存在同编码页面")
        return await self.update(id=id, obj_in=obj_in)


class FieldGroupConfigController(CRUDBase[FieldGroupConfig, FieldGroupConfigCreate, FieldGroupConfigUpdate]):
    """字段组配置控制器"""
    def __init__(self):
        super().__init__(model=FieldGroupConfig)

    async def create_field_group(self, obj_in: FieldGroupConfigCreate) -> FieldGroupConfig:
        """创建字段组，检查同一页面下字段组名称唯一性，自动生成编码"""
        # 如果 group_code 为空，则自动生成
        if not obj_in.group_code:
            obj_in.group_code = generate_field_group_code()

        existing = await self.model.filter(
            page_id=obj_in.page_id,
            group_name=obj_in.group_name
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该页面下已存在同名字段组")
        return await self.create(obj_in)

    async def update_field_group(self, id: int, obj_in: FieldGroupConfigUpdate) -> FieldGroupConfig:
        """更新字段组，检查名称唯一性，自动增加版本号"""
        field_group = await self.get(id=id)

        # 检查名称唯一性
        if obj_in.group_name and obj_in.group_name != field_group.group_name:
            existing = await self.model.filter(
                page_id=field_group.page_id,
                group_name=obj_in.group_name
            ).exclude(id=id).first()
            if existing:
                raise HTTPException(status_code=400, detail="该页面下已存在同名字段组")

        # 如果更新了关键配置，增加版本号
        update_data = obj_in.model_dump(exclude_unset=True)
        if (obj_in.prompt_template_base is not None or
            obj_in.output_templates is not None or
            obj_in.group_name is not None):
            update_data['version'] = field_group.version + 1

        return await self.update(id=id, obj_in=update_data)

    async def get_by_code(self, code: str) -> Optional[FieldGroupConfig]:
        """通过唯一编码获取字段组配置"""
        return await self.model.filter(group_code=code).first()


class FieldSpecController(CRUDBase[FieldSpec, FieldSpecCreate, FieldSpecUpdate]):
    """字段明细控制器（多对多关联字段组）"""
    def __init__(self):
        super().__init__(model=FieldSpec)

    async def create_field_spec(self, obj_in: FieldSpecCreate, tenant_id: int = 0, app_name: str = "", sync_mode: str = "merge") -> FieldSpec:
        """
        创建或更新字段明细（Upsert模式）
        根据 field_name + tenant_id + app_name 唯一确定一个字段

        Args:
            obj_in: 字段创建数据
            tenant_id: 租户ID
            app_name: 应用名称
            sync_mode: 同步模式，仅支持merge=合并（新值非空时更新，否则保留原值）

        Returns:
            FieldSpec: 创建或更新后的字段对象
        """
        # 处理选项中的 corrections 字段
        options = _convert_corrections_to_list(obj_in.options.model_dump() if obj_in.options else {})

        # 复用 service 层的 upsert_field_spec 逻辑
        result = await upsert_field_spec(
            tenant_id=tenant_id,
            app_name=app_name,
            field_name=obj_in.field_name,
            field_label=obj_in.field_label,
            field_type=obj_in.field_type.value if hasattr(obj_in.field_type, 'value') else str(obj_in.field_type),
            field_group_ids=obj_in.field_group_ids or [],
            fill_instruction=obj_in.fill_instruction or "",
            options=options if options else None
        )

        return result["field_spec"]

    async def update_field_spec(self, id: int, obj_in: FieldSpecUpdate, tenant_id: int = 0, app_name: str = "", merge_groups: bool = True, merge_options: bool = True) -> FieldSpec:
        """
        更新字段明细，支持 merge 模式

        Args:
            id: 字段ID
            obj_in: 更新数据
            tenant_id: 租户ID
            app_name: 应用名称
            merge_groups: 是否合并字段组关联（True=合并，False=替换）
            merge_options: 是否合并选项（True=合并保留原有属性，False=完全替换）
        """
        field_spec = await self.get(id=id)

        # 检查字段名唯一性（在同一租户+应用下）
        if obj_in.field_name and obj_in.field_name != field_spec.field_name:
            existing = await self.model.filter(
                tenant_id=field_spec.tenant_id,
                app_name=field_spec.app_name,
                field_name=obj_in.field_name
            ).exclude(id=id).first()
            if existing:
                raise HTTPException(status_code=400, detail="该应用下已存在同名字段")

        # 处理选项中的 corrections 字段
        options = _convert_corrections_to_list(obj_in.options.model_dump() if obj_in.options else None)

        # 复用 service 层的 upsert_field_spec 逻辑
        result = await upsert_field_spec(
            tenant_id=field_spec.tenant_id,
            app_name=field_spec.app_name,
            field_name=field_spec.field_name,
            field_label=obj_in.field_label or field_spec.field_label,
            field_type=obj_in.field_type.value if hasattr(obj_in.field_type, 'value') else str(obj_in.field_type or field_spec.field_type),
            field_group_ids=obj_in.field_group_ids or [],
            fill_instruction=obj_in.fill_instruction or field_spec.fill_instruction or "",
            options=options
        )

        return result["field_spec"]

    async def get_by_field_group(self, field_group_id: int, active_only: bool = True) -> List[FieldSpec]:
        """获取字段组下的所有字段明细（通过中间表）

        Args:
            field_group_id: 字段组ID
            active_only: 是否只查询启用的字段，默认为True
        """
        # 通过中间表查询关联的字段ID
        relations = await FieldGroupFieldSpec.filter(field_group_id=field_group_id).all()
        field_spec_ids = [r.field_spec_id for r in relations]

        if not field_spec_ids:
            return []

        if active_only:
            return await self.model.filter(id__in=field_spec_ids, is_active=True).all()
        else:
            return await self.model.filter(id__in=field_spec_ids).all()

    async def get_field_groups(self, field_spec_id: int) -> List[FieldGroupConfig]:
        """获取字段关联的所有字段组"""
        relations = await FieldGroupFieldSpec.filter(field_spec_id=field_spec_id).all()
        group_ids = [r.field_group_id for r in relations]

        if not group_ids:
            return []

        return await FieldGroupConfig.filter(id__in=group_ids).all()

    async def delete_field_spec(self, id: int) -> None:
        """删除字段及其关联关系"""
        # 删除中间表关联
        await FieldGroupFieldSpec.filter(field_spec_id=id).delete()
        # 删除字段
        await self.remove(id=id)


# 实例化控制器
app_management_controller = AppManagementController()
summary_template_controller = SummaryTemplateController()
dropdown_option_controller = DropdownOptionController()
fill_data_record_controller = FillDataRecordController()
fill_page_controller = FillPageController()
field_group_config_controller = FieldGroupConfigController()
field_spec_controller = FieldSpecController()
