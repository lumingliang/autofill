#!/usr/bin/env python3
"""
迁移脚本：将旧的 'select' 类型字段转换为新的类型
- text -> text (不变)
- select + selection_mode=0 -> select_single (单选)
- select + selection_mode=1 -> select_multi (多选)

直接在数据库层面执行SQL，避免枚举验证
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

import aiomysql
from app.settings.config import settings


async def migrate():
    # 连接数据库
    conn = await aiomysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE
    )
    
    try:
        async with conn.cursor() as cur:
            # 1. 先查询所有 select 类型的字段
            await cur.execute("SELECT id, field_name, field_type, options FROM field_spec WHERE field_type = 'select'")
            rows = await cur.fetchall()
            
            print(f"找到 {len(rows)} 个需要迁移的字段")
            
            migrated_count = 0
            for row in rows:
                field_id, field_name, old_type, options = row
                
                # 解析options获取 selection_mode
                import json
                try:
                    options_dict = json.loads(options) if options else {}
                except:
                    options_dict = {}
                
                selection_mode = options_dict.get('selection_mode', 0)
                
                if selection_mode == 1:
                    new_type = 'select_multi'
                else:
                    new_type = 'select_single'
                
                # 更新字段类型
                await cur.execute(
                    "UPDATE field_spec SET field_type = %s WHERE id = %s",
                    (new_type, field_id)
                )
                
                print(f'迁移: {field_name} (ID={field_id}): {old_type} -> {new_type}')
                migrated_count += 1
            
            await conn.commit()
            print(f'\n迁移完成！共迁移 {migrated_count} 个字段')
            
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
