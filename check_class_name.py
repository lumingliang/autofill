import asyncio
from tortoise import Tortoise
from app.models import DropdownOption

async def check():
    await Tortoise.init(
        db_url='sqlite://db.sqlite3',
        modules={'models': ['app.models']}
    )

    # 获取所有 test_app 的记录
    options = await DropdownOption.filter(app_name='test_app').all()
    print(f'总记录数: {len(options)}')
    for opt in options:
        print(f'  ID={opt.id}, option_value={opt.option_value}, class_name={repr(opt.class_name)}, parent_id={opt.parent_id}')

    # 获取不同的 class_name
    distinct = await DropdownOption.filter(app_name='test_app').distinct().values('class_name')
    print(f'\n不同的 class_name: {distinct}')

    await Tortoise.close_connections()

asyncio.run(check())
