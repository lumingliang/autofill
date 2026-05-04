#!/usr/bin/env python3
"""清理所有字段组和字段"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.core.init_app import init_db
from app.models.autofill import FieldGroupConfig, FieldSpec, FieldGroupFieldSpec

async def cleanup():
    # 初始化数据库
    await init_db()
    
    print("开始清理数据...")
    
    # 删除关联表数据
    relations = await FieldGroupFieldSpec.all()
    for r in relations:
        await r.delete()
    print(f"✅ 已删除 {len(relations)} 条字段组-字段关联")
    
    # 删除字段
    fields = await FieldSpec.all()
    for f in fields:
        await f.delete()
    print(f"✅ 已删除 {len(fields)} 个字段")
    
    # 删除字段组
    groups = await FieldGroupConfig.all()
    for g in groups:
        await g.delete()
    print(f"✅ 已删除 {len(groups)} 个字段组")
    
    print("\n清理完成！")

if __name__ == "__main__":
    asyncio.run(cleanup())
