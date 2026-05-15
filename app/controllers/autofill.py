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
            sync_mode: 同步模式，merge=合并（保留人工标注），replace=替换
        
        Returns:
            FieldSpec: 创建或更新后的字段对象
        """
        # 查找现有字段
        existing = await self.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            field_name=obj_in.field_name
        ).first()
        
        # 处理选项中的 corrections 字段 - 将字符串转换为列表格式
        spec_data = obj_in.model_dump(exclude={'field_group_ids'})
        if spec_data.get('options') and spec_data['options'].get('items'):
            for item in spec_data['options']['items']:
                if 'corrections' in item and isinstance(item['corrections'], str):
                    corrections_str = item['corrections'].strip()
                    if corrections_str:
                        # 将字符串按换行+*分割转换为列表
                        corrections_list = []
                        for text in corrections_str.split('\n*'):
                            text = text.strip()
                            if text:
                                corrections_list.append({"text": text})
                        item['corrections'] = corrections_list
                    else:
                        item['corrections'] = []
        
        if existing:
            # 字段已存在，执行更新（Upsert逻辑）
            logger.info(f"[FieldSpecController] 字段已存在，执行更新: {obj_in.field_name}")
            
            # 根据sync_mode处理选项
            existing_options = existing.options or {}
            existing_items = existing_options.get('items', []) if isinstance(existing_options, dict) else []
            new_items = spec_data.get('options', {}).get('items', [])
            
            if sync_mode == 'replace':
                # replace模式：替换选项，但保留相同选项的fill_instruction和corrections
                existing_items_map = {item['label']: item for item in existing_items if isinstance(item, dict) and 'label' in item}
                final_items = []
                for new_item in new_items:
                    label = new_item['label']
                    if label in existing_items_map:
                        # 保留原有fill_instruction和corrections，更新其他字段
                        existing_item = existing_items_map[label]
                        merged_item = {**new_item}
                        if 'fill_instruction' in existing_item:
                            merged_item['fill_instruction'] = existing_item['fill_instruction']
                        if 'corrections' in existing_item:
                            merged_item['corrections'] = existing_item['corrections']
                        final_items.append(merged_item)
                    else:
                        final_items.append(new_item)
            else:
                # merge模式（默认）：合并现有选项和新选项，保留已有选项的fill_instruction和corrections
                merged_items_map = {}
                for item in existing_items:
                    if isinstance(item, dict) and 'label' in item:
                        merged_items_map[item['label']] = item
                
                for new_item in new_items:
                    label = new_item['label']
                    if label in merged_items_map:
                        # 保留原有fill_instruction和corrections，只更新value
                        merged_items_map[label]['value'] = new_item['value']
                    else:
                        merged_items_map[label] = new_item
                
                final_items = list(merged_items_map.values())
            
            # 更新选项数据
            spec_data['options']['items'] = final_items
            
            # 获取当前所有关联的字段组ID
            existing_relations = await FieldGroupFieldSpec.filter(field_spec_id=existing.id).all()
            existing_group_ids = [r.field_group_id for r in existing_relations]
            
            # 合并字段组ID（去重）
            new_group_ids = obj_in.field_group_ids or []
            all_group_ids = list(set(existing_group_ids + new_group_ids))
            
            # 更新字段
            update_data = FieldSpecUpdate(
                id=existing.id,
                field_label=spec_data.get('field_label', existing.field_label),
                field_type=spec_data.get('field_type', existing.field_type),
                fill_instruction=spec_data.get('fill_instruction', existing.fill_instruction),
                field_group_ids=all_group_ids,
                options=FieldOptions(**spec_data['options']) if spec_data.get('options') else existing.options,
                is_active=spec_data.get('is_active', existing.is_active)
            )
            
            return await self.update_field_spec(
                id=existing.id,
                obj_in=update_data,
                tenant_id=tenant_id,
                app_name=app_name,
                merge_groups=True,
                merge_options=sync_mode == 'merge'
            )
        else:
            # 字段不存在，创建新字段
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

        # 更新字段基本信息（不包含关联关系）
        update_data = obj_in.model_dump(exclude={'field_group_ids'}, exclude_unset=True)
        
        # 处理选项 merge 逻辑
        if merge_options and update_data.get('options') and update_data['options'].get('items'):
            existing_options = field_spec.options or {}
            existing_items = existing_options.get('items', []) if isinstance(existing_options, dict) else []
            new_items = update_data['options']['items']
            
            # Merge 模式：保留现有选项的 fill_instruction 和 corrections
            merged_items_map = {}
            for item in existing_items:
                if isinstance(item, dict) and 'label' in item:
                    merged_items_map[item['label']] = item
            
            for new_item in new_items:
                label = new_item['label']
                if label in merged_items_map:
                    # 保留原有 fill_instruction 和 corrections，更新 value 和 label
                    existing_item = merged_items_map[label]
                    existing_item['value'] = new_item['value']
                    existing_item['label'] = new_item['label']
                else:
                    merged_items_map[label] = new_item
            
            update_data['options']['items'] = list(merged_items_map.values())
        
        # 处理选项中的 corrections 字段 - 将字符串转换为列表格式
        if update_data.get('options') and update_data['options'].get('items'):
            for item in update_data['options']['items']:
                if 'corrections' in item and isinstance(item['corrections'], str):
                    corrections_str = item['corrections'].strip()
                    if corrections_str:
                        # 将字符串按换行+*分割转换为列表
                        corrections_list = []
                        for text in corrections_str.split('\n*'):
                            text = text.strip()
                            if text:
                                corrections_list.append({"text": text})
                        item['corrections'] = corrections_list
                    else:
                        item['corrections'] = []
        
        field_spec = await self.update(id=id, obj_in=update_data)

        # 更新关联关系
        if obj_in.field_group_ids is not None:
            if merge_groups:
                # Merge 模式：合并现有和新的字段组关联
                existing_relations = await FieldGroupFieldSpec.filter(field_spec_id=id).all()
                existing_group_ids = [r.field_group_id for r in existing_relations]
                new_group_ids = obj_in.field_group_ids
                all_group_ids = list(set(existing_group_ids + new_group_ids))
                
                # 删除旧关联
                await FieldGroupFieldSpec.filter(field_spec_id=id).delete()
                # 创建合并后的关联
                for group_id in all_group_ids:
                    await FieldGroupFieldSpec.create(
                        field_group_id=group_id,
                        field_spec_id=id,
                        tenant_id=field_spec.tenant_id,
                        app_name=field_spec.app_name
                    )
            else:
                # 替换模式：删除旧关联，创建新关联
                await FieldGroupFieldSpec.filter(field_spec_id=id).delete()
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
