#!/usr/bin/env python3
"""
创建 400 汽车客服工单事件类型规则

规则字段（共 6 个）：
- level1_label: 一级事件类型名称
- level2_label: 二级事件类型名称
- level3_label: 三级事件类型名称
- level1_instruction: 一级填写说明
- level2_instruction: 二级填写说明
- level3_instruction: 三级填写说明
"""
import asyncio
import sys

sys.path.insert(0, "/Users/lu/code/code/py/autofill")

from tortoise import Tortoise

from app.core.ctx import Ctx
from app.models.rule_management import RuleInfo
from app.repositories import rule_info_repository
from app.services.rule_management.rule_service import rule_service
from app.settings import TORTOISE_ORM

# 租户 ID 与现有测试规则保持一致
TENANT_ID = 20
APP_NAME = "autofill"
RULE_NAME = "400汽车客服工单事件类型"
RULE_CODE = "cs400_event_types"
RULE_DESC = "400 汽车客服热线工单的三级事件类型及各级填写说明"

HEADERS = [
    "level1_label",
    "level2_label",
    "level3_label",
    "level1_instruction",
    "level2_instruction",
    "level3_instruction",
]

# 一级：道路救援、车辆质量、保养维修、客户服务
EVENT_TYPES = [
    # ========== 道路救援 ==========
    {
        "level1": "道路救援",
        "level1_instruction": "适用于车辆因故障、事故等原因无法继续行驶，需要救援服务。需优先确认人员安全和车辆准确位置。",
        "children": [
            {
                "level2": "拖车服务",
                "level2_instruction": "车辆无法自行移动或高速/危险路段必须拖离时使用。需确认道路环境、车辆损坏程度和目的地。",
                "children": [
                    {
                        "level3": "标准拖车",
                        "level3_instruction": "普通道路拖车。必填：车辆准确位置、拖车目的地、车辆当前状态（能否挂挡/方向盘是否锁死）、联系人电话。",
                    },
                    {
                        "level3": "高速紧急拖车",
                        "level3_instruction": "高速公路或快速路紧急拖车。必填：具体桩号/收费站、人员安全状况、是否影响交通、车上人数、拖车目的地。",
                    },
                ],
            },
            {
                "level2": "现场抢修",
                "level2_instruction": "可现场修复的简易故障。需确认现场条件、维修可行性和所需工具配件。",
                "children": [
                    {
                        "level3": "电瓶搭电",
                        "level3_instruction": "电瓶亏电导致无法启动。必填：停放时长、上次正常行驶时间、仪表盘指示、周边环境。",
                    },
                    {
                        "level3": "轮胎更换",
                        "level3_instruction": "爆胎或轮胎损坏。必填：损坏轮胎位置、备胎是否可用、当前路况、车辆能否短距离移动。",
                    },
                ],
            },
        ],
    },
    # ========== 车辆质量 ==========
    {
        "level1": "车辆质量",
        "level1_instruction": "车辆质量相关咨询、报修或投诉。需确认问题现象、发生条件、车辆基本信息和首次发现时间。",
        "children": [
            {
                "level2": "动力系统",
                "level2_instruction": "发动机、电机、电池等动力相关异常。需确认可行驶性、故障灯状态和异常声音/抖动。",
                "children": [
                    {
                        "level3": "无法启动",
                        "level3_instruction": "车辆无法启动。必填：启动时声音/灯光表现、故障灯状态、电瓶状态、上次熄火时间。",
                    },
                    {
                        "level3": "发动机异响",
                        "level3_instruction": "发动机舱异响、抖动或动力下降。必填：发生转速/车速、冷热车是否都有、是否影响行驶。",
                    },
                ],
            },
            {
                "level2": "车身外观",
                "level2_instruction": "漆面、钣金、锈蚀、密封等外观质量问题。需确认损伤部位、发现时间和是否发生过事故。",
                "children": [
                    {
                        "level3": "漆面损伤",
                        "level3_instruction": "漆面划痕、掉漆、色差或起泡。必填：损伤部位、面积、发现时间、是否有事故/维修史。",
                    },
                    {
                        "level3": "钣金变形",
                        "level3_instruction": "车身凹陷、变形、缝隙不均或异响。必填：部位、首次发现时间、是否因事故造成。",
                    },
                ],
            },
        ],
    },
    # ========== 保养维修 ==========
    {
        "level1": "保养维修",
        "level1_instruction": "定期保养、故障维修预约与跟进。需确认车辆里程、预约时间和客户到店/上门偏好。",
        "children": [
            {
                "level2": "常规保养",
                "level2_instruction": "按里程或周期进行的预防性保养。需确认保养类型、里程和上次保养时间。",
                "children": [
                    {
                        "level3": "小保养",
                        "level3_instruction": "机油机滤等常规项目。必填：当前里程、上次保养时间/里程、车辆年限。",
                    },
                    {
                        "level3": "大保养",
                        "level3_instruction": "多系统深度保养。必填：当前里程、需要更换的大件、车辆年限。",
                    },
                ],
            },
            {
                "level2": "故障维修",
                "level2_instruction": "车辆故障需要诊断维修。需确认故障现象、可行驶性和预约方式。",
                "children": [
                    {
                        "level3": "进店检修",
                        "level3_instruction": "车辆到店进行故障诊断维修。必填：故障现象、可行驶性、期望到店时间。",
                    },
                    {
                        "level3": "上门检测",
                        "level3_instruction": "预约技师上门检测。必填：地址、联系方式、检测项目和可上门时间。",
                    },
                ],
            },
        ],
    },
    # ========== 客户服务 ==========
    {
        "level1": "客户服务",
        "level1_instruction": "投诉建议、会员权益、账户相关服务。需确认客户身份、诉求和期望处理方式。",
        "children": [
            {
                "level2": "投诉建议",
                "level2_instruction": "对服务、价格、维修质量等提出投诉或建议。需确认对象、时间和客户诉求。",
                "children": [
                    {
                        "level3": "服务态度",
                        "level3_instruction": "对门店、热线或救援人员服务态度不满。必填：发生时间、涉及人员、具体行为和期望处理结果。",
                    },
                    {
                        "level3": "价格争议",
                        "level3_instruction": "对工时费、配件价或套餐价格有异议。必填：争议项目、金额、报价依据和客户期望。",
                    },
                ],
            },
            {
                "level2": "会员服务",
                "level2_instruction": "会员权益、积分、账户相关咨询与办理。需确认会员账号和具体业务类型。",
                "children": [
                    {
                        "level3": "权益查询",
                        "level3_instruction": "查询会员权益、有效期或使用规则。必填：会员账号/手机号、权益类型。",
                    },
                    {
                        "level3": "积分问题",
                        "level3_instruction": "积分余额、明细、兑换或异常问题。必填：会员账号/手机号、积分变动情况。",
                    },
                ],
            },
        ],
    },
]


def build_rows() -> list:
    rows = []
    for l1 in EVENT_TYPES:
        for l2 in l1["children"]:
            for l3 in l2["children"]:
                rows.append([
                    l1["level1"],
                    l2["level2"],
                    l3["level3"],
                    l1["level1_instruction"],
                    l2["level2_instruction"],
                    l3["level3_instruction"],
                ])
    return rows


async def main():
    await Tortoise.init(config=TORTOISE_ORM)
    Ctx.set_request_tenant_id(TENANT_ID)

    # 如果规则已存在则复用，否则创建
    rule = await rule_info_repository.filter(rule_code=RULE_CODE).first()
    if rule:
        print(f"Rule already exists: id={rule.id}, name={rule.rule_name}")
    else:
        rule = await rule_service.create_rule(
            rule_name=RULE_NAME,
            desc=RULE_DESC,
            rule_code=RULE_CODE,
            app_name=APP_NAME,
        )
        print(f"Created rule: id={rule.id}, name={rule.rule_name}, code={rule.rule_code}")

    content_json = {
        "headers": HEADERS,
        "data": build_rows(),
    }

    version = await rule_service.save_version(
        rule=rule,
        content_json=content_json,
        current_md5="",
        remark="初始版本：400 汽车客服工单三级事件类型",
    )
    print(f"Saved version: version_no={version.version_no}, collection={version.seekdb_collection_name}")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
