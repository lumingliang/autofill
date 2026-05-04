#!/usr/bin/env python3
"""检查字段组详情"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.core.init_app import init_db
from app.models.autofill import FieldGroupConfig, FieldSpec, FieldGroupFieldSpec

async def check():
    await init_db()
    
    # 检查每个服务记录字段组的字段
    groups = await FieldGroupConfig.filter(page_name="用户信息页").exclude(group_name="default").all()
    
    print("=" * 60)
    print("服务记录字段组详情")
    print("=" * 60)
    
    for group in groups:
        print(f"\n📋 {group.group_name}")
        print(f"   输出模板: {group.output_templates}")
        print(f"   Prompt模板: {group.prompt_template_base}")
        
        # 获取关联的字段
        relations = await FieldGroupFieldSpec.filter(field_group_id=group.id).all()
        print(f"   关联字段数: {len(relations)}")
        
        for r in relations:
            field = await FieldSpec.filter(id=r.field_spec_id).first()
            if field:
                print(f"     - {field.field_name} ({field.field_label})")

if __name__ == "__main__":
    asyncio.run(check())
