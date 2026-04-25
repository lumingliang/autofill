#!/usr/bin/env python3
"""
为部门管理员角色添加查看菜单列表和API列表的权限
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.models.admin import Role, Menu, Api

async def add_permissions():
    # 获取部门管理员角色
    role = await Role.filter(name="部门管理员").first()
    if not role:
        print("部门管理员角色不存在")
        return
    
    print(f"找到角色: {role.name} (ID: {role.id})")
    
    # 获取查看菜单列表的API
    menu_list_api = await Api.filter(path="/api/v1/menu/list", method="GET").first()
    if menu_list_api:
        # 检查是否已关联
        existing_apis = await role.apis.all()
        if menu_list_api not in existing_apis:
            await role.apis.add(menu_list_api)
            print(f"已添加API权限: {menu_list_api.summary} ({menu_list_api.path})")
        else:
            print(f"API权限已存在: {menu_list_api.summary}")
    else:
        print("查看菜单列表API不存在")
    
    # 获取查看API列表的API
    api_list_api = await Api.filter(path="/api/v1/api/list", method="GET").first()
    if api_list_api:
        existing_apis = await role.apis.all()
        if api_list_api not in existing_apis:
            await role.apis.add(api_list_api)
            print(f"已添加API权限: {api_list_api.summary} ({api_list_api.path})")
        else:
            print(f"API权限已存在: {api_list_api.summary}")
    else:
        print("查看API列表API不存在")
    
    # 获取菜单管理菜单
    menu_mgmt = await Menu.filter(name="菜单管理").first()
    if menu_mgmt:
        existing_menus = await role.menus.all()
        if menu_mgmt not in existing_menus:
            await role.menus.add(menu_mgmt)
            print(f"已添加菜单: {menu_mgmt.name}")
        else:
            print(f"菜单已存在: {menu_mgmt.name}")
    else:
        print("菜单管理菜单不存在")
    
    # 获取API管理菜单
    api_mgmt = await Menu.filter(name="API管理").first()
    if api_mgmt:
        existing_menus = await role.menus.all()
        if api_mgmt not in existing_menus:
            await role.menus.add(api_mgmt)
            print(f"已添加菜单: {api_mgmt.name}")
        else:
            print(f"菜单已存在: {api_mgmt.name}")
    else:
        print("API管理菜单不存在")
    
    print("\n权限添加完成！")

if __name__ == "__main__":
    asyncio.run(add_permissions())
