#!/usr/bin/env python3
"""
清理所有测试数据的脚本
删除所有非超管创建的数据：租户、用户、角色
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from tortoise import Tortoise

from app.settings.config import settings
from app.models.admin import Tenant, User, Role, UserTenant, UserRole, RoleMenu, RoleApi

async def cleanup_all_test_data():
    print("="*60)
    print("清理所有测试数据")
    print("="*60)
    
    db_url = f"mysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    
    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['app.models']}
    )
    await Tortoise.generate_schemas()
    
    print("\n正在查询数据...")
    
    all_tenants = await Tenant.all()
    all_users = await User.all()
    all_roles = await Role.all()
    
    print(f"租户总数: {len(all_tenants)}")
    print(f"用户总数: {len(all_users)}")
    print(f"角色总数: {len(all_roles)}")
    
    print(f"\n保留: 超级管理员 (ID=1)")
    
    print("\n" + "="*60)
    response = input("确认删除所有测试数据？(y/n): ")
    
    if response.lower() != 'y':
        print("已取消")
        return
    
    print("\n开始清理...")
    
    # 删除所有租户
    for tenant in all_tenants:
        roles = await Role.filter(tenant_id=tenant.id)
        role_ids = [r.id for r in roles]
        
        if role_ids:
            await RoleMenu.filter(role_id__in=role_ids).delete()
            await RoleApi.filter(role_id__in=role_ids).delete()
            await UserRole.filter(role_id__in=role_ids).delete()
            await Role.filter(id__in=role_ids).delete()
        
        user_tenants = await UserTenant.filter(tenant_id=tenant.id)
        for ut in user_tenants:
            if ut.user_id != 1:
                await UserRole.filter(user_id=ut.user_id).delete()
                await User.filter(id=ut.user_id).delete()
        
        await UserTenant.filter(tenant_id=tenant.id).delete()
        await tenant.delete()
        print(f"  ✓ 删除租户: {tenant.name}")
    
    # 删除所有非超管租户创建的角色 (tenant_id != 0)
    roles = await Role.filter(tenant_id__not=0)
    for role in roles:
        await RoleMenu.filter(role_id=role.id).delete()
        await RoleApi.filter(role_id=role.id).delete()
        await UserRole.filter(role_id=role.id).delete()
        await role.delete()
        print(f"  ✓ 删除角色: {role.name}")
    
    # 删除所有非超管用户
    users = await User.filter(id__not=1)
    for user in users:
        await UserTenant.filter(user_id=user.id).delete()
        await UserRole.filter(user_id=user.id).delete()
        await user.delete()
        print(f"  ✓ 删除用户: {user.username}")
    
    print("\n" + "="*60)
    print("清理完成！")
    print("="*60)
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(cleanup_all_test_data())
