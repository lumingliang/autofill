#!/usr/bin/env python3
"""
分步测试LLM填单工作流
测试场景：基于用户和客服的10轮聊天记录，分步获取填单数据

测试步骤：
1. 第一步：获取一级事件类型和服务记录类型
2. 第二步：根据服务记录类型获取对应字段组的所有字段 + 根据一级事件类型获取二三级事件类型

使用方法:
    python test_llm_fill_workflow.py [--api-key API_KEY] [--base-url BASE_URL]
"""

import argparse
import json
import sys
from typing import Dict, List, Any, Optional

import requests

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
PAGE_NAME = "用户信息页"

# 测试用例：10轮客服对话记录
TEST_CONVERSATION = """
【第1轮】
客服：您好，比亚迪汽车客服中心，请问有什么可以帮您？
用户：你好，我的车突然启动不了了，刚才还好好的。

【第2轮】
客服：您好，请问您的车辆型号是什么？车架号方便提供吗？
用户：我是比亚迪汉EV，车架号是LGXC14EAXN1234567。

【第3轮】
客服：好的，请问您现在车辆的具体位置在哪里？车辆目前是什么状态？
用户：我在家里地下车库，车辆完全没反应，按启动键什么反应都没有。

【第4轮】
客服：请问仪表盘上有显示什么故障灯吗？或者有什么提示信息？
用户：仪表盘上有个红色的电池图标在闪，还有提示说"动力系统故障"。

【第5轮】
客服：明白了，这是动力电池系统的故障报警。请问您最近有没有涉水或者车辆发生过碰撞？
用户：没有碰撞，但是前几天下大雨，我开车经过了一段积水路段，水还挺深的。

【第6轮】
客服：了解了，涉水可能是导致故障的原因。请问您现在车辆还能移动吗？还是完全动不了？
用户：完全动不了，连档位都挂不进去，车门都是机械钥匙打开的。

【第7轮】
客服：好的，这种情况需要安排道路救援。请问您车上现在有几个人？是否需要拖车服务？
用户：就我一个人，需要拖车，帮我拖到最近的4S店吧。

【第8轮】
客服：好的，已为您查询到最近的4S店是比亚迪XX路店。请问您方便接收拖车的手机号码是多少？
用户：我的手机号是13812345678。

【第9轮】
客服：好的，已记录。请问您的车辆当前行驶里程是多少？购车时间是什么时候？
用户：现在跑了35000公里，是2023年5月买的车。

【第10轮】
客服：好的，所有信息已记录。我们会立即安排拖车前往您的位置，预计30-45分钟到达。请您在车辆附近等待，注意安全。
用户：好的，谢谢，麻烦尽快安排。
"""


def send_llm_fill_request(
    api_base_url: str,
    api_key: str,
    page_name: str,
    group_fields: Dict[str, List[str]],
    query: str
) -> Dict:
    """
    发送LLM填单请求
    
    Args:
        api_base_url: API基础URL
        api_key: API密钥
        page_name: 页面名称
        group_fields: 字段组与字段的映射关系，如 {"default": ["field1", "field2"]}
        query: 用户对话内容
    
    Returns:
        API响应结果
    """
    url = f"{api_base_url}/api/autofill/llm/fill"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "page_name": page_name,
        "group_fields": group_fields,
        "query": query
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应状态码: {e.response.status_code}")
            print(f"响应内容: {e.response.text[:500]}")
        raise


def step1_get_basic_fields(api_base_url: str, api_key: str, page_name: str, query: str) -> Dict:
    """
    第一步：获取一级事件类型和服务记录类型
    
    Returns:
        {
            "一级事件类型": "...",
            "服务记录类型": "..."
        }
    """
    print("\n" + "=" * 80)
    print("【步骤1】获取一级事件类型和服务记录类型")
    print("=" * 80)
    
    # 请求 default 字段组中的 一级事件类型 和 服务记录类型
    group_fields = {
        "default": ["一级事件类型", "服务记录类型"]
    }
    
    print(f"请求字段组: {list(group_fields.keys())}")
    print(f"请求字段: {group_fields}")
    
    try:
        response = send_llm_fill_request(
            api_base_url=api_base_url,
            api_key=api_key,
            page_name=page_name,
            group_fields=group_fields,
            query=query
        )
        
        if response.get("code") == 200 or response.get("success"):
            result = response.get("data", {}).get("result", {})
            print("\n✓ 步骤1成功")
            print("\n提取结果:")
            
            # 提取关键字段
            step1_result = {}
            for field_name in ["一级事件类型", "服务记录类型"]:
                field_data = result.get(field_name, {})
                value = field_data.get("value", "") if isinstance(field_data, dict) else field_data
                step1_result[field_name] = value
                print(f"  - {field_name}: {value}")
            
            return step1_result
        else:
            print(f"✗ 步骤1失败: {response.get('message', '未知错误')}")
            return {}
            
    except Exception as e:
        print(f"✗ 步骤1异常: {e}")
        return {}


def step2_get_detailed_fields(
    api_base_url: str,
    api_key: str,
    page_name: str,
    query: str,
    step1_result: Dict
) -> Dict:
    """
    第二步：根据服务记录类型获取对应字段组的所有字段 + 根据一级事件类型获取二三级事件类型
    
    Args:
        step1_result: 步骤1的结果，包含 一级事件类型 和 服务记录类型
    
    Returns:
        完整的填单数据
    """
    print("\n" + "=" * 80)
    print("【步骤2】获取详细字段信息")
    print("=" * 80)
    
    # 从步骤1结果中获取关键信息（提取label值）
    service_record_type_data = step1_result.get("服务记录类型", {})
    level1_event_type_data = step1_result.get("一级事件类型", {})
    
    # 提取label值（如果结果是字典）
    if isinstance(service_record_type_data, dict):
        service_record_type = service_record_type_data.get("label", "")
    else:
        service_record_type = service_record_type_data
        
    if isinstance(level1_event_type_data, dict):
        level1_event_type = level1_event_type_data.get("label", "")
    else:
        level1_event_type = level1_event_type_data
    
    print(f"服务记录类型: {service_record_type}")
    print(f"一级事件类型: {level1_event_type}")
    
    # 构建字段组请求
    # 1. 根据服务记录类型确定字段组名称
    service_group_name = f"服务记录-{service_record_type}" if service_record_type else None
    
    # 2. 根据一级事件类型确定二三级事件类型字段名
    level23_field_name = f"{level1_event_type}_二三级事件类型" if level1_event_type else None
    
    group_fields = {}
    
    # 添加服务记录字段组（获取所有字段，不传具体字段名）
    if service_group_name:
        group_fields[service_group_name] = []  # 空列表表示获取该字段组的所有字段
        print(f"\n将请求字段组: {service_group_name} (所有字段)")
    
    # 添加二三级事件类型字段
    if level23_field_name:
        group_fields["default"] = [level23_field_name]
        print(f"将请求字段: {level23_field_name}")
    
    if not group_fields:
        print("✗ 无法确定要请求的字段组或字段")
        return {}
    
    print(f"\n请求配置: {json.dumps(group_fields, ensure_ascii=False, indent=2)}")
    
    try:
        response = send_llm_fill_request(
            api_base_url=api_base_url,
            api_key=api_key,
            page_name=page_name,
            group_fields=group_fields,
            query=query
        )
        
        if response.get("code") == 200 or response.get("success"):
            result = response.get("data", {}).get("result", {})
            print("\n✓ 步骤2成功")
            print(f"\n提取到 {len(result)} 个字段:")
            
            # 格式化输出结果
            for field_name, field_data in result.items():
                if isinstance(field_data, dict):
                    value = field_data.get("value", "")
                    label = field_data.get("label", field_name)
                    print(f"  - {label}({field_name}): {value}")
                else:
                    print(f"  - {field_name}: {field_data}")
            
            return result
        else:
            print(f"✗ 步骤2失败: {response.get('message', '未知错误')}")
            return {}
            
    except Exception as e:
        print(f"✗ 步骤2异常: {e}")
        return {}


def merge_results(step1_result: Dict, step2_result: Dict) -> Dict:
    """合并两步的结果"""
    merged = {}
    
    # 添加步骤1的结果
    for key, value in step1_result.items():
        merged[key] = value
    
    # 添加步骤2的结果
    for key, value in step2_result.items():
        # 如果值是字典，提取value字段
        if isinstance(value, dict):
            merged[key] = value.get("value", "")
        else:
            merged[key] = value
    
    return merged


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="分步测试LLM填单工作流")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API Key")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE_URL, help="API基础URL")
    parser.add_argument("--page-name", default=PAGE_NAME, help="页面名称")
    parser.add_argument("--conversation", default=TEST_CONVERSATION, help="测试对话内容")
    args = parser.parse_args()

    api_base_url = args.base_url
    api_key = args.api_key
    page_name = args.page_name
    conversation = args.conversation

    print("=" * 80)
    print("分步测试LLM填单工作流")
    print("=" * 80)
    print(f"API Base URL: {api_base_url}")
    print(f"页面名称: {page_name}")
    print(f"\n测试对话内容:\n{conversation[:200]}...")
    print("=" * 80)

    # 执行步骤1
    step1_result = step1_get_basic_fields(
        api_base_url=api_base_url,
        api_key=api_key,
        page_name=page_name,
        query=conversation
    )

    if not step1_result:
        print("\n✗ 步骤1失败，终止测试")
        sys.exit(1)

    # 执行步骤2
    step2_result = step2_get_detailed_fields(
        api_base_url=api_base_url,
        api_key=api_key,
        page_name=page_name,
        query=conversation,
        step1_result=step1_result
    )

    if not step2_result:
        print("\n✗ 步骤2失败")
        # 仍然继续输出步骤1的结果

    # 合并结果
    final_result = merge_results(step1_result, step2_result)

    # 输出最终结果
    print("\n" + "=" * 80)
    print("【最终填单结果】")
    print("=" * 80)
    print(json.dumps(final_result, ensure_ascii=False, indent=2))
    print("=" * 80)
    print(f"\n总计提取字段数: {len(final_result)}")
    print("\n测试完成!")


if __name__ == "__main__":
    main()
