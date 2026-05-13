"""
下拉选项管理接口
"""
import csv
import io

from fastapi import APIRouter, File, Header, Query, UploadFile
from tortoise.expressions import Q

from app.controllers.autofill import (
    app_management_controller,
    dropdown_option_controller,
)
from app.core.dependency import AuthControl, is_superuser, build_tenant_query
from app.schemas.autofill import DropdownOptionCreate, DropdownOptionUpdate
from app.schemas.base import Fail, Success, SuccessExtra

router = APIRouter()


@router.get("/dropdown/list", summary="下拉选项列表")
async def list_dropdown(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    app_name: str = Query("", description="应用名称"),
    class_name: str = Query("", description="分类名称"),
    parent_id: int = Query(0, description="父选项ID"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    q = Q()
    if app_name:
        q &= Q(app_name__contains=app_name)
    if class_name:
        q &= Q(class_name__contains=class_name)
    if parent_id >= 0:
        q &= Q(parent_id=parent_id)

    tenant_query = build_tenant_query(current_user, tenant_id)
    if tenant_query["tenant_id"] > 0:
        q &= Q(tenant_id=tenant_query["tenant_id"])

    total, options = await dropdown_option_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict() for obj in options]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/dropdown/tree", summary="下拉选项树形结构")
async def get_dropdown_tree(
    app_name: str = Query(..., description="应用名称"),
    class_name: str = Query("", description="分类名称"),
    parent_id: int = Query(0, description="父选项ID"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 非超级用户必须指定租户ID
    if not is_superuser(current_user):
        effective_tenant_id = tenant_id
        if effective_tenant_id <= 0:
            effective_tenant_id = current_user.current_tenant_id
        if effective_tenant_id <= 0:
            return Fail(code=400, msg="请指定租户ID")
    else:
        # 超级用户使用传入的tenant_id（可能为0，表示查询所有）
        effective_tenant_id = tenant_id

    tree = await dropdown_option_controller.get_tree(
        effective_tenant_id, app_name, parent_id, class_name,
        is_superuser=is_superuser(current_user)
    )
    return Success(data=tree)


@router.get("/dropdown/classes", summary="获取应用下的分类列表")
async def get_dropdown_classes(
    app_name: str = Query(..., description="应用名称"),
    tenant_id: int = Query(0, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    # 构建查询条件
    query = Q(app_name=app_name)
    
    # 非超级用户只能查看自己租户的数据
    if not is_superuser(current_user):
        effective_tenant_id = tenant_id
        if effective_tenant_id <= 0:
            effective_tenant_id = current_user.current_tenant_id
        if effective_tenant_id <= 0:
            return Fail(code=400, msg="请指定租户ID")
        query &= Q(tenant_id=effective_tenant_id)
    elif tenant_id > 0:
        # 超级用户明确指定了租户ID，才使用该租户过滤
        query &= Q(tenant_id=tenant_id)
    # 超级用户未指定租户ID，查询所有租户

    options = await dropdown_option_controller.model.filter(
        query
    ).distinct().values("class_name")

    class_names = [opt["class_name"] for opt in options if opt["class_name"]]
    return Success(data=class_names)


@router.get("/dropdown/get", summary="下拉选项详情")
async def get_dropdown(
    id: int = Query(..., description="选项ID"),
    token: str = Header(..., description="token验证"),
):
    await AuthControl.is_authed(token)
    option = await dropdown_option_controller.get(id=id)
    data = await option.to_dict()

    children = await dropdown_option_controller.model.filter(parent_id=id).all()
    data["children"] = [await child.to_dict() for child in children]

    return Success(data=data)


@router.post("/dropdown/create", summary="创建下拉选项")
async def create_dropdown(
    option_in: DropdownOptionCreate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)

    target_tenant_id = 0
    if is_superuser(current_user):
        if option_in.tenant_id and option_in.tenant_id > 0:
            target_tenant_id = option_in.tenant_id
        elif option_in.app_name:
            app = await app_management_controller.model.filter(app_name=option_in.app_name).first()
            if app:
                target_tenant_id = app.tenant_id
            else:
                return Fail(code=400, msg=f"应用 '{option_in.app_name}' 不存在")
        else:
            return Fail(code=400, msg="请指定租户ID或应用名称")
    else:
        target_tenant_id = current_user.current_tenant_id
        if target_tenant_id <= 0:
            return Fail(code=400, msg="您当前未选择租户，无法创建选项")

    option_in.tenant_id = target_tenant_id
    option = await dropdown_option_controller.create_option(obj_in=option_in)
    return Success(data=await option.to_dict())


@router.post("/dropdown/update", summary="更新下拉选项")
async def update_dropdown(
    option_in: DropdownOptionUpdate,
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    option = await dropdown_option_controller.get(id=option_in.id)

    if not is_superuser(current_user):
        if option.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的选项")

    updated = await dropdown_option_controller.update_option(id=option_in.id, obj_in=option_in)
    return Success(data=await updated.to_dict())


@router.delete("/dropdown/delete", summary="删除下拉选项")
async def delete_dropdown(
    id: int = Query(..., description="选项ID"),
    token: str = Header(..., description="token验证"),
):
    current_user = await AuthControl.is_authed(token)
    option = await dropdown_option_controller.get(id=id)

    if not is_superuser(current_user):
        if option.tenant_id != current_user.current_tenant_id:
            return Fail(code=403, msg="无权操作其他租户的选项")

    children_count = await dropdown_option_controller.model.filter(parent_id=id).count()
    if children_count > 0:
        return Fail(code=400, msg="该选项下有子选项，请先删除子选项")

    await dropdown_option_controller.remove(id=id)
    return Success(msg="删除成功")


@router.post("/dropdown/import", summary="CSV批量导入下拉选项")
async def import_dropdown_from_csv(
    file: UploadFile = File(..., description="CSV文件"),
    app_name: str = Query(..., description="应用名称"),
    tenant_id: int = Query(None, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """
    CSV格式: option_value,summary,class_name,parent_option_value
    """
    current_user = await AuthControl.is_authed(token)

    target_tenant_id = tenant_id
    if is_superuser(current_user):
        if target_tenant_id and target_tenant_id > 0:
            target_tenant_id = target_tenant_id
        elif app_name:
            app = await app_management_controller.model.filter(app_name=app_name).first()
            if app:
                target_tenant_id = app.tenant_id
            else:
                return Fail(code=400, msg=f"应用 '{app_name}' 不存在")
        else:
            return Fail(code=400, msg="请指定租户ID或应用名称")
    else:
        target_tenant_id = current_user.current_tenant_id
        if target_tenant_id <= 0:
            return Fail(code=400, msg="您当前未选择租户")

    if not file.filename.endswith('.csv'):
        return Fail(code=400, msg="请上传CSV文件")

    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content_str))

        required_fields = ['option_value', 'class_name']
        if not csv_reader.fieldnames:
            return Fail(code=400, msg="CSV文件格式错误：无法读取表头")

        for field in required_fields:
            if field not in csv_reader.fieldnames:
                return Fail(code=400, msg=f"CSV文件缺少必填字段: {field}")

        rows = list(csv_reader)
        created_count = 0
        updated_count = 0
        errors = []
        value_to_id = {}

        for idx, row in enumerate(rows, start=2):
            try:
                option_value = row.get('option_value', '').strip()
                class_name = row.get('class_name', '').strip()

                if not option_value:
                    errors.append(f"第{idx}行: 选项值不能为空")
                    continue
                if not class_name:
                    errors.append(f"第{idx}行: 分类名称不能为空")
                    continue

                summary = row.get('summary', '').strip()

                existing = await dropdown_option_controller.model.filter(
                    tenant_id=target_tenant_id,
                    app_name=app_name,
                    class_name=class_name,
                    option_value=option_value
                ).first()

                if existing:
                    existing.summary = summary
                    existing.parent_id = 0
                    await existing.save()
                    value_to_id[option_value] = existing.id
                    updated_count += 1
                else:
                    option = await dropdown_option_controller.model.create(
                        tenant_id=target_tenant_id,
                        app_name=app_name,
                        class_name=class_name,
                        option_value=option_value,
                        summary=summary,
                        parent_id=0,
                        description=''
                    )
                    value_to_id[option_value] = option.id
                    created_count += 1

            except Exception as e:
                errors.append(f"第{idx}行: {str(e)}")

        for idx, row in enumerate(rows, start=2):
            try:
                option_value = row.get('option_value', '').strip()
                parent_option_value = row.get('parent_option_value', '').strip()

                if not option_value or not parent_option_value:
                    continue

                option = await dropdown_option_controller.model.filter(
                    tenant_id=target_tenant_id,
                    app_name=app_name,
                    option_value=option_value
                ).first()

                if option and parent_option_value in value_to_id:
                    option.parent_id = value_to_id[parent_option_value]
                    await option.save()
                elif option:
                    parent = await dropdown_option_controller.model.filter(
                        tenant_id=target_tenant_id,
                        app_name=app_name,
                        option_value=parent_option_value
                    ).first()
                    if parent:
                        option.parent_id = parent.id
                        await option.save()

            except Exception as e:
                errors.append(f"第{idx}行更新父子关系失败: {str(e)}")

        result = {
            "created": created_count,
            "updated": updated_count,
            "total": len(rows),
            "errors": errors
        }

        if errors:
            return Success(data=result, msg=f"导入完成，但有{len(errors)}个错误")
        return Success(data=result, msg="导入成功")

    except Exception as e:
        return Fail(code=500, msg=f"导入失败: {str(e)}")


@router.post("/dropdown/preview-csv", summary="预览CSV文件结构")
async def preview_csv_structure(
    file: UploadFile = File(..., description="CSV文件"),
    token: str = Header(..., description="token验证"),
):
    """
    预览CSV文件，返回表头字段列表和样例数据
    """
    await AuthControl.is_authed(token)

    if not file.filename.endswith('.csv'):
        return Fail(code=400, msg="请上传CSV文件")

    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content_str))

        if not csv_reader.fieldnames:
            return Fail(code=400, msg="CSV文件格式错误：无法读取表头")

        fieldnames = list(csv_reader.fieldnames)
        rows = list(csv_reader)

        # 返回前3行样例数据
        sample_data = rows[:3] if rows else []

        # 智能识别可能的字段映射
        suggested_mapping = {
            "level1_name": None,
            "level1_id": None,
            "level1_desc": None,
            "level2_name": None,
            "level2_id": None,
            "level2_desc": None,
            "level3_name": None,
            "level3_id": None,
            "level3_desc": None,
        }

        for field in fieldnames:
            field_lower = field.lower()
            # 一级字段识别
            if any(k in field_lower for k in ['一级', 'level1', 'level_1']):
                if any(k in field_lower for k in ['id', '标识', '编码']):
                    suggested_mapping["level1_id"] = field
                elif any(k in field_lower for k in ['说明', '描述', 'desc', 'description']):
                    suggested_mapping["level1_desc"] = field
                else:
                    suggested_mapping["level1_name"] = field
            # 二级字段识别
            elif any(k in field_lower for k in ['二级', 'level2', 'level_2']):
                if any(k in field_lower for k in ['id', '标识', '编码']):
                    suggested_mapping["level2_id"] = field
                elif any(k in field_lower for k in ['说明', '描述', 'desc', 'description']):
                    suggested_mapping["level2_desc"] = field
                else:
                    suggested_mapping["level2_name"] = field
            # 三级字段识别
            elif any(k in field_lower for k in ['三级', 'level3', 'level_3']):
                if any(k in field_lower for k in ['id', '标识', '编码']):
                    suggested_mapping["level3_id"] = field
                elif any(k in field_lower for k in ['说明', '描述', 'desc', 'description']):
                    suggested_mapping["level3_desc"] = field
                else:
                    suggested_mapping["level3_name"] = field

        return Success(data={
            "fields": fieldnames,
            "sample_data": sample_data,
            "suggested_mapping": suggested_mapping,
            "total_rows": len(rows)
        })

    except Exception as e:
        return Fail(code=500, msg=f"解析CSV失败: {str(e)}")


@router.post("/dropdown/import-hierarchical", summary="CSV批量导入层级下拉选项")
async def import_hierarchical_dropdown_from_csv(
    file: UploadFile = File(..., description="CSV文件"),
    app_name: str = Query(..., description="应用名称"),
    class_name: str = Query("事件类型", description="分类名称"),
    level1_name_field: str = Query(..., description="一级名称字段"),
    level1_id_field: str = Query(..., description="一级ID字段"),
    level1_desc_field: str = Query("", description="一级说明字段"),
    level2_name_field: str = Query("", description="二级名称字段"),
    level2_id_field: str = Query("", description="二级ID字段"),
    level2_desc_field: str = Query("", description="二级说明字段"),
    level3_name_field: str = Query("", description="三级名称字段"),
    level3_id_field: str = Query("", description="三级ID字段"),
    level3_desc_field: str = Query("", description="三级说明字段"),
    tenant_id: int = Query(None, description="租户ID"),
    token: str = Header(..., description="token验证"),
):
    """
    三级下拉选项CSV导入，支持自定义字段映射
    """
    current_user = await AuthControl.is_authed(token)

    target_tenant_id = tenant_id
    if is_superuser(current_user):
        if target_tenant_id and target_tenant_id > 0:
            target_tenant_id = target_tenant_id
        elif app_name:
            app = await app_management_controller.model.filter(app_name=app_name).first()
            if app:
                target_tenant_id = app.tenant_id
            else:
                return Fail(code=400, msg=f"应用 '{app_name}' 不存在")
        else:
            return Fail(code=400, msg="请指定租户ID或应用名称")
    else:
        target_tenant_id = current_user.current_tenant_id
        if target_tenant_id <= 0:
            return Fail(code=400, msg="您当前未选择租户")

    if not file.filename.endswith('.csv'):
        return Fail(code=400, msg="请上传CSV文件")

    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content_str))

        if not csv_reader.fieldnames:
            return Fail(code=400, msg="CSV文件格式错误：无法读取表头")
        required_level1_fields = ['一级事件类型', '一级事件类型ID']
        required_level2_fields = ['二级事件类型', '二级事件类型ID']
        required_level3_fields = ['三级事件类型', '三级事件类型ID']

        fieldnames = csv_reader.fieldnames
        has_level1 = all(f in fieldnames for f in required_level1_fields)
        rows = list(csv_reader)
        created_count = 0
        updated_count = 0
        errors = []

        # 用于存储各级选项的ID映射
        level1_map = {}  # {option_value: id}
        level2_map = {}  # {option_value: id}
        level3_map = {}  # {option_value: id}

        # 第一步：创建/更新所有一级事件类型
        for idx, row in enumerate(rows, start=2):
            try:
                level1_name = row.get(level1_name_field, '').strip()
                level1_id = row.get(level1_id_field, '').strip()
                level1_desc = row.get(level1_desc_field, '').strip() if level1_desc_field else ''

                if not level1_name or not level1_id:
                    continue

                # 使用ID作为option_value，名称作为summary
                option_value = level1_id
                summary = level1_name
                description = level1_desc

                existing = await dropdown_option_controller.model.filter(
                    tenant_id=target_tenant_id,
                    app_name=app_name,
                    class_name=class_name,
                    option_value=option_value
                ).first()

                if existing:
                    existing.summary = summary
                    existing.description = description
                    existing.parent_id = 0
                    await existing.save()
                    level1_map[option_value] = existing.id
                    updated_count += 1
                else:
                    option = await dropdown_option_controller.model.create(
                        tenant_id=target_tenant_id,
                        app_name=app_name,
                        class_name=class_name,
                        option_value=option_value,
                        summary=summary,
                        description=description,
                        parent_id=0
                    )
                    level1_map[option_value] = option.id
                    created_count += 1

            except Exception as e:
                errors.append(f"第{idx}行(一级): {str(e)}")

        # 第二步：创建/更新所有二级事件类型（如果配置了二级字段映射）
        if level2_name_field and level2_id_field:
            for idx, row in enumerate(rows, start=2):
                try:
                    level1_id = row.get(level1_id_field, '').strip()
                    level2_name = row.get(level2_name_field, '').strip()
                    level2_id = row.get(level2_id_field, '').strip()
                    level2_desc = row.get(level2_desc_field, '').strip() if level2_desc_field else ''

                    if not level2_name or not level2_id or not level1_id:
                        continue

                    option_value = level2_id
                    summary = level2_name
                    description = level2_desc

                    # 查找父级ID
                    parent_id = level1_map.get(level1_id, 0)

                    existing = await dropdown_option_controller.model.filter(
                        tenant_id=target_tenant_id,
                        app_name=app_name,
                        class_name=class_name,
                        option_value=option_value
                    ).first()

                    if existing:
                        existing.summary = summary
                        existing.description = description
                        existing.parent_id = parent_id
                        await existing.save()
                        level2_map[option_value] = existing.id
                        updated_count += 1
                    else:
                        option = await dropdown_option_controller.model.create(
                            tenant_id=target_tenant_id,
                            app_name=app_name,
                            class_name=class_name,
                            option_value=option_value,
                            summary=summary,
                            description=description,
                            parent_id=parent_id
                        )
                        level2_map[option_value] = option.id
                        created_count += 1

                except Exception as e:
                    errors.append(f"第{idx}行(二级): {str(e)}")

        # 第三步：创建/更新所有三级事件类型（如果配置了三级字段映射且配置了二级字段映射）
        if level3_name_field and level3_id_field and level2_name_field and level2_id_field:
          for idx, row in enumerate(rows, start=2):
              try:
                  level2_id = row.get(level2_id_field, '').strip()
                  level3_name = row.get(level3_name_field, '').strip()
                  level3_id = row.get(level3_id_field, '').strip()
                  level3_desc = row.get(level3_desc_field, '').strip() if level3_desc_field else ''

                  if not level3_name or not level3_id or not level2_id:
                      continue

                  option_value = level3_id
                  summary = level3_name
                  description = level3_desc

                  # 查找父级ID
                  parent_id = level2_map.get(level2_id, 0)

                  existing = await dropdown_option_controller.model.filter(
                      tenant_id=target_tenant_id,
                      app_name=app_name,
                      class_name=class_name,
                      option_value=option_value
                  ).first()

                  if existing:
                      existing.summary = summary
                      existing.description = description
                      existing.parent_id = parent_id
                      await existing.save()
                      level3_map[option_value] = existing.id
                      updated_count += 1
                  else:
                      option = await dropdown_option_controller.model.create(
                          tenant_id=target_tenant_id,
                          app_name=app_name,
                          class_name=class_name,
                          option_value=option_value,
                          summary=summary,
                          description=description,
                          parent_id=parent_id
                      )
                      level3_map[option_value] = option.id
                      created_count += 1

              except Exception as e:
                  errors.append(f"第{idx}行(三级): {str(e)}")

        result = {
            "created": created_count,
            "updated": updated_count,
            "total": len(rows),
            "level1_count": len(level1_map),
            "level2_count": len(level2_map),
            "level3_count": len(level3_map),
            "errors": errors
        }

        if errors:
            return Success(data=result, msg=f"导入完成，但有{len(errors)}个错误")
        return Success(data=result, msg="导入成功")

    except Exception as e:
        return Fail(code=500, msg=f"导入失败: {str(e)}")
