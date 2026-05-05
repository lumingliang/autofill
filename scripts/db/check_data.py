#!/usr/bin/env python3
"""检查同步后的数据是否正常"""

import asyncio
import httpx

API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
BASE_URL = "http://localhost:9999"


async def check_data():
    async with httpx.AsyncClient() as client:
        # 查询字段列表
        resp = await client.get(
            f"{BASE_URL}/api/autofill/field_spec/list",
            params={"page_name": "用户信息页", "group_name": "default"},
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        data = resp.json()

        print("=" * 60)
        print("字段列表检查")
        print("=" * 60)

        # 统计字段
        fields = data.get("data", [])
        event_type_fields = [f for f in fields if "事件类型" in f.get("field_name", "")]
        second_level_fields = [f for f in fields if "二三级" in f.get("field_name", "")]

        print(f"总字段数: {len(fields)}")
        print(f"一级事件类型字段: {len(event_type_fields)}")
        print(f"二三级事件类型字段: {len(second_level_fields)}")
        print()

        # 检查一级事件类型字段
        print("-" * 60)
        print("一级事件类型字段详情:")
        print("-" * 60)
        for f in event_type_fields:
            print(f"  字段ID: {f['id']}")
            print(f"  字段名: {f['field_name']}")
            print(f"  字段标签: {f['field_label']}")
            print(f"  填写指引: {f['fill_instruction']}")
            opts = f.get("options", {}).get("items", [])
            print(f"  选项数量: {len(opts)}")
            for opt in opts:
                print(f"    - {opt.get('label')} (value={opt.get('value')})")
            print()

        # 检查二三级字段
        print("-" * 60)
        print("二三级事件类型字段汇总:")
        print("-" * 60)
        for f in second_level_fields:
            opts = f.get("options", {}).get("items", [])
            print(f"  {f['field_name']}: {len(opts)} 个选项")

        # 验证数据完整性
        print()
        print("=" * 60)
        print("数据完整性验证")
        print("=" * 60)

        all_ok = True

        # 验证一级事件类型
        if len(event_type_fields) == 1:
            f = event_type_fields[0]
            opts = f.get("options", {}).get("items", [])
            if len(opts) == 11:
                print("✅ 一级事件类型: 11 个选项 (正确)")
            else:
                print(f"❌ 一级事件类型: {len(opts)} 个选项 (期望 11)")
                all_ok = False
        else:
            print(f"❌ 一级事件类型字段数量: {len(event_type_fields)} (期望 1)")
            all_ok = False

        # 验证二三级字段
        if len(second_level_fields) == 11:
            print("✅ 二三级事件类型字段: 11 个 (正确)")
        else:
            print(f"❌ 二三级事件类型字段: {len(second_level_fields)} 个 (期望 11)")
            all_ok = False

        # 验证每个二三级字段的选项数
        for f in second_level_fields:
            opts = f.get("options", {}).get("items", [])
            if len(opts) != 15:
                print(f"❌ {f['field_name']}: {len(opts)} 个选项 (期望 15)")
                all_ok = False

        if all_ok:
            print("✅ 所有二三级字段: 各 15 个选项 (正确)")

        print()
        if all_ok:
            print("=" * 60)
            print("✅ 所有数据检查通过!")
            print("=" * 60)
        else:
            print("=" * 60)
            print("❌ 数据检查发现问题")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(check_data())
