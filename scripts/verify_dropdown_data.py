"""验证生成的 dropdown 数据"""
import asyncio
from tortoise import Tortoise
from app.models.autofill import DropdownOption
from app.settings import settings


async def init():
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def close():
    await Tortoise.close_connections()


async def main():
    await init()

    try:
        # 统计各级菜单数量
        level1_options = await DropdownOption.filter(parent_id=0).all()
        level1_count = len(level1_options)

        level2_ids = []
        level2_count = 0
        for l1 in level1_options:
            l2_list = await DropdownOption.filter(parent_id=l1.id).all()
            level2_count += len(l2_list)
            level2_ids.extend([l2.id for l2 in l2_list])

        level3_count = await DropdownOption.filter(parent_id__in=level2_ids).count()

        print("=" * 60)
        print("数据生成统计")
        print("=" * 60)
        print(f"一级菜单数量: {level1_count}")
        print(f"二级菜单数量: {level2_count}")
        print(f"三级菜单数量: {level3_count}")
        print(f"总记录数: {level1_count + level2_count + level3_count}")
        print("=" * 60)

        # 显示树形结构示例（前3个一级菜单）
        print("\n树形结构示例（前3个一级菜单）:")
        for idx, level1 in enumerate(level1_options[:3]):
            print(f"\n📁 {level1.option_value} (id: {level1.id})")

            level2_options = await DropdownOption.filter(parent_id=level1.id).all()
            for l2_idx, level2 in enumerate(level2_options):
                is_last_l2 = l2_idx == len(level2_options) - 1
                l2_prefix = "   └── " if is_last_l2 else "   ├── "
                print(f"{l2_prefix}📂 {level2.option_value} (id: {level2.id}, parent: {level2.parent_id})")

                level3_options = await DropdownOption.filter(parent_id=level2.id).all()
                for l3_idx, level3 in enumerate(level3_options):
                    is_last_l3 = l3_idx == len(level3_options) - 1
                    l3_prefix = "       └── " if is_last_l3 else "       ├── "
                    print(f"{l3_prefix}📄 {level3.option_value} (id: {level3.id}, parent: {level3.parent_id})")

    finally:
        await close()


if __name__ == "__main__":
    asyncio.run(main())
