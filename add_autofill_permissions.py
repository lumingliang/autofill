#!/usr/bin/env python3
"""
智能填单系统权限初始化脚本
为新的 autofill 接口添加权限记录
"""
import asyncio
import sys

sys.path.insert(0, ".")

from app.models.admin import Api, Role
from app.models.enums import MethodType
from app.core.relation import RelationQuery


async def init_autofill_apis():
    """初始化智能填单相关API权限"""

    # 定义需要添加的API
    apis = [
        # 应用管理
        ("GET", "/api/v1/autofill/app/list", "应用列表", "智能填单"),
        ("GET", "/api/v1/autofill/app/get", "应用详情", "智能填单"),
        ("POST", "/api/v1/autofill/app/create", "创建应用", "智能填单"),
        ("POST", "/api/v1/autofill/app/update", "更新应用", "智能填单"),
        ("DELETE", "/api/v1/autofill/app/delete", "删除应用", "智能填单"),
        # 模板管理
        ("GET", "/api/v1/autofill/template/list", "模板列表", "智能填单"),
        ("GET", "/api/v1/autofill/template/get", "模板详情", "智能填单"),
        ("POST", "/api/v1/autofill/template/create", "创建模板", "智能填单"),
        ("POST", "/api/v1/autofill/template/update", "更新模板", "智能填单"),
        ("DELETE", "/api/v1/autofill/template/delete", "删除模板", "智能填单"),
        # 下拉选项管理
        ("GET", "/api/v1/autofill/dropdown/list", "下拉选项列表", "智能填单"),
        ("GET", "/api/v1/autofill/dropdown/tree", "下拉选项树形结构", "智能填单"),
        ("GET", "/api/v1/autofill/dropdown/get", "下拉选项详情", "智能填单"),
        ("POST", "/api/v1/autofill/dropdown/create", "创建下拉选项", "智能填单"),
        ("POST", "/api/v1/autofill/dropdown/update", "更新下拉选项", "智能填单"),
        ("DELETE", "/api/v1/autofill/dropdown/delete", "删除下拉选项", "智能填单"),
        # 填单记录管理
        ("GET", "/api/v1/autofill/record/list", "填单记录列表", "智能填单"),
        ("GET", "/api/v1/autofill/record/get", "填单记录详情", "智能填单"),
        ("POST", "/api/v1/autofill/record/update", "更新填单记录", "智能填单"),
        ("DELETE", "/api/v1/autofill/record/delete", "删除填单记录", "智能填单"),
    ]

    created_apis = []
    for method, path, summary, tags in apis:
        # 检查是否已存在
        existing = await Api.filter(method=MethodType(method), path=path).first()
        if not existing:
            api = await Api.create(
                method=MethodType(method),
                path=path,
                summary=summary,
                tags=tags,
            )
            created_apis.append(api)
            print(f"Created API: {method} {path}")
        else:
            print(f"API already exists: {method} {path}")

    # 为管理员角色分配新权限
    admin_role = await Role.filter(name="管理员").first()
    if admin_role and created_apis:
        api_ids = [api.id for api in created_apis]
        await RelationQuery.batch_add_role_apis([(admin_role.id, aid) for aid in api_ids])
        print(f"\nAssigned {len(api_ids)} new APIs to admin role")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(init_autofill_apis())
