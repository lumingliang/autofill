#!/usr/bin/env python3
"""
测试接口服务 - 端口6666
提供自动填单相关的测试接口
"""

from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
import uvicorn
from typing import Dict, Any, List, Optional
import csv
import os

app = FastAPI(title="Autofill Test API", version="1.0.0")

# ==================== 数据加载 ====================

def load_event_types() -> List[Dict[str, Any]]:
    """加载事件类型数据"""
    data = []
    csv_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "data", "event_types.csv")
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    return data

def load_templates() -> List[Dict[str, Any]]:
    """加载模板数据"""
    data = []
    csv_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "data", "templates_export.csv")
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    return data

# 加载数据
EVENT_TYPES_DATA = load_event_types()
TEMPLATES_DATA = load_templates()

# ==================== 表单字段定义 ====================

FORM_FIELDS = [
    {
        "field_id": "event_type_level1",
        "field_name": "一级事件类型",
        "field_type": "dropdown",
        "required": True,
        "description": "请选择一级事件类型",
        "placeholder": "请选择",
        "order": 1,
        "cascade": True,
        "has_children": True
    },
    {
        "field_id": "event_type_level2",
        "field_name": "二级事件类型",
        "field_type": "dropdown",
        "required": True,
        "description": "请选择二级事件类型",
        "placeholder": "请先选择一级事件类型",
        "order": 2,
        "cascade": True,
        "parent_field": "event_type_level1",
        "has_children": True
    },
    {
        "field_id": "event_type_level3",
        "field_name": "三级事件类型",
        "field_type": "dropdown",
        "required": True,
        "description": "请选择三级事件类型",
        "placeholder": "请先选择二级事件类型",
        "order": 3,
        "cascade": True,
        "parent_field": "event_type_level2",
        "has_children": False
    },
    {
        "field_id": "service_summary",
        "field_name": "服务记录总结",
        "field_type": "textarea",
        "required": True,
        "description": "请填写服务记录总结",
        "placeholder": "根据选择的模板自动生成或手动填写",
        "order": 4,
        "template_based": True,
        "min_length": 10,
        "max_length": 2000
    }
]

# ==================== 字段填写规则定义 ====================

FIELD_RULES = {
    "event_type_level1": {
        "field_id": "event_type_level1",
        "field_name": "一级事件类型",
        "field_type": "dropdown",
        "required": True,
        "description": "请选择一级事件类型，这是事件分类的最高层级",
        "validation_rules": [
            {"type": "required", "message": "一级事件类型不能为空", "severity": "error"},
            {"type": "enum", "message": "请选择有效的一级事件类型", "severity": "error"}
        ],
        "business_rules": [
            {"rule": "必须先选择一级事件类型才能选择二级", "affects": "event_type_level2"},
            {"rule": "一级事件类型决定后续可选的服务模板", "affects": "service_summary"}
        ],
        "options": [
            {"option_id": "EVT001", "option_name": "道路救援", "description": "车辆故障无法行驶，需要现场救援或拖车服务"},
            {"option_id": "EVT002", "option_name": "保养预约", "description": "定期保养或指定项目的保养服务预约"},
            {"option_id": "EVT003", "option_name": "质量问题", "description": "车辆质量相关问题，包括车身、动力系统等"}
        ]
    },
    "event_type_level2": {
        "field_id": "event_type_level2",
        "field_name": "二级事件类型",
        "field_type": "dropdown",
        "required": True,
        "description": "请选择二级事件类型，细化事件分类",
        "validation_rules": [
            {"type": "required", "message": "二级事件类型不能为空", "severity": "error"},
            {"type": "enum", "message": "请选择有效的二级事件类型", "severity": "error"},
            {"type": "cascade", "message": "请先选择一级事件类型", "depends_on": "event_type_level1", "severity": "error"}
        ],
        "cascade_rule": {
            "parent_field": "event_type_level1",
            "query_order": 2,
            "cascade_logic": "根据一级事件类型ID过滤二级选项"
        },
        "business_rules": [
            {"rule": "二级事件类型必须与一级事件类型关联", "affects": "self"},
            {"rule": "必须先选择二级事件类型才能选择三级", "affects": "event_type_level3"}
        ]
    },
    "event_type_level3": {
        "field_id": "event_type_level3",
        "field_name": "三级事件类型",
        "field_type": "dropdown",
        "required": True,
        "description": "请选择三级事件类型，最具体的事件分类",
        "validation_rules": [
            {"type": "required", "message": "三级事件类型不能为空", "severity": "error"},
            {"type": "enum", "message": "请选择有效的三级事件类型", "severity": "error"},
            {"type": "cascade", "message": "请先选择二级事件类型", "depends_on": "event_type_level2", "severity": "error"}
        ],
        "cascade_rule": {
            "parent_field": "event_type_level2",
            "query_order": 3,
            "cascade_logic": "根据二级事件类型ID过滤三级选项"
        },
        "business_rules": [
            {"rule": "三级事件类型是最具体的分类，决定服务模板", "affects": "service_summary"},
            {"rule": "三级事件类型ID用于获取对应的服务记录模板", "affects": "template_selection"}
        ]
    },
    "service_summary": {
        "field_id": "service_summary",
        "field_name": "服务记录总结",
        "field_type": "textarea",
        "required": True,
        "description": "请填写服务记录总结，系统会根据选择的事件类型自动推荐模板",
        "placeholder": "根据选择的模板自动生成或手动填写",
        "min_length": 10,
        "max_length": 2000,
        "validation_rules": [
            {"type": "required", "message": "服务记录总结不能为空", "severity": "error"},
            {"type": "min_length", "value": 10, "message": "服务记录总结至少需要10个字符", "severity": "error"},
            {"type": "max_length", "value": 2000, "message": "服务记录总结不能超过2000个字符", "severity": "error"},
            {"type": "pattern", "value": "【.+】", "message": "建议按照模板格式填写，包含【】标记的章节", "severity": "warning"}
        ],
        "template_based": True,
        "auto_generate": {
            "enabled": True,
            "description": "根据三级事件类型自动获取对应模板",
            "template_api": "/api/templates/{event_type_id}",
            "variable_extraction": "从对话中提取客户信息、车辆信息、问题描述等变量"
        },
        "business_rules": [
            {"rule": "服务记录总结必须基于选择的三级事件类型模板生成", "affects": "self"},
            {"rule": "必须包含客户联系方式和车辆位置等关键信息", "affects": "self"},
            {"rule": "紧急事件需要标注优先级和处理时限", "affects": "self"}
        ]
    }
}

# ==================== 选项填写说明映射 ====================

OPTION_FILL_INSTRUCTIONS = {
    # ========== 一级事件类型 ==========
    "EVT001": {
        "instruction": "道路救援类事件，包括拖车、现场维修等服务。需要记录车辆位置、故障现象、客户联系方式。",
        "required_fields": ["vehicle_location", "contact_phone", "fault_description"],
        "priority": "high",
        "response_time": "30分钟内响应",
        "key_points": ["确认车辆位置", "确认人员安全", "确认故障现象"]
    },
    "EVT002": {
        "instruction": "保养预约类事件，包括定期保养、指定项目保养等。需要记录预约时间、保养类型、车辆信息。",
        "required_fields": ["appointment_date", "appointment_time", "maintenance_type", "vehicle_system"],
        "priority": "normal",
        "response_time": "2小时内确认",
        "key_points": ["确认保养类型", "确认预约时间", "确认车辆信息"]
    },
    "EVT003": {
        "instruction": "质量问题类事件，包括漆面、钣金、发动机等质量问题。需要记录问题描述、发现时间、客户诉求。",
        "required_fields": ["issue_description", "issue_found_date", "customer_demand"],
        "priority": "high",
        "response_time": "1小时内响应",
        "key_points": ["确认问题类型", "确认发现时间", "确认客户诉求"]
    },
    
    # ========== 二级事件类型 - 道路救援 ==========
    "EVT001001": {
        "instruction": "拖车服务，需要明确拖车类型（标准/紧急）、车辆位置、目的地。车辆无法移动时必须选择此项。",
        "required_fields": ["vehicle_location", "destination", "rescue_type"],
        "priority": "high",
        "response_time": "30分钟内到达",
        "key_points": ["确认车辆位置", "确认目的地", "确认车辆能否移动"]
    },
    "EVT001002": {
        "instruction": "现场维修服务，需要明确故障类型、现场条件、维修可行性。适用于电瓶亏电、轮胎问题等可现场修复的故障。",
        "required_fields": ["vehicle_location", "fault_description", "startup_issue_type"],
        "priority": "high",
        "response_time": "45分钟内到达",
        "key_points": ["确认故障类型", "确认现场条件", "确认维修可行性"]
    },
    
    # ========== 二级事件类型 - 保养预约 ==========
    "EVT002001": {
        "instruction": "定期保养服务，需要明确保养类型（小保养/大保养）、预约时间、车辆里程。",
        "required_fields": ["appointment_date", "appointment_time", "maintenance_type", "mileage"],
        "priority": "normal",
        "response_time": "2小时内确认",
        "key_points": ["确认保养类型", "确认车辆里程", "确认上次保养时间"]
    },
    "EVT002002": {
        "instruction": "指定项目保养，需要明确指定项目、问题描述、预约时间。针对特定系统的保养需求。",
        "required_fields": ["appointment_date", "appointment_time", "specified_items", "issue_description"],
        "priority": "normal",
        "response_time": "2小时内确认",
        "key_points": ["确认指定项目", "确认问题描述", "确认预约时间"]
    },
    
    # ========== 二级事件类型 - 质量问题 ==========
    "EVT003001": {
        "instruction": "车身质量问题，需要明确问题类型（漆面/钣金）、问题部位、发现时间。",
        "required_fields": ["paint_issue_type", "affected_part", "issue_found_date"],
        "priority": "high",
        "response_time": "1小时内响应",
        "key_points": ["确认问题类型", "确认问题部位", "确认是否有事故史"]
    },
    "EVT003002": {
        "instruction": "动力系统问题，需要明确故障现象、发生条件、车辆状态。包括发动机、电池等核心部件问题。",
        "required_fields": ["fault_description", "noise_condition", "vehicle_status"],
        "priority": "urgent",
        "response_time": "30分钟内响应",
        "key_points": ["确认故障现象", "确认发生条件", "确认车辆可行驶性"]
    },
    
    # ========== 三级事件类型 - 拖车服务 ==========
    "EVT001001001": {
        "instruction": "标准拖车服务，适用于一般道路故障。记录车辆位置、故障原因、拖车目的地。",
        "required_fields": ["vehicle_location", "fault_description", "destination"],
        "priority": "normal",
        "response_time": "60分钟内到达",
        "key_points": ["确认准确位置", "确认故障原因", "确认目的地"]
    },
    "EVT001001002": {
        "instruction": "紧急拖车服务，适用于高速公路等紧急情况。优先处理，记录准确位置、安全状况。",
        "required_fields": ["vehicle_location", "is_safe_parked", "affect_traffic", "passenger_count"],
        "priority": "urgent",
        "response_time": "30分钟内到达",
        "key_points": ["确认人员安全", "确认是否影响交通", "确认车上人数", "确认准确位置"]
    },
    
    # ========== 三级事件类型 - 现场维修 ==========
    "EVT001002001": {
        "instruction": "电瓶搭电服务，记录车辆位置、电瓶状态、尝试启动次数。适用于电瓶亏电无法启动。",
        "required_fields": ["vehicle_location", "parking_duration", "last_drive_normal"],
        "priority": "high",
        "response_time": "45分钟内到达",
        "key_points": ["确认停放时间", "确认上次行驶是否正常", "确认天气情况"]
    },
    "EVT001002002": {
        "instruction": "更换轮胎服务，记录车辆位置、轮胎状况、备胎可用性。适用于爆胎或轮胎损坏。",
        "required_fields": ["vehicle_location", "road_condition", "current_location"],
        "priority": "high",
        "response_time": "45分钟内到达",
        "key_points": ["确认轮胎损坏情况", "确认备胎可用性", "确认路况"]
    },
    "EVT001002003": {
        "instruction": "送油服务，记录车辆位置、油量状态、燃油类型。适用于燃油耗尽。",
        "required_fields": ["vehicle_location", "current_location"],
        "priority": "high",
        "response_time": "60分钟内到达",
        "key_points": ["确认燃油类型", "确认准确位置", "确认安全停车"]
    },
    
    # ========== 三级事件类型 - 定期保养 ==========
    "EVT002001001": {
        "instruction": "小保养服务，记录预约时间、车辆里程、上次保养时间。包括机油机滤更换等常规项目。",
        "required_fields": ["appointment_date", "appointment_time", "mileage", "last_maintenance_date"],
        "priority": "normal",
        "response_time": "2小时内确认",
        "key_points": ["确认车辆里程", "确认上次保养时间", "确认保养项目"]
    },
    "EVT002001002": {
        "instruction": "大保养服务，记录预约时间、车辆里程、需要更换的大件。包括更多检查和更换项目。",
        "required_fields": ["appointment_date", "appointment_time", "mileage", "specified_items"],
        "priority": "normal",
        "response_time": "2小时内确认",
        "key_points": ["确认车辆里程", "确认需要更换的大件", "确认预约时间"]
    },
    
    # ========== 三级事件类型 - 指定项目 ==========
    "EVT002002001": {
        "instruction": "刹车系统保养，记录刹车异常现象、预约时间、行驶里程。包括刹车片、刹车盘检查更换。",
        "required_fields": ["appointment_date", "appointment_time", "brake_effectiveness", "speed_when_occurred"],
        "priority": "high",
        "response_time": "1小时内确认",
        "key_points": ["确认刹车异常现象", "确认制动效果", "确认是否可行驶"]
    },
    "EVT002002002": {
        "instruction": "空调系统保养，记录空调问题、预约时间、车辆信息。包括制冷效果检查、冷媒添加等。",
        "required_fields": ["appointment_date", "appointment_time", "ac_issue_type", "issue_duration"],
        "priority": "normal",
        "response_time": "2小时内确认",
        "key_points": ["确认空调问题类型", "确认问题持续时间", "确认环境温度"]
    },
    
    # ========== 三级事件类型 - 车身质量 ==========
    "EVT003001001": {
        "instruction": "漆面质量问题，记录问题类型、问题部位、发现时间、是否有事故史。包括色差、起泡、脱落等。",
        "required_fields": ["paint_issue_type", "affected_part", "issue_found_date", "has_accident_history"],
        "priority": "normal",
        "response_time": "4小时内响应",
        "key_points": ["确认问题类型", "确认问题部位", "确认是否有事故史", "确认是否有照片"]
    },
    "EVT003001002": {
        "instruction": "钣金质量问题，记录异响位置、发生条件、首次出现时间。包括变形、异响、缝隙等。",
        "required_fields": ["noise_location", "noise_condition", "first_occurrence_date"],
        "priority": "normal",
        "response_time": "4小时内响应",
        "key_points": ["确认异响位置", "确认发生条件", "确认首次出现时间"]
    },
    
    # ========== 三级事件类型 - 动力系统 ==========
    "EVT003002001": {
        "instruction": "发动机故障，记录故障现象、故障灯状态、车辆可行驶性。包括异响、抖动、动力下降等。",
        "required_fields": ["fault_description", "warning_light_status", "drivable_status"],
        "priority": "urgent",
        "response_time": "30分钟内响应",
        "key_points": ["确认故障现象", "确认故障灯状态", "确认是否可行驶", "确认发生条件"]
    },
    "EVT003002002": {
        "instruction": "电池问题，记录电池报警类型、剩余电量、车辆状态。包括续航异常、充电故障等。",
        "required_fields": ["battery_warning_type", "soc", "vehicle_status", "remaining_range"],
        "priority": "urgent",
        "response_time": "30分钟内响应",
        "key_points": ["确认电池报警类型", "确认剩余电量", "确认车辆状态", "确认是否需要拖车"]
    },
}

# ==================== 辅助函数 ====================

def get_level1_options() -> List[Dict[str, Any]]:
    options = []
    seen = set()
    for row in EVENT_TYPES_DATA:
        key = row.get("一级事件类型ID", "")
        if key and key not in seen:
            seen.add(key)
            options.append({
                "id": key,
                "label": row.get("一级事件类型", ""),
                "value": key
            })
    return options

def get_level2_options(level1_id: str) -> List[Dict[str, Any]]:
    options = []
    seen = set()
    for row in EVENT_TYPES_DATA:
        if row.get("一级事件类型ID") == level1_id:
            key = row.get("二级事件类型ID", "")
            if key and key not in seen:
                seen.add(key)
                options.append({
                    "id": key,
                    "label": row.get("二级事件类型", ""),
                    "value": key
                })
    return options

def get_level3_options(level2_id: str) -> List[Dict[str, Any]]:
    options = []
    for row in EVENT_TYPES_DATA:
        if row.get("二级事件类型ID") == level2_id:
            options.append({
                "id": row.get("三级事件类型ID", ""),
                "label": row.get("三级事件类型", ""),
                "value": row.get("三级事件类型ID", "")
            })
    return options

def get_option_fill_instruction(option_id: str) -> Optional[Dict[str, Any]]:
    """获取选项的填写说明"""
    return OPTION_FILL_INSTRUCTIONS.get(option_id)

def get_template_by_event_type(event_type_id: str) -> Optional[Dict[str, Any]]:
    """根据事件类型ID获取模板"""
    # 映射三级事件类型到模板
    template_mapping = {
        # 道路救援 - 拖车服务
        "EVT001001001": "1",  # 标准拖车 -> 道路救援请求
        "EVT001001002": "1",  # 紧急拖车 -> 道路救援请求
        # 道路救援 - 现场维修
        "EVT001002001": "5",  # 电瓶搭电 -> 车辆无法启动
        "EVT001002002": "1",  # 更换轮胎 -> 道路救援请求
        "EVT001002003": "1",  # 送油服务 -> 道路救援请求
        # 保养预约
        "EVT002001001": "2",  # 小保养 -> 保养预约
        "EVT002001002": "2",  # 大保养 -> 保养预约
        "EVT002002001": "6",  # 刹车系统 -> 制动系统报警
        "EVT002002002": "7",  # 空调系统 -> 空调制冷异常
        # 质量问题
        "EVT003001001": "3",  # 漆面问题 -> 漆面质量问题
        "EVT003001002": "4",  # 钣金问题 -> 异响投诉
        "EVT003002001": "4",  # 发动机故障 -> 异响投诉
        "EVT003002002": "9",  # 电池问题 -> 动力电池故障
    }

    template_id = template_mapping.get(event_type_id)
    if template_id:
        for template in TEMPLATES_DATA:
            if template.get("id") == template_id:
                return template
    return None

def extract_template_variables(template_content: str) -> List[Dict[str, Any]]:
    """从模板内容中提取变量"""
    import re
    variables = []
    pattern = r'\$\{(\w+)\}'
    matches = re.findall(pattern, template_content)

    # 变量描述映射
    var_descriptions = {
        "customer_name": {"desc": "客户姓名", "required": True},
        "contact_phone": {"desc": "联系电话", "required": True},
        "vehicle_system": {"desc": "车系", "required": True},
        "vin_code": {"desc": "车架号", "required": False},
        "mileage": {"desc": "行驶里程", "required": False},
        "fault_description": {"desc": "故障现象", "required": True},
        "vehicle_location": {"desc": "车辆位置", "required": True},
        "rescue_type": {"desc": "救援需求", "required": True},
        "expected_time": {"desc": "期望到达时间", "required": False},
        "is_safe_parked": {"desc": "是否安全停放", "required": False},
        "affect_traffic": {"desc": "是否影响交通", "required": False},
        "passenger_count": {"desc": "车上人数", "required": False},
        "rescue_arrangement": {"desc": "救援安排", "required": False},
        "eta": {"desc": "预计到达时间", "required": False},
        "destination": {"desc": "拖车目的地", "required": False},
        "remarks": {"desc": "客服备注", "required": False},
        "maintenance_type": {"desc": "保养类型", "required": True},
        "specified_items": {"desc": "指定项目", "required": False},
        "appointment_date": {"desc": "预约日期", "required": True},
        "appointment_time": {"desc": "预约时间", "required": True},
        "preferred_store": {"desc": "偏好服务店", "required": False},
        "need_pickup": {"desc": "是否需要接送车", "required": False},
        "need_loaner": {"desc": "是否需要备用车", "required": False},
        "last_maintenance_date": {"desc": "上次保养时间", "required": False},
        "last_maintenance_mileage": {"desc": "上次保养里程", "required": False},
        "appointment_no": {"desc": "预约单号", "required": False},
        "service_advisor": {"desc": "服务顾问", "required": False},
        "paint_issue_type": {"desc": "漆面问题类型", "required": True},
        "affected_part": {"desc": "问题部位", "required": True},
        "issue_found_date": {"desc": "发现问题时间", "required": False},
        "has_accident_history": {"desc": "是否发生事故", "required": False},
        "has_photos": {"desc": "是否有照片", "required": False},
        "has_video": {"desc": "是否有视频", "required": False},
        "customer_demand": {"desc": "客户诉求", "required": True},
        "inspection_arrangement": {"desc": "检测安排", "required": False},
        "repair_duration": {"desc": "预计维修时间", "required": False},
        "provide_loaner": {"desc": "是否提供代步车", "required": False},
        "noise_type": {"desc": "异响类型", "required": True},
        "noise_location": {"desc": "异响位置", "required": True},
        "noise_condition": {"desc": "发生条件", "required": True},
        "noise_frequency": {"desc": "发生频率", "required": False},
        "first_occurrence_date": {"desc": "首次出现时间", "required": False},
        "recent_repair": {"desc": "近期是否维修", "required": False},
        "last_repair_date": {"desc": "上次维修时间", "required": False},
        "service_store": {"desc": "服务店", "required": False},
        "preliminary_diagnosis": {"desc": "初步判断", "required": False},
        "inspection_time": {"desc": "预计检测时长", "required": False},
        "startup_issue_type": {"desc": "启动问题类型", "required": True},
        "warning_light_status": {"desc": "故障灯状态", "required": False},
        "parking_duration": {"desc": "停放时间", "required": False},
        "last_drive_normal": {"desc": "上次行驶是否正常", "required": False},
        "weather_condition": {"desc": "天气情况", "required": False},
        "parking_environment": {"desc": "停车环境", "required": False},
        "has_modification": {"desc": "是否改装", "required": False},
        "modification_items": {"desc": "改装项目", "required": False},
        "current_location": {"desc": "当前位置", "required": True},
        "need_rescue": {"desc": "是否需要救援", "required": False},
        "handling_suggestion": {"desc": "处理建议", "required": False},
        "estimated_resolution_time": {"desc": "预计解决时间", "required": False},
        "brake_warning_type": {"desc": "制动报警类型", "required": True},
        "warning_time": {"desc": "报警时间", "required": False},
        "drivable_status": {"desc": "是否可行驶", "required": True},
        "brake_effectiveness": {"desc": "制动效果", "required": True},
        "speed_when_occurred": {"desc": "发生时车速", "required": False},
        "road_condition": {"desc": "路况", "required": False},
        "safety_instructions": {"desc": "安全提示", "required": False},
        "suggested_parking": {"desc": "建议停车地点", "required": False},
        "ac_issue_type": {"desc": "空调问题类型", "required": True},
        "issue_duration": {"desc": "问题持续时间", "required": False},
        "ambient_temp": {"desc": "环境温度", "required": False},
        "set_temp": {"desc": "设置温度", "required": False},
        "fan_speed": {"desc": "风量档位", "required": False},
        "ac_switch_status": {"desc": "AC开关状态", "required": False},
        "air_outlet": {"desc": "出风口", "required": False},
        "circulation_mode": {"desc": "循环模式", "required": False},
        "ac_repair_history": {"desc": "空调维修历史", "required": False},
        "last_ac_repair_date": {"desc": "上次空调维修时间", "required": False},
        "system_issue_type": {"desc": "系统问题类型", "required": True},
        "issue_frequency": {"desc": "问题频率", "required": False},
        "vehicle_status_when_issue": {"desc": "问题发生时车辆状态", "required": False},
        "trigger_operation": {"desc": "触发操作", "required": False},
        "recover_after_restart": {"desc": "重启后是否恢复", "required": False},
        "recovery_time": {"desc": "恢复时间", "required": False},
        "headunit_version": {"desc": "车机版本", "required": False},
        "phone_model": {"desc": "手机型号", "required": False},
        "app_version": {"desc": "APP版本", "required": False},
        "agree_upload_log": {"desc": "是否同意上传日志", "required": False},
        "has_evidence": {"desc": "是否有证据", "required": False},
        "remote_troubleshooting_steps": {"desc": "远程指导步骤", "required": False},
        "battery_capacity": {"desc": "电池容量", "required": False},
        "battery_warning_type": {"desc": "电池报警类型", "required": True},
        "vehicle_status": {"desc": "车辆状态", "required": True},
        "soc": {"desc": "剩余电量百分比", "required": True},
        "remaining_range": {"desc": "剩余续航里程", "required": False},
        "scenario_when_occurred": {"desc": "发生时场景", "required": False},
        "last_charging_method": {"desc": "上次充电方式", "required": False},
        "battery_impact_history": {"desc": "电池撞击历史", "required": False},
        "flood_history": {"desc": "涉水历史", "required": False},
        "need_towing": {"desc": "是否需要拖车", "required": False},
        "purchase_date": {"desc": "购车日期", "required": False},
        "scheduled_start_time": {"desc": "预约开始时间", "required": True},
        "plug_in_time": {"desc": "插枪时间", "required": False},
        "charging_issue_type": {"desc": "充电问题类型", "required": True},
        "charger_type": {"desc": "充电桩类型", "required": False},
        "charging_location": {"desc": "充电地点", "required": False},
        "soc_when_scheduled": {"desc": "预约时电量", "required": False},
        "current_soc": {"desc": "当前电量", "required": False},
        "previous_success": {"desc": "是否成功预约过", "required": False},
        "last_success_time": {"desc": "上次成功时间", "required": False},
        "headunit_report_id": {"desc": "车机上报ID", "required": False},
        "app_report_id": {"desc": "APP上报ID", "required": False},
        "has_screenshot": {"desc": "是否有截图", "required": False},
        "transferred_to_tech": {"desc": "是否转交技术部门", "required": False},
        "estimated_response_time": {"desc": "预计回复时间", "required": False},
    }

    seen = set()
    for var_name in matches:
        if var_name not in seen:
            seen.add(var_name)
            var_info = var_descriptions.get(var_name, {"desc": var_name, "required": False})
            variables.append({
                "name": var_name,
                "description": var_info["desc"],
                "required": var_info["required"]
            })

    return variables

# ==================== 接口1: 获取表单字段列表 ====================

@app.get("/api/form/fields")
async def get_form_fields(
    app_id: Optional[str] = Query(None, description="应用ID")
):
    """
    获取所有待填写的字段列表

    返回4个核心字段：
    - 一级事件类型 (dropdown)
    - 二级事件类型 (dropdown, 级联)
    - 三级事件类型 (dropdown, 级联)
    - 服务记录总结 (textarea, 模板基于)
    """
    simplified_fields = [
        {
            "field_id": f["field_id"],
            "field_name": f["field_name"],
            "field_type": f["field_type"]
        }
        for f in FORM_FIELDS
    ]
    return {
        "code": 200,
        "msg": "OK",
        "data": simplified_fields
    }

# ==================== 接口2: 获取字段详情 ====================

@app.get("/api/form/fields/{field_id}/detail")
async def get_field_detail(field_id: str):
    """
    获取指定字段的详细信息
    """
    field = next((f for f in FORM_FIELDS if f["field_id"] == field_id), None)
    if not field:
        return {
            "code": 404,
            "msg": f"Field not found: {field_id}",
            "data": None
        }

    return {
        "code": 200,
        "msg": "OK",
        "data": field
    }

# ==================== 接口3: 获取字段选项 ====================

@app.get("/api/form/fields/{field_id}/options")
async def get_field_options(
    field_id: str,
    parent_id: Optional[str] = Query(None, description="父级选项ID，用于级联查询")
):
    """
    获取下拉字段的可选值

    - field_id: event_type_level1 / event_type_level2 / event_type_level3
    - parent_id: 级联查询时传入父级选项ID
    """
    if field_id == "event_type_level1":
        options = get_level1_options()
    elif field_id == "event_type_level2":
        if not parent_id:
            return {
                "code": 400,
                "msg": "parent_id is required for level2 query",
                "data": None
            }
        options = get_level2_options(parent_id)
    elif field_id == "event_type_level3":
        if not parent_id:
            return {
                "code": 400,
                "msg": "parent_id is required for level3 query",
                "data": None
            }
        options = get_level3_options(parent_id)
    else:
        return {
            "code": 400,
            "msg": f"Field {field_id} does not support options",
            "data": None
        }

    return {
        "code": 200,
        "msg": "OK",
        "data": {
            "field_id": field_id,
            "parent_id": parent_id,
            "options": options
        }
    }

# ==================== 接口4: 获取字段规则 ====================

@app.get("/api/form/fields/{field_id}/rules")
async def get_field_rules(
    field_id: str,
    option_id: Optional[str] = Query(None, description="选项ID（指定后只返回单个选项的规则）"),
    parent_id: Optional[str] = Query(None, description="父级选项ID（级联字段过滤时使用）")
):
    """
    获取字段的填写规则和约束

    默认返回字段的验证规则、填写说明，以及该字段下所有选项的规则
    如果指定option_id，只返回该选项的填写说明（单个选项模式）
    如果指定parent_id，返回该父级下所有子选项的规则（级联过滤模式）
    """
    # 优先从 FIELD_RULES 获取完整的规则定义
    if field_id in FIELD_RULES:
        rules = FIELD_RULES[field_id].copy()
    else:
        # 回退到从 FORM_FIELDS 构建基础规则
        field = next((f for f in FORM_FIELDS if f["field_id"] == field_id), None)
        if not field:
            return {
                "code": 404,
                "msg": f"Field not found: {field_id}",
                "data": None
            }
        rules = {
            "field_id": field_id,
            "field_name": field["field_name"],
            "field_type": field["field_type"],
            "required": field["required"],
            "description": field.get("description", ""),
        }

    # 如果指定了option_id，只返回单个选项的填写说明（原有功能）
    if option_id:
        instruction = get_option_fill_instruction(option_id)
        if instruction:
            rules["option_fill_instruction"] = instruction
        return {
            "code": 200,
            "msg": "OK",
            "data": rules
        }

    options_rules = []
    
    if field_id == "event_type_level1":
        options = get_level1_options()
    elif field_id == "event_type_level2":
        if parent_id:
            options = get_level2_options(parent_id)
        else:
            options = []
            seen = set()
            for row in EVENT_TYPES_DATA:
                key = row.get("二级事件类型ID", "")
                if key and key not in seen:
                    seen.add(key)
                    options.append({
                        "id": key,
                        "label": row.get("二级事件类型", ""),
                        "value": key
                    })
    elif field_id == "event_type_level3":
        if parent_id:
            options = get_level3_options(parent_id)
        else:
            options = []
            seen = set()
            for row in EVENT_TYPES_DATA:
                key = row.get("三级事件类型ID", "")
                if key and key not in seen:
                    seen.add(key)
                    options.append({
                        "id": key,
                        "label": row.get("三级事件类型", ""),
                        "value": key
                    })
    else:
        options = []

    for option in options:
        instruction = get_option_fill_instruction(option["value"])
        options_rules.append({
            "label": option["label"],
            "value": option["value"],
            "instruction": instruction.get("instruction", "") if instruction else ""
        })

    return {
        "code": 200,
        "msg": "OK",
        "data": options_rules
    }

# ==================== 接口5: 批量获取字段规则 ====================

@app.post("/api/form/fields/rules/batch")
async def get_fields_rules_batch(request: Request):
    """
    批量获取多个字段的填写规则

    请求体：
    {
        "field_ids": ["event_type_level1", "event_type_level2", ...],
        "option_ids": ["EVT001", "EVT001001", ...]  // 可选，与field_ids对应
    }
    """
    try:
        body = await request.json()
        field_ids = body.get("field_ids", [])
        option_ids = body.get("option_ids", [])

        rules = []
        for i, field_id in enumerate(field_ids):
            # 优先从 FIELD_RULES 获取完整规则
            if field_id in FIELD_RULES:
                rule = FIELD_RULES[field_id].copy()
            else:
                # 回退到从 FORM_FIELDS 构建基础规则
                field = next((f for f in FORM_FIELDS if f["field_id"] == field_id), None)
                if not field:
                    continue
                rule = {
                    "field_id": field_id,
                    "field_name": field["field_name"],
                    "field_type": field["field_type"],
                    "required": field["required"],
                    "description": field.get("description", ""),
                }

                # 添加级联规则
                if field.get("cascade"):
                    rule["cascade_rule"] = {
                        "parent_field": field.get("parent_field"),
                        "query_order": f"请先填写{field.get('parent_field', '上级字段')}"
                    }

                # 添加长度限制
                if "min_length" in field:
                    rule["min_length"] = field["min_length"]
                    rule["max_length"] = field["max_length"]

            # 添加选项填写说明（如果提供了option_id）
            if i < len(option_ids) and option_ids[i]:
                instruction = get_option_fill_instruction(option_ids[i])
                if instruction:
                    rule["option_fill_instruction"] = instruction

            rules.append(rule)

        return {
            "code": 200,
            "msg": "OK",
            "data": {
                "field_count": len(rules),
                "rules": rules
            }
        }
    except Exception as e:
        return {
            "code": 400,
            "msg": f"Invalid request: {str(e)}",
            "data": None
        }

# ==================== 接口6: 获取服务记录模板 ====================

@app.get("/api/templates/{event_type_id}")
async def get_template(event_type_id: str):
    """
    根据三级事件类型ID获取服务记录模板

    - event_type_id: 三级事件类型ID，如 EVT001001001
    """
    template = get_template_by_event_type(event_type_id)
    if not template:
        return {
            "code": 404,
            "msg": f"Template not found for event type: {event_type_id}",
            "data": None
        }

    # 提取模板变量
    variables = extract_template_variables(template.get("template_content", ""))

    return {
        "code": 200,
        "msg": "OK",
        "data": {
            "event_type_id": event_type_id,
            "template_id": template.get("id"),
            "template_name": template.get("name"),
            "summary": template.get("summary"),
            "template_content": template.get("template_content"),
            "variables": variables,
            "variable_count": len(variables)
        }
    }

# ==================== 接口7: 获取所有模板列表 ====================

@app.get("/api/templates")
async def get_all_templates():
    """
    获取所有可用的服务记录模板
    """
    templates = []
    for template in TEMPLATES_DATA:
        templates.append({
            "template_id": template.get("id"),
            "template_name": template.get("name"),
            "summary": template.get("summary"),
            "variable_count": len(extract_template_variables(template.get("template_content", "")))
        })

    return {
        "code": 200,
        "msg": "OK",
        "data": {
            "template_count": len(templates),
            "templates": templates
        }
    }

# ==================== 接口7.5: 根据模板ID获取模板内容 ====================

@app.get("/api/templates/{template_id}/content")
async def get_template_content_by_id(template_id: str):
    """
    根据模板ID获取模板内容

    - template_id: 模板ID，如 1, 2, 3...
    """
    template = None
    for t in TEMPLATES_DATA:
        if t.get("id") == template_id:
            template = t
            break

    if not template:
        return {
            "code": 404,
            "msg": f"Template not found: {template_id}",
            "data": None
        }

    # 提取模板变量
    variables = extract_template_variables(template.get("template_content", ""))

    return {
        "code": 200,
        "msg": "OK",
        "data": {
            "template_id": template_id,
            "template_name": template.get("name"),
            "summary": template.get("summary"),
            "template_content": template.get("template_content"),
            "variables": variables,
            "variable_count": len(variables)
        }
    }

# ==================== 接口8: 根据一级事件类型获取模板列表 ====================

@app.get("/api/templates/list/{level1_id}")
async def get_templates_by_level1(level1_id: str):
    """
    根据一级事件类型ID获取可用的模板列表

    - level1_id: 一级事件类型ID，如 EVT001
    """
    # 模板与一级事件类型的映射关系
    template_mapping = {
        "EVT001": ["1", "5"],  # 道路救援 -> 道路救援请求、车辆无法启动
        "EVT002": ["2", "6", "7"],  # 保养预约 -> 保养预约、制动系统报警、空调制冷异常
        "EVT003": ["3", "4", "9"],  # 质量问题 -> 漆面质量问题、异响投诉、动力电池故障
    }

    template_ids = template_mapping.get(level1_id, [])
    templates = []

    for template_id in template_ids:
        for template in TEMPLATES_DATA:
            if template.get("id") == template_id:
                templates.append({
                    "template_id": template.get("id"),
                    "template_name": template.get("name"),
                    "summary": template.get("summary"),
                    "variable_count": len(extract_template_variables(template.get("template_content", "")))
                })

    return {
        "code": 200,
        "msg": "OK",
        "data": {
            "level1_id": level1_id,
            "template_count": len(templates),
            "templates": templates
        }
    }


# ==================== 接口9: 获取模板规则 ====================

@app.get("/api/templates/{template_id}/rules")
async def get_template_rules(template_id: str):
    """
    获取模板的填写规则

    - template_id: 模板ID，如 1, 2, 3...
    """
    template = None
    for t in TEMPLATES_DATA:
        if t.get("id") == template_id:
            template = t
            break

    if not template:
        return {
            "code": 404,
            "msg": f"Template not found: {template_id}",
            "data": None
        }

    # 提取变量
    variables = extract_template_variables(template.get("template_content", ""))

    # 构建模板规则
    rules = {
        "template_id": template_id,
        "template_name": template.get("name"),
        "description": template.get("summary"),
        "template_type": "service_record",
        "validation_rules": [
            {
                "type": "required",
                "message": "模板内容不能为空",
                "severity": "error"
            },
            {
                "type": "min_length",
                "message": "服务记录总结至少需要10个字符",
                "value": 10,
                "severity": "error"
            },
            {
                "type": "max_length",
                "message": "服务记录总结最多2000个字符",
                "value": 2000,
                "severity": "error"
            }
        ],
        "variable_rules": {
            "total_count": len(variables),
            "required_count": sum(1 for v in variables if v.get("required")),
            "optional_count": sum(1 for v in variables if not v.get("required")),
            "variables": variables
        },
        "fill_instruction": {
            "description": f"使用【{template.get('name')}】模板填写服务记录总结",
            "steps": [
                "从用户对话中提取模板变量",
                "将 ${variable_name} 替换为实际值",
                "对于无法提取的变量，保留占位符或询问用户",
                "确保所有必需变量已填充"
            ],
            "key_points": [
                "客户信息必须准确",
                "故障描述要详细具体",
                "处理措施要清晰明确"
            ]
        }
    }

    return {
        "code": 200,
        "msg": "OK",
        "data": rules
    }


# ==================== 接口11: 提交表单 ====================

@app.post("/api/form/submit")
async def submit_form(request: Request):
    """
    提交填单结果

    请求体：
    {
        "app_id": "app_001",
        "data": {
            "event_type_level1": "EVT001",
            "event_type_level2": "EVT001001",
            "event_type_level3": "EVT001001001",
            "service_summary": "【客户信息】..."
        }
    }
    """
    try:
        body = await request.json()
        app_id = body.get("app_id", "default")
        data = body.get("data", {})

        # 验证必填字段
        missing_fields = []
        for field in FORM_FIELDS:
            if field["required"] and field["field_id"] not in data:
                missing_fields.append(field["field_name"])

        if missing_fields:
            return {
                "code": 400,
                "msg": f"Missing required fields: {', '.join(missing_fields)}",
                "data": {"missing_fields": missing_fields}
            }

        # 生成表单ID
        import uuid
        form_id = f"FORM_{uuid.uuid4().hex[:12].upper()}"

        return {
            "code": 200,
            "msg": "Form submitted successfully",
            "data": {
                "form_id": form_id,
                "app_id": app_id,
                "submitted_at": "2024-01-01T00:00:00Z",
                "field_count": len(data),
                "summary": {
                    "event_type": f"{data.get('event_type_level1')} > {data.get('event_type_level2')} > {data.get('event_type_level3')}",
                    "service_summary_length": len(data.get('service_summary', ''))
                }
            }
        }
    except Exception as e:
        return {
            "code": 400,
            "msg": f"Invalid request: {str(e)}",
            "data": None
        }

# ==================== 接口12: 验证表单数据 ====================

@app.post("/api/form/validate")
async def validate_form(request: Request):
    """
    验证表单数据

    请求体：
    {
        "field_id": "service_summary",
        "value": "..."
    }
    """
    try:
        body = await request.json()
        field_id = body.get("field_id")
        value = body.get("value")

        field = next((f for f in FORM_FIELDS if f["field_id"] == field_id), None)
        if not field:
            return {
                "code": 404,
                "msg": f"Field not found: {field_id}",
                "data": None
            }

        errors = []

        # 必填验证
        if field["required"] and not value:
            errors.append({"type": "required", "message": f"{field['field_name']}不能为空"})

        # 长度验证
        if field["field_type"] in ["textarea", "text"]:
            min_len = field.get("min_length", 0)
            max_len = field.get("max_length", 2000)
            if value and len(value) < min_len:
                errors.append({"type": "min_length", "message": f"至少需要{min_len}个字符"})
            if value and len(value) > max_len:
                errors.append({"type": "max_length", "message": f"不能超过{max_len}个字符"})

        return {
            "code": 200,
            "msg": "Validation completed",
            "data": {
                "field_id": field_id,
                "valid": len(errors) == 0,
                "errors": errors
            }
        }
    except Exception as e:
        return {
            "code": 400,
            "msg": f"Invalid request: {str(e)}",
            "data": None
        }

# ==================== 健康检查 ====================

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "autofill-test-api",
        "version": "1.0.0",
        "data": {
            "event_types_loaded": len(EVENT_TYPES_DATA),
            "templates_loaded": len(TEMPLATES_DATA)
        }
    }

# ==================== 旧接口兼容 ====================

@app.post("/api/test/tree")
async def get_tree_data(request: Request):
    """单请求树形结构接口 (兼容旧版本)"""
    # 构建树形结构
    tree = []
    for level1 in get_level1_options():
        level1_node = {
            "id": level1["option_id"],
            "option_value": level1["option_id"],
            "summary": level1["option_name"],
            "children": []
        }
        for level2 in get_level2_options(level1["option_id"]):
            level2_node = {
                "id": level2["option_id"],
                "option_value": level2["option_id"],
                "summary": level2["option_name"],
                "children": []
            }
            for level3 in get_level3_options(level2["option_id"]):
                level2_node["children"].append({
                    "id": level3["option_id"],
                    "option_value": level3["option_id"],
                    "summary": level3["option_name"]
                })
            level1_node["children"].append(level2_node)
        tree.append(level1_node)

    return {
        "code": 200,
        "msg": "OK",
        "data": tree
    }


if __name__ == "__main__":
    print("=" * 60)
    print("启动自动填单测试接口服务")
    print("端口: 6666")
    print("")
    print("表单相关接口:")
    print("  GET  /api/form/fields                    - 获取所有字段")
    print("  GET  /api/form/fields/{field_id}/detail  - 获取字段详情")
    print("  GET  /api/form/fields/{field_id}/options - 获取字段选项")
    print("  GET  /api/form/fields/{field_id}/rules   - 获取字段规则")
    print("  POST /api/form/fields/rules/batch        - 批量获取字段规则")
    print("  POST /api/form/submit                    - 提交表单")
    print("  POST /api/form/validate                  - 验证表单数据")
    print("")
    print("模板相关接口:")
    print("  GET  /api/templates                      - 获取所有模板")
    print("  GET  /api/templates/{event_type_id}      - 获取指定模板")
    print("")
    print("兼容接口:")
    print("  POST /api/test/tree                      - 树形结构")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=6666)
