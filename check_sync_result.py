#!/usr/bin/env python3
"""检查同步结果"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.core.init_app import init_db
from app.models.autofill import FieldGroupConfig, FieldSpec, FieldGroupFieldSpec

async def check():
    # 初始化数据库
    await init_db()
    
    print("=" * 60)
    print("同步结果检查")
    print("=" * 60)
    
    # 检查字段组
    groups = await FieldGroupConfig.filter(page_name="用户信息页").all()
    print(f"\n📋 字段组数量: {len(groups)}")
    for g in groups:
        print(f"  - {g.group_name} (ID: {g.id})")
    
    # 检查字段
    fields = await FieldSpec.filter(tenant_id=1, app_name="test_app").all()
    print(f"\n📋 字段数量: {len(fields)}")
    for f in fields:
        print(f"  - {f.field_name} ({f.field_label}, 类型: {f.field_type})")
    
    # 检查场景分类字段的选项
    scene_field = await FieldSpec.filter(field_name="scene_category").first()
    if scene_field and scene_field.options:
        items = scene_field.options.get('items', [])
        print(f"\n📋 场景分类下拉选项数量: {len(items)}")
        for item in items[:5]:
            fill_inst = item.get('fill_instruction', '未设置')
            print(f"  - {item['label']}: fill_instruction={fill_inst[:30]}...")
        if len(items) > 5:
            print(f"  ... 还有 {len(items) - 5} 个选项")
    
    # 检查关联关系
    relations = await FieldGroupFieldSpec.filter(tenant_id=1, app_name="test_app").all()
    print(f"\n📋 字段组-字段关联数量: {len(relations)}")
    
    print("\n" + "=" * 60)
    print("预期结果:")
    print("  - 字段组: 11 个 (1个default + 10个服务记录)")
    print("  - 场景分类字段: 1 个，包含 10 个下拉选项")
    print("  - 服务记录字段: 约 40 个 (每个模板4个变量)")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(check())
