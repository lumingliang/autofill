#!/usr/bin/env python3
"""
分步骤填单测试脚本
第一步：提取一级事件类型、service_types、scene_category
第二步：基于第一步结果，动态提取相关字段组的字段

API Key = af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR
"""
import json
import requests

# 配置
BASE_URL = "http://localhost:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

# 10轮400客服和用户的对话 - 道路救援场景
CONVERSATION = """
客服: 您好，欢迎致电比亚迪400客服中心，请问有什么可以帮您？
用户: 你好，我的车在高速上抛锚了，需要紧急救援！

客服: 好的，请您先保持冷静。请问您的车辆是什么品牌和型号？
用户: 比亚迪汉EV，2023款旗舰版。

客服: 收到，汉EV 2023款。请问您现在具体位置在哪里？
用户: 我在京沪高速北京方向，大概在廊坊段，路边有K85的公里牌。

客服: 好的，K85公里牌，京沪高速北京方向廊坊段。请问您的姓名和联系电话？
用户: 我叫李明，电话是13900139000。

客服: 好的李先生，请问车辆目前是什么情况？能描述一下故障现象吗？
用户: 仪表盘显示"动力电池系统故障"，然后车子突然失去动力，现在停在应急车道，双闪已经打开了。

客服: 明白，动力电池故障导致失去动力。请问车上还有几位乘客？大家都安全吗？
用户: 就我和我妻子两个人，我们都已经撤离到护栏外面了。

客服: 非常好，请您们继续待在护栏外安全位置。请问您需要拖车服务还是现场维修？
用户: 需要拖车，拖到最近的比亚迪4S店检修，这车不敢开了。

客服: 收到，我们会安排拖车将您的车辆拖至最近的比亚迪4S店。请问您方便接收短信通知吗？
用户: 可以，发到我这个手机号就行。

客服: 好的，已经记录。救援人员预计40分钟内到达，请您们在安全位置等候，注意后方来车。还有其他问题吗？
用户: 没有了，谢谢，请尽快安排。
"""


def step1_extract_basic_fields():
    """
    第一步：提取基础字段
    - 一级事件类型
    - service_types
    - scene_category
    """
    url = f"{BASE_URL}/autofill/llm/fill"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "page_name": "用户信息页",
        "group_names": ["default"],
        "field_names": ["一级事件类型", "service_types", "scene_category"],
        "query": CONVERSATION.strip()
    }

    print("=" * 70)
    print("【第一步】提取基础字段")
    print("=" * 70)
    print(f"提取字段: 一级事件类型, service_types, scene_category")
    print(f"\n请求: POST {url}")
    print(f"请求体: {json.dumps(data, ensure_ascii=False, indent=2)}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        print(f"\n状态码: {resp.status_code}")
        result = resp.json()
        
        if result.get("code") == 200:
            extracted = result.get("data", {}).get("result", {})
            print(f"\n✅ 提取成功:")
            for key, value in extracted.items():
                print(f"  {key}: {value}")
            return extracted
        else:
            print(f"\n❌ 错误: {result.get('msg')}")
            return None
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return None


def step2_extract_dynamic_fields(step1_result):
    """
    第二步：基于第一步结果动态提取字段
    - 基于 scene_category 值，提取 "服务记录-{val}" 字段组的所有字段
    - 基于 一级事件类型 值，提取 "{val2}-二三级" 字段
    
    使用新的 group_fields 传参格式：
    {
        "default": ["救援-二三级"],
        "服务记录-道路救援请求": []
    }
    """
    if not step1_result:
        print("\n❌ 第一步没有结果，无法执行第二步")
        return None

    # 获取第一步的结果值
    scene_category = step1_result.get("scene_category", "")
    primary_event_type = step1_result.get("一级事件类型", "")
    
    print("\n" + "=" * 70)
    print("【第二步】动态提取字段")
    print("=" * 70)
    print(f"第一步结果:")
    print(f"  - 一级事件类型: {primary_event_type}")
    print(f"  - scene_category: {scene_category}")
    
    # 使用新的 group_fields 传参格式
    group_fields = {}
    
    # 如果有二级事件类型字段，添加到 default 字段组
    if primary_event_type:
        secondary_field = f"{primary_event_type}-二三级"
        group_fields["default"] = [secondary_field]
        print(f"\n📋 default 字段组查询字段: {secondary_field}")
    else:
        group_fields["default"] = []
    
    # 基于 scene_category 确定服务记录字段组（空列表表示查询该组所有字段）
    if scene_category:
        service_record_group = f"服务记录-{scene_category}"
        group_fields[service_record_group] = []  # 空列表表示查询该组所有字段
        print(f"📋 {service_record_group} 字段组查询字段: 所有字段")
    
    url = f"{BASE_URL}/autofill/llm/fill"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 使用新的 group_fields 传参格式
    data = {
        "page_name": "用户信息页",
        "group_fields": group_fields,
        "query": CONVERSATION.strip()
    }
    
    print(f"\n请求: POST {url}")
    print(f"请求体: {json.dumps(data, ensure_ascii=False, indent=2)}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        print(f"\n状态码: {resp.status_code}")
        result = resp.json()
        
        if result.get("code") == 200:
            extracted = result.get("data", {}).get("result", {})
            print(f"\n✅ 提取成功:")
            for key, value in extracted.items():
                print(f"  {key}: {value}")
            return extracted
        else:
            print(f"\n❌ 错误: {result.get('msg')}")
            return None
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return None


def update_field_instruction(field_name, instruction):
    """
    如果结果不符合预期，调用 upsert 接口更新字段指引
    """
    url = f"{BASE_URL}/autofill/field_spec/upsert"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "page_name": "用户信息页",
        "group_name": "default",
        "field_name": field_name,
        "field_label": field_name,
        "field_type": "select",
        "fill_instruction": instruction
    }
    
    print(f"\n📝 更新字段指引: {field_name}")
    print(f"请求: POST {url}")
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        result = resp.json()
        if result.get("code") == 200:
            print(f"✅ 更新成功")
            return True
        else:
            print(f"❌ 更新失败: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


def main():
    print("=" * 70)
    print("分步骤填单测试脚本")
    print("=" * 70)
    print(f"API Key: {API_KEY}")
    print(f"目标页面: 用户信息页")
    
    # 执行第一步
    step1_result = step1_extract_basic_fields()
    
    if step1_result:
        # 验证第一步结果
        print("\n" + "-" * 70)
        print("【第一步结果验证】")
        print("-" * 70)
        
        expected_scene_category = "道路救援请求"
        expected_service_type = "拖车服务"
        
        scene_category = step1_result.get("scene_category")
        service_types = step1_result.get("service_types", [])
        
        # 验证 scene_category
        if scene_category == expected_scene_category:
            print(f"✅ scene_category 正确: {scene_category}")
        else:
            print(f"⚠️ scene_category 可能不准确: {scene_category} (期望: {expected_scene_category})")
            print(f"   建议: 更新 scene_category 字段的 fill_instruction 以优化识别")
        
        # 验证 service_types
        if expected_service_type in service_types:
            print(f"✅ service_types 包含: {expected_service_type}")
        else:
            print(f"⚠️ service_types 可能不完整: {service_types} (期望包含: {expected_service_type})")
        
        # 执行第二步
        print("\n")
        step2_result = step2_extract_dynamic_fields(step1_result)
        
        if step2_result:
            print("\n" + "=" * 70)
            print("【测试总结】")
            print("=" * 70)
            print("✅ 第一步: 基础字段提取成功")
            print(f"   - scene_category: {step1_result.get('scene_category')}")
            print(f"   - service_types: {step1_result.get('service_types')}")
            print(f"   - 一级事件类型: {step1_result.get('一级事件类型')}")
            print("\n✅ 第二步: 动态字段提取成功")
            print(f"   共提取 {len(step2_result)} 个字段")
            for key, value in step2_result.items():
                print(f"   - {key}: {value}")
        else:
            print("\n❌ 第二步: 动态字段提取失败")
    else:
        print("\n❌ 第一步: 基础字段提取失败")


if __name__ == "__main__":
    main()
