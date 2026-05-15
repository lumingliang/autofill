import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from tortoise import Tortoise
from tortoise.expressions import Q
from app.models import DropdownOption

async def test():
    await Tortoise.init(
        config={
            'connections': {
                'default': 'mysql://root:root123456@127.0.0.1:3306/autofill'
            },
            'apps': {
                'models': {
                    'models': ['app.models'],
                    'default_connection': 'default',
                }
            }
        }
    )

    app_name = 'test_app'
    effective_tenant_id = 3
    is_superuser = True

    # 构建查询条件
    query = Q(app_name=app_name)

    # 非超级用户只能查看自己租户的数据
    if not is_superuser:
        if effective_tenant_id <= 0:
            print("请指定租户ID")
            return
        query &= Q(tenant_id=effective_tenant_id)
    elif effective_tenant_id > 0:
        # 超级用户指定了租户ID，优先使用该租户
        query &= Q(tenant_id=effective_tenant_id)
    # 超级用户未指定租户ID，查询所有租户

    print(f"Query: {query}")

    options = await DropdownOption.filter(
        query
    ).distinct().values("class_name")

    print(f"Found {len(options)} options: {options}")

    # 测试查询所有
    query2 = Q(app_name=app_name)
    options2 = await DropdownOption.filter(
        query2
    ).distinct().values("class_name")
    print(f"All options: {options2}")

    await Tortoise.close_connections()

asyncio.run(test())
