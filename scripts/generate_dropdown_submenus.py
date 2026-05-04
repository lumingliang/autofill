"""
为 dropdown 一级菜单生成二级和三级菜单数据

用法:
    python scripts/generate_dropdown_submenus.py
    python scripts/generate_dropdown_submenus.py --tenant-id 1 --app-name autofill --class-name 问题分类
    python scripts/generate_dropdown_submenus.py --clear-existing  # 先清空现有数据再生成
"""
import asyncio
import argparse
import random
from typing import List, Dict, Any

from tortoise import Tortoise

from app.models.autofill import DropdownOption
from app.settings import settings


# 二级菜单模板数据（按分类组织）
LEVEL2_TEMPLATES: Dict[str, List[str]] = {
    "产品问题": [
        "功能异常", "性能问题", "兼容性问题", "界面显示", "操作体验",
        "安装问题", "更新问题", "闪退崩溃", "数据丢失", "网络连接"
    ],
    "服务问题": [
        "响应速度慢", "服务态度", "服务流程", "预约困难", "等待时间长",
        "沟通不畅", "解决方案不满意", "跟进不及时", "回访缺失", "投诉处理"
    ],
    "费用问题": [
        "收费不透明", "价格过高", "额外收费", "退款问题", "发票问题",
        "优惠政策", "分期付款", "保险理赔", "质保范围", "费用争议"
    ],
    "技术问题": [
        "系统故障", "接口异常", "数据同步", "权限问题", "配置错误",
        "安全漏洞", "日志报错", "数据库问题", "缓存异常", "第三方对接"
    ],
    "物流问题": [
        "配送延迟", "包裹损坏", "地址错误", "丢失件", "配送态度",
        "自提问题", "运费争议", "包装问题", "签收问题", "退换货运费"
    ],
    "售后问题": [
        "维修质量", "配件问题", "保修期争议", "退换货", "维修周期",
        "上门服务", "维修费用", "原厂配件", "质保政策", "售后态度"
    ],
    "咨询类": [
        "产品咨询", "价格咨询", "活动咨询", "使用指导", "功能介绍",
        "购买建议", "对比咨询", "定制需求", "合作咨询", "其他咨询"
    ],
    "投诉类": [
        "产品质量投诉", "服务态度投诉", "价格投诉", "虚假宣传投诉",
        "合同违约投诉", "隐私泄露投诉", "侵权投诉", "欺诈投诉", "其他投诉"
    ],
    "建议类": [
        "产品改进建议", "服务改进建议", "功能新增建议", "流程优化建议",
        "价格调整建议", "活动建议", "渠道建议", "合作建议", "其他建议"
    ],
    "其他": [
        "无法分类", "综合问题", "历史遗留", "跨部门问题", "紧急事件",
        "特殊案例", "测试数据", "内部问题", "外部因素", "待定分类"
    ],
}

# 三级菜单模板数据（按二级分类组织）
LEVEL3_TEMPLATES: Dict[str, List[str]] = {
    # 产品问题 - 子项
    "功能异常": ["核心功能失效", "次要功能异常", "间歇性功能问题", "特定场景失效", "功能缺失"],
    "性能问题": ["加载缓慢", "响应迟钝", "内存占用高", "CPU占用高", "卡顿 freeze"],
    "兼容性问题": ["浏览器不兼容", "设备不兼容", "系统版本问题", "分辨率适配", "第三方冲突"],
    "界面显示": ["布局错乱", "样式异常", "图片不显示", "文字乱码", "颜色异常"],
    "操作体验": ["流程繁琐", "交互不友好", "提示不清晰", "操作无反馈", "学习成本高"],

    # 服务问题 - 子项
    "响应速度慢": ["电话等待久", "在线回复慢", "工单处理慢", "紧急响应慢", "非工作时间响应"],
    "服务态度": ["语气生硬", "不耐烦", "推诿责任", "敷衍了事", "态度冷漠"],
    "服务流程": ["流程复杂", "环节过多", "重复提交", "审批缓慢", "流程不透明"],

    # 费用问题 - 子项
    "收费不透明": ["未提前告知", "收费标准不清", "隐藏费用", "计费错误", "费用明细缺失"],
    "价格过高": ["高于市场价", "高于预期", "涨价过快", "性价比低", "同类对比贵"],

    # 技术问题 - 子项
    "系统故障": ["服务器宕机", "服务不可用", "系统错误", "503错误", "500错误"],
    "数据同步": ["同步延迟", "数据不一致", "同步失败", "丢失更新", "冲突未解决"],

    # 物流问题 - 子项
    "配送延迟": ["超出承诺时效", "物流信息不更新", "中转延误", "天气原因", "节假日延迟"],
    "包裹损坏": ["外包装破损", "内件损坏", "液体泄漏", "挤压变形", "划痕磨损"],

    # 售后问题 - 子项
    "维修质量": ["未修复问题", "反复故障", "维修引入新问题", "清洁不到位", "测试不充分"],
    "保修期争议": ["保修期计算", "人为损坏认定", "保修范围争议", "凭证问题", "延保问题"],

    # 通用三级选项（用于没有特定匹配的二级分类）
    "default": ["严重", "一般", "轻微", "紧急", "普通", "建议", "咨询", "其他"],
}


def get_level2_options(level1_name: str) -> List[str]:
    """根据一级菜单名称获取对应的二级菜单选项"""
    # 尝试直接匹配
    if level1_name in LEVEL2_TEMPLATES:
        return LEVEL2_TEMPLATES[level1_name]

    # 尝试模糊匹配
    for key in LEVEL2_TEMPLATES:
        if key in level1_name or level1_name in key:
            return LEVEL2_TEMPLATES[key]

    # 返回默认选项
    return ["子选项A", "子选项B", "子选项C", "子选项D", "子选项E"]


def get_level3_options(level2_name: str) -> List[str]:
    """根据二级菜单名称获取对应的三级菜单选项"""
    if level2_name in LEVEL3_TEMPLATES:
        return LEVEL3_TEMPLATES[level2_name]
    return LEVEL3_TEMPLATES["default"]


async def init_tortoise():
    """初始化数据库连接"""
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def close_tortoise():
    """关闭数据库连接"""
    await Tortoise.close_connections()


async def get_existing_level1_options(tenant_id: int, app_name: str, class_name: str = None) -> List[DropdownOption]:
    """获取现有的一级菜单选项（parent_id=0）"""
    query = DropdownOption.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        parent_id=0
    )
    if class_name:
        query = query.filter(class_name=class_name)

    return await query.all()


async def clear_existing_submenus(tenant_id: int, app_name: str, class_name: str = None):
    """清空现有的二级和三级菜单"""
    query = DropdownOption.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        parent_id__gt=0  # parent_id > 0 表示非一级菜单
    )
    if class_name:
        query = query.filter(class_name=class_name)

    count = await query.count()
    await query.delete()
    print(f"已清空 {count} 个二级/三级菜单选项")


async def generate_submenus_for_level1(
    level1_option: DropdownOption,
    level2_count: int = 3,
    level3_count: int = 2
) -> Dict[str, Any]:
    """为单个一级菜单生成二级和三级菜单"""

    level1_name = level1_option.option_value
    class_name = level1_option.class_name
    tenant_id = level1_option.tenant_id
    app_name = level1_option.app_name

    print(f"\n处理一级菜单: {level1_name} (class: {class_name})")

    # 获取二级菜单选项列表
    level2_options = get_level2_options(level1_name)
    # 随机选择指定数量的二级菜单
    selected_level2 = random.sample(
        level2_options,
        min(level2_count, len(level2_options))
    )

    created_count = {"level2": 0, "level3": 0}

    for level2_name in selected_level2:
        # 创建二级菜单
        level2_option = await DropdownOption.create(
            summary=f"{level1_name} - {level2_name}",
            description=f"{level1_name}分类下的{level2_name}子选项",
            class_name=class_name,
            tenant_id=tenant_id,
            app_name=app_name,
            parent_id=level1_option.id,
            option_value=level2_name
        )
        created_count["level2"] += 1
        print(f"  创建二级菜单: {level2_name} (id: {level2_option.id})")

        # 为二级菜单创建三级菜单
        level3_options = get_level3_options(level2_name)
        selected_level3 = random.sample(
            level3_options,
            min(level3_count, len(level3_options))
        )

        for level3_name in selected_level3:
            level3_option = await DropdownOption.create(
                summary=f"{level1_name} - {level2_name} - {level3_name}",
                description=f"{level2_name}分类下的{level3_name}子选项",
                class_name=class_name,
                tenant_id=tenant_id,
                app_name=app_name,
                parent_id=level2_option.id,
                option_value=level3_name
            )
            created_count["level3"] += 1
            print(f"    创建三级菜单: {level3_name} (id: {level3_option.id})")

    return created_count


async def main():
    parser = argparse.ArgumentParser(description="生成 dropdown 多级菜单测试数据")
    parser.add_argument("--tenant-id", type=int, default=1, help="租户ID (默认: 1)")
    parser.add_argument("--app-name", type=str, default="autofill", help="应用名称 (默认: autofill)")
    parser.add_argument("--class-name", type=str, default=None, help="分类名称 (可选)")
    parser.add_argument("--level2-count", type=int, default=3, help="每个一级菜单生成的二级菜单数量 (默认: 3)")
    parser.add_argument("--level3-count", type=int, default=2, help="每个二级菜单生成的三级菜单数量 (默认: 2)")
    parser.add_argument("--clear-existing", action="store_true", help="是否先清空现有的二级/三级菜单")

    args = parser.parse_args()

    print("=" * 60)
    print("Dropdown 多级菜单生成工具")
    print("=" * 60)
    print(f"租户ID: {args.tenant_id}")
    print(f"应用名称: {args.app_name}")
    print(f"分类名称: {args.class_name or '所有分类'}")
    print(f"二级菜单数量/一级: {args.level2_count}")
    print(f"三级菜单数量/二级: {args.level3_count}")
    print("=" * 60)

    await init_tortoise()

    try:
        # 如果需要，先清空现有数据
        if args.clear_existing:
            await clear_existing_submenus(args.tenant_id, args.app_name, args.class_name)

        # 获取所有一级菜单
        level1_options = await get_existing_level1_options(
            args.tenant_id, args.app_name, args.class_name
        )

        if not level1_options:
            print(f"\n未找到一级菜单选项，请先创建一级菜单数据")
            print(f"查询条件: tenant_id={args.tenant_id}, app_name={args.app_name}, parent_id=0")
            return

        print(f"\n找到 {len(level1_options)} 个一级菜单")

        # 统计信息
        total_stats = {"level2": 0, "level3": 0}

        # 为每个一级菜单生成子菜单
        for level1 in level1_options:
            stats = await generate_submenus_for_level1(
                level1,
                level2_count=args.level2_count,
                level3_count=args.level3_count
            )
            total_stats["level2"] += stats["level2"]
            total_stats["level3"] += stats["level3"]

        print("\n" + "=" * 60)
        print("生成完成!")
        print(f"一级菜单数量: {len(level1_options)}")
        print(f"二级菜单数量: {total_stats['level2']}")
        print(f"三级菜单数量: {total_stats['level3']}")
        print("=" * 60)

    finally:
        await close_tortoise()


if __name__ == "__main__":
    asyncio.run(main())
