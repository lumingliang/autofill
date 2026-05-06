#!/usr/bin/env python3
"""
直接查询数据库检查字段组配置
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.db import init_db, close_db
from app.controllers.autofill import field_group_config_controller, field_spec_controller, fill_page_controller
from app.models.autofill import FieldGroupFieldSpec


async def check_db():
    await init_db()
    
    try:
        tenant_id = 1
        app_name = "autofill"
        
        # 1. 查找页面
        page = await fill_page_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            page_name="用户信息页"
        ).first()
        
        if not page:
            print("页面 '用户信息页' 不存在")
            return
        
        print(f"页面 ID: {page.id}, 名称: {page.page_name}")
        
        # 2. 查找所有字段组
        field_groups = await field_group_config_controller.model.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            page_id=page.id
        ).all()
        
        print(f"\n找到 {len(field_groups)} 个字段组:")
        for fg in field_groups:
            print(f"\n  字段组: {fg.group_name} (ID: {fg.id})")
            
            # 查找关联的字段
            relations = await FieldGroupFieldSpec.filter(
                field_group_id=fg.id,
                tenant_id=tenant_id,
                app_name=app_name
            ).all()
            
            print(f"    关联数量: {len(relations)}")
            
            if relations:
                field_spec_ids = [r.field_spec_id for r in relations]
                field_specs = await field_spec_controller.model.filter(
                    id__in=field_spec_ids,
                    is_active=True
                ).all()
                
                for fs in field_specs:
                    print(f"      - {fs.field_name} ({fs.field_label})")
    
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(check_db())
