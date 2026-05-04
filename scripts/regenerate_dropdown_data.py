#!/usr/bin/env python3
"""
重新生成400客服下拉菜单数据
1. 先删除现有的2/3级数据
2. 生成有意义的400客服二级和三级菜单数据
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tortoise import Tortoise
from app.models.autofill import DropdownOption
from app.settings.config import settings


# 400客服实际业务分类数据
LEVEL2_CATEGORIES = {
    "智能网联": ["APP问题", "车机系统", "流量服务", "远程控制", "OTA升级"],
    "产品咨询": ["车辆配置", "价格政策", "促销活动", "网点查询", "保修保养"],
    "4S店": ["预约服务", "投诉建议", "配件查询", "服务评价", "紧急救援"],
    "救援": ["道路救援", "事故救援", "故障救援", "拖车服务", "现场维修"],
    "业务互转": ["转接销售", "转接售后", "转接投诉", "转接救援", "转接技术"],
    "表扬": ["服务表扬", "产品表扬", "员工表扬", "门店表扬", "整体满意"],
    "建议": ["产品建议", "服务建议", "流程建议", "功能建议", "其他建议"],
    "售前投诉": ["销售欺诈", "价格争议", "承诺未兑现", "服务态度", "交车延迟"],
    "售后投诉": ["维修质量", "配件问题", "服务态度", "收费争议", "保修争议"],
    "内部投诉": ["客服态度", "处理不当", "回复不及时", "信息错误", "推诿扯皮"],
    "三级报警": ["电池故障", "电机故障", "电控故障", "安全系统", "其他故障"],
}

LEVEL3_OPTIONS = {
    # APP问题
    "APP问题": ["无法登录", "闪退卡顿", "功能异常", "数据不同步", "推送问题"],
    # 车机系统
    "车机系统": ["系统卡顿", "导航异常", "蓝牙连接", "语音识别", "软件升级"],
    # 流量服务
    "流量服务": ["流量查询", "流量充值", "流量套餐", "网络连接", "热点共享"],
    # 远程控制
    "远程控制": ["远程启动", "空调控制", "车门控制", "定位寻车", "充电管理"],
    # OTA升级
    "OTA升级": ["升级失败", "升级中断", "版本回退", "功能异常", "预约升级"],
    # 车辆配置
    "车辆配置": ["车型参数", "配置差异", "选装配置", "颜色内饰", "技术规格"],
    # 价格政策
    "价格政策": ["官方指导价", "优惠活动", "置换补贴", "金融政策", "保险方案"],
    # 促销活动
    "促销活动": ["限时优惠", "购车礼包", "试驾活动", "车展活动", "老带新活动"],
    # 网点查询
    "网点查询": ["4S店地址", "服务时间", "联系方式", "维修能力", "配件库存"],
    # 保修保养
    "保修保养": ["保修政策", "保养周期", "保养项目", "保养费用", "延保服务"],
    # 预约服务
    "预约服务": ["保养预约", "维修预约", "试驾预约", "上门取送", "专属顾问"],
    # 投诉建议
    "投诉建议": ["服务投诉", "价格投诉", "质量投诉", "改进建议", "满意度评价"],
    # 配件查询
    "配件查询": ["配件价格", "配件库存", "配件订购", "配件真伪", "配件安装"],
    # 服务评价
    "服务评价": ["服务态度", "服务效率", "服务质量", "环境卫生", "整体满意"],
    # 紧急救援
    "紧急救援": ["24小时热线", "现场救援", "拖车服务", "备用车辆", "应急方案"],
    # 道路救援
    "道路救援": ["爆胎救援", "缺油救援", "电瓶亏电", "钥匙丢失", "困境救援"],
    # 事故救援
    "事故救援": ["现场处理", "保险理赔", "伤情救助", "车辆拖运", "后续跟进"],
    # 故障救援
    "故障救援": ["故障诊断", "现场维修", "拖车维修", "技术支持", "备用方案"],
    # 拖车服务
    "拖车服务": ["市区拖车", "高速拖车", "跨省拖车", "特殊地形", "费用标准"],
    # 现场维修
    "现场维修": ["简单故障", "更换配件", "紧急处理", "临时修复", "安全检测"],
    # 转接销售
    "转接销售": ["购车咨询", "试驾安排", "价格谈判", "订单跟进", "交车服务"],
    # 转接售后
    "转接售后": ["维修咨询", "保养预约", "配件购买", "服务投诉", "技术支持"],
    # 转接投诉
    "转接投诉": ["服务投诉", "质量投诉", "价格投诉", "欺诈投诉", "紧急投诉"],
    # 转接救援
    "转接救援": ["道路救援", "事故救援", "故障救援", "紧急救援", "24小时热线"],
    # 转接技术
    "转接技术": ["技术咨询", "故障诊断", "系统升级", "功能指导", "远程支持"],
    # 服务表扬
    "服务表扬": ["态度热情", "专业高效", "耐心细致", "主动服务", "超出预期"],
    # 产品表扬
    "产品表扬": ["质量可靠", "性能优异", "设计美观", "功能丰富", "性价比高"],
    # 员工表扬
    "员工表扬": ["服务明星", "技术专家", "销售精英", "救援英雄", "贴心顾问"],
    # 门店表扬
    "门店表扬": ["环境整洁", "设施完善", "服务周到", "技术过硬", "管理规范"],
    # 整体满意
    "整体满意": ["购车体验", "用车体验", "服务体验", "品牌认同", "推荐意愿"],
    # 产品建议
    "产品建议": ["功能改进", "配置优化", "质量提升", "设计建议", "新品期待"],
    # 服务建议
    "服务建议": ["流程优化", "效率提升", "态度改善", "专业培训", "服务创新"],
    # 流程建议
    "流程建议": ["简化流程", "透明化", "标准化", "个性化", "数字化"],
    # 功能建议
    "功能建议": ["新增功能", "功能优化", "操作便捷", "智能化", "个性化"],
    # 其他建议
    "其他建议": ["价格建议", "政策建议", "渠道建议", "沟通建议", "其他意见"],
    # 销售欺诈
    "销售欺诈": ["虚假宣传", "隐瞒信息", "强制消费", "合同欺诈", "价格欺诈"],
    # 价格争议
    "价格争议": ["价格变动", "优惠不实", "费用不明", "加价销售", "退款争议"],
    # 承诺未兑现
    "承诺未兑现": ["交车时间", "赠品承诺", "服务承诺", "优惠政策", "质量保证"],
    # 服务态度
    "服务态度": ["态度恶劣", "敷衍了事", "推诿扯皮", "冷漠无视", "歧视客户"],
    # 交车延迟
    "交车延迟": ["无货延迟", "物流延迟", "手续延迟", "质量问题", "沟通不畅"],
    # 维修质量
    "维修质量": ["故障未排除", "越修越坏", "配件质量", "技术水平", "返修率高"],
    # 配件问题
    "配件问题": ["配件缺货", "配件质量", "配件价格", "配件真伪", "安装问题"],
    # 收费争议
    "收费争议": ["收费过高", "收费不明", "重复收费", "乱收费", "价格欺诈"],
    # 保修争议
    "保修争议": ["保修范围", "保修期限", "拒保理由", "保修流程", "保修凭证"],
    # 客服态度
    "客服态度": ["态度生硬", "不耐烦", "不专业", "推诿责任", "敷衍客户"],
    # 处理不当
    "处理不当": ["处理拖延", "处理错误", "处理不公", "处理草率", "处理无果"],
    # 回复不及时
    "回复不及时": ["长时间等待", "无人接听", "回复延迟", "跟进缺失", "失联"],
    # 信息错误
    "信息错误": ["信息有误", "信息不全", "信息过时", "信息矛盾", "误导客户"],
    # 推诿扯皮
    "推诿扯皮": ["部门推诿", "责任不清", "互相扯皮", "无人负责", "逃避责任"],
    # 电池故障
    "电池故障": ["续航异常", "充电故障", "电池过热", "电池漏液", "BMS故障"],
    # 电机故障
    "电机故障": ["动力下降", "异响抖动", "过热保护", "电机进水", "控制器故障"],
    # 电控故障
    "电控故障": ["系统故障", "传感器故障", "线路故障", "软件故障", "通讯故障"],
    # 安全系统
    "安全系统": ["气囊故障", "刹车故障", "转向故障", "胎压异常", "安全预警"],
    # 其他故障
    "其他故障": ["空调故障", "门窗故障", "灯光故障", "仪表故障", "其他异常"],
}


async def init():
    """初始化数据库连接"""
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def close():
    """关闭数据库连接"""
    await Tortoise.close_connections()


async def delete_level2_and_level3():
    """删除所有2级和3级菜单数据"""
    # 先获取所有parent_id > 0的记录（即非顶级菜单）
    non_top_options = await DropdownOption.filter(parent_id__gt=0).all()
    deleted_count = len(non_top_options)

    for option in non_top_options:
        await option.delete()

    return deleted_count


async def generate_meaningful_submenus():
    """生成有意义的400客服二级和三级菜单数据"""
    # 获取所有一级菜单
    level1_options = await DropdownOption.filter(parent_id=0).all()

    total_level2 = 0
    total_level3 = 0

    for level1 in level1_options:
        level1_name = level1.option_value
        class_name = level1.class_name
        tenant_id = level1.tenant_id
        app_name = level1.app_name

        # 获取该一级菜单对应的二级分类
        level2_categories = LEVEL2_CATEGORIES.get(level1_name, [])

        if not level2_categories:
            print(f"  ⚠️ 未找到 '{level1_name}' 的二级分类定义，跳过")
            continue

        print(f"\n📁 {level1_name} (id: {level1.id})")

        for level2_name in level2_categories:
            # 创建二级菜单
            level2_option = await DropdownOption.create(
                summary=f"{level1_name} - {level2_name}",
                description=f"{level1_name}业务类型下的{level2_name}分类，用于处理客户关于{level2_name}的相关咨询、投诉或建议",
                class_name=class_name,
                tenant_id=tenant_id,
                app_name=app_name,
                parent_id=level1.id,
                option_value=level2_name
            )
            total_level2 += 1
            print(f"  📂 {level2_name} (id: {level2_option.id})")

            # 获取该二级菜单对应的三级选项
            level3_options = LEVEL3_OPTIONS.get(level2_name, [])

            if level3_options:
                for level3_name in level3_options[:3]:  # 每个二级菜单最多3个三级选项
                    level3_option = await DropdownOption.create(
                        summary=f"{level1_name} - {level2_name} - {level3_name}",
                        description=f"{level2_name}分类下的{level3_name}具体事项，客户可反馈关于{level3_name}的详细问题",
                        class_name=class_name,
                        tenant_id=tenant_id,
                        app_name=app_name,
                        parent_id=level2_option.id,
                        option_value=level3_name
                    )
                    total_level3 += 1
                    print(f"    📄 {level3_name} (id: {level3_option.id})")

    return total_level2, total_level3


async def main():
    await init()

    try:
        print("=" * 60)
        print("🗑️  第一步：删除现有的2/3级数据")
        print("=" * 60)

        deleted_count = await delete_level2_and_level3()
        print(f"✅ 已删除 {deleted_count} 条2/3级菜单数据")

        print("\n" + "=" * 60)
        print("📝 第二步：生成有意义的400客服数据")
        print("=" * 60)

        level2_count, level3_count = await generate_meaningful_submenus()

        print("\n" + "=" * 60)
        print("📊 数据生成统计")
        print("=" * 60)

        # 统计各级菜单数量
        level1_count = await DropdownOption.filter(parent_id=0).count()
        print(f"一级菜单数量: {level1_count}")
        print(f"二级菜单数量: {level2_count}")
        print(f"三级菜单数量: {level3_count}")
        print(f"总记录数: {level1_count + level2_count + level3_count}")
        print("=" * 60)

    finally:
        await close()


if __name__ == "__main__":
    asyncio.run(main())
