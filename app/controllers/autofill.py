from typing import Any, Dict, List, Optional

from fastapi.exceptions import HTTPException
from tortoise.expressions import Q

from app.core.crud import CRUDBase
from app.models.autofill import (AppManagement, DropdownOption, FieldGroupConfig,
                                 FieldGroupFieldSpec, FieldSpec, FillDataRecord, FillPage, SummaryTemplate)
from app.schemas.autofill import (AppCreate, AppUpdate, DropdownOptionCreate,
                                  DropdownOptionUpdate, FillDataRecordCreate,
                                  FillDataRecordUpdate, SummaryTemplateCreate,
                                  SummaryTemplateUpdate)
from app.schemas.fill_page import (FieldGroupConfigCreate, FieldGroupConfigUpdate,
                                   FieldSpecCreate, FieldSpecUpdate, FillPageCreate,
                                   FillPageUpdate)


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

    async def get_tree(self, tenant_id: int, app_name: str, parent_id: int = 0, class_name: str = "") -> List[Dict[str, Any]]:
        """获取树形结构的下拉选项"""
        query = Q(
            tenant_id=tenant_id,
            app_name=app_name,
            parent_id=parent_id
        )
        if class_name:
            query &= Q(class_name=class_name)

        options = await self.model.filter(query).all()

        result = []
        for opt in options:
            opt_dict = await opt.to_dict()
            # 递归获取子选项
            children = await self.get_tree(tenant_id, app_name, opt.id, class_name)
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
            from app.models.autofill import generate_page_code
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
            from app.models.autofill import generate_field_group_code
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

    async def create_field_spec(self, obj_in: FieldSpecCreate, tenant_id: int = 0, app_name: str = "") -> FieldSpec:
        """创建字段明细，检查同一租户+应用下字段名唯一性"""
        existing = await self.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            field_name=obj_in.field_name
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该应用下已存在同名字段")

        # 创建字段（不包含关联关系）
        spec_data = obj_in.model_dump(exclude={'field_group_ids'})
        spec_data['tenant_id'] = tenant_id
        spec_data['app_name'] = app_name
        field_spec = await self.create(spec_data)

        # 创建关联关系
        if obj_in.field_group_ids:
            for group_id in obj_in.field_group_ids:
                await FieldGroupFieldSpec.create(
                    field_group_id=group_id,
                    field_spec_id=field_spec.id,
                    tenant_id=tenant_id,
                    app_name=app_name
                )

        return field_spec

    async def update_field_spec(self, id: int, obj_in: FieldSpecUpdate, tenant_id: int = 0, app_name: str = "") -> FieldSpec:
        """更新字段明细，检查字段名唯一性，更新关联关系"""
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

        # 更新字段基本信息（不包含关联关系）
        update_data = obj_in.model_dump(exclude={'field_group_ids'}, exclude_unset=True)
        field_spec = await self.update(id=id, obj_in=update_data)

        # 更新关联关系
        if obj_in.field_group_ids is not None:
            # 删除旧关联
            await FieldGroupFieldSpec.filter(field_spec_id=id).delete()
            # 创建新关联
            for group_id in obj_in.field_group_ids:
                await FieldGroupFieldSpec.create(
                    field_group_id=group_id,
                    field_spec_id=id,
                    tenant_id=field_spec.tenant_id,
                    app_name=field_spec.app_name
                )

        return field_spec

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
