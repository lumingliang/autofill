#!/usr/bin/env python3
"""
重新生成所有API的api_code
由于api_code格式变更，需要清空表并重新生成
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from tortoise import Tortoise
from app.settings.config import settings
from app.controllers.api import api_controller
from app.models.admin import Api

async def init_tortoise():
    """初始化Tortoise ORM"""
    await Tortoise.init(config=settings.TORTOISE_ORM)

async def regenerate_api_codes():
    print("开始重新生成API Codes...")
    
    # 初始化数据库连接
    await init_tortoise()
    print("✓ 数据库连接已初始化")
    
    # 清空现有API表
    print("清空现有API表...")
    await Api.all().delete()
    print("✓ API表已清空")
    
    # 从app导入FastAPI实例
    from app import app
    
    # 刷新API列表
    print("重新生成API列表...")
    await api_controller.refresh_api(app)
    
    # 统计生成的API
    count = await Api.all().count()
    print(f"✓ 成功生成 {count} 个API")
    
    # 显示前20个API作为示例
    print("\n前20个API示例:")
    apis = await Api.all().limit(20)
    for api in apis:
        print(f"  - {api.api_code}: {api.method} {api.path}")
    
    # 关闭数据库连接
    await Tortoise.close_connections()
    print("\n✓ 完成")

if __name__ == "__main__":
    asyncio.run(regenerate_api_codes())
