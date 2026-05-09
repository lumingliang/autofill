#!/usr/bin/env python3
"""
为字段组添加输出模板配置
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from tortoise import Tortoise
from app.models.autofill import FieldGroupConfig

# 数据库配置
DB_CONFIG = {
    "connections": {
        "default": "sqlite:///Users/lu/code/code/py/autofill/autofill.db"
    },
    "apps": {
        "models": {
            "models": ["app.models.autofill", "app.models.llm_config"],
            "default_connection": "default",
        }
    }
}

async def init_db():
    """初始化数据库连接"""
    await Tortoise.init(config=DB_CONFIG)

async def close_db():
    """关闭数据库连接"""
    await Tortoise.close_connections()

async def add_output_templates():
    """为字段组添加输出模板"""
    await init_db()
    
    try:
        # 获取所有字段组
        groups = await FieldGroupConfig.filter(tenant_id=1, app_name='autofill').all()
        
        print(f"找到 {len(groups)} 个字段组")
        
        for group in groups:
            print(f"\n处理字段组: {group.group_name}")
            print(f"当前输出模板: {group.output_templates}")
            
            # 根据字段组名称设置不同的输出模板
            if group.group_name == "服务记录-保养预约":
                output_templates = {
                    "summary": "客户{{customer_name}}预约了{{maintenance_type}}，预约时间：{{appointment_date}} {{appointment_time}}，门店：{{preferred_store}}。",
                    "detail": "【保养预约详情】\n客户姓名：{{customer_name}}\n联系电话：{{contact_phone}}\n车辆型号：{{vehicle_system}}\n车架号：{{vin_code}}\n预约类型：{{maintenance_type}}\n预约时间：{{appointment_date}} {{appointment_time}}\n预约门店：{{preferred_store}}\n服务顾问：{{service_advisor}}\n指定项目：{{specified_items}}\n备注：{{remarks}}"
                }
            elif group.group_name == "服务记录-道路救援请求":
                output_templates = {
                    "summary": "客户{{customer_name}}请求道路救援，车辆位置：{{vehicle_location}}，救援类型：{{rescue_type}}。",
                    "detail": "【道路救援详情】\n客户姓名：{{customer_name}}\n联系电话：{{contact_phone}}\n车辆型号：{{vehicle_system}}\n车架号：{{vin_code}}\n车辆位置：{{vehicle_location}}\n故障描述：{{fault_description}}\n救援类型：{{rescue_type}}\n目的地：{{destination}}\n是否安全停放：{{is_safe_parked}}"
                }
            elif group.group_name == "服务记录-漆面质量问题":
                output_templates = {
                    "summary": "客户{{customer_name}}反馈漆面质量问题，问题类型：{{paint_issue_type}}。",
                    "detail": "【漆面质量问题详情】\n客户姓名：{{customer_name}}\n联系电话：{{contact_phone}}\n车辆型号：{{vehicle_system}}\n车架号：{{vin_code}}\n问题类型：{{paint_issue_type}}\n影响部位：{{affected_part}}\n客户诉求：{{customer_demand}}\n是否提供照片：{{has_photos}}\n检测安排：{{inspection_arrangement}}"
                }
            else:
                # 为其他字段组添加默认模板
                output_templates = {
                    "summary": "字段组 {{group_name}} 的数据已提取完成。",
                    "detail": "【{{group_name}} 详情】\n数据已提取，请查看具体字段值。"
                }
            
            # 更新字段组
            group.output_templates = output_templates
            await group.save()
            
            print(f"已添加输出模板: {list(output_templates.keys())}")
        
        print("\n✓ 所有字段组的输出模板已更新")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(add_output_templates())
