#!/usr/bin/env python3
"""
分步测试LLM填单工作流 - 增强版
测试场景：基于用户和客服的聊天记录，分步获取填单数据

测试步骤：
1. 第一步：获取一级事件类型和服务记录类型
2. 第二步：根据服务记录类型获取对应字段组的所有字段 + 根据一级事件类型获取二三级事件类型

特性：
- 支持自定义测试用例（从文件读取或命令行传入）
- 支持多种对话场景（道路救援、保养预约、质量问题等）
- 详细的执行日志和结果格式化输出
- 支持保存结果到JSON文件

使用方法:
    python test_llm_fill_workflow_v2.py [选项]

示例:
    # 使用默认测试用例
    python test_llm_fill_workflow_v2.py
    
    # 从文件读取对话内容
    python test_llm_fill_workflow_v2.py --conversation-file conversation.txt
    
    # 直接传入对话内容
    python test_llm_fill_workflow_v2.py --conversation "用户：我的车无法启动..."
    
    # 保存结果到文件
    python test_llm_fill_workflow_v2.py --output result.json
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

import requests

# 默认配置
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
PAGE_NAME = "用户信息页"

# 测试用例1：道路救援场景
TEST_CONVERSATION_RESCUE = """
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

# 测试用例2：保养预约场景
TEST_CONVERSATION_MAINTENANCE = """
【第1轮】
客服：您好，比亚迪汽车客服中心，请问有什么可以帮您？
用户：你好，我想预约一下车辆保养。

【第2轮】
客服：好的，请问您的车辆型号和车架号？
用户：比亚迪唐DM-i，车架号LGXC14EAXN7654321。

【第3轮】
客服：好的，请问您想预约什么时间的保养服务？
用户：我想预约下周三下午，5月15日下午2点左右。

【第4轮】
客服：好的，请问您需要什么类型的保养？常规保养还是大保养？
用户：常规保养就行，顺便帮我检查一下刹车片。

【第5轮】
客服：明白了。请问您有偏好的服务店吗？
用户：就去我常去的那家，比亚迪朝阳路店。

【第6轮】
客服：好的，已为您查询。请问您需要接送车服务吗？
用户：不用了，我自己开过去。

【第7轮】
客服：好的，请问您的联系电话是多少？
用户：13987654321。

【第8轮】
客服：已为您预约成功，预约单号是BYD20240515001，接待顾问是张师傅。请您准时到店。
用户：好的，谢谢。
"""

# 测试用例3：质量问题投诉场景
TEST_CONVERSATION_QUALITY = """
【第1轮】
客服：您好，比亚迪汽车客服中心，请问有什么可以帮您？
用户：我要投诉，我的新车才买了两个月，车漆就有问题了！

【第2轮】
客服：非常抱歉给您带来不好的体验。请问是什么问题呢？能详细描述一下吗？
用户：引擎盖上有块漆颜色不一样，像是补过漆的，还有流挂的痕迹。

【第3轮】
客服：明白了，是漆面色差和流挂问题。请问您的车辆型号和车架号？
用户：比亚迪海豹，车架号LGXC14EAXN1112223。

【第4轮】
客服：好的，请问您是什么时候发现这个问题的？
用户：上周洗车的时候发现的，之前没注意。

【第5轮】
客服：请问您有拍照片吗？能否提供给我们？
用户：拍了，我可以通过APP上传。

【第6轮】
客服：好的，请问您的诉求是什么？希望如何处理？
用户：我要求免费重新喷漆，还要给我补偿！

【第7轮】
客服：理解您的心情。我们会安排您到店检测，如果确认是质量问题，会免费为您处理。请问您方便什么时候到店？
用户：这周六上午吧。

【第8轮】
客服：好的，已为您预约。请问您的联系电话？
用户：13611112222。
"""


def send_llm_fill_request(
    api_base_url: str,
    api_key: str,
    page_name: str,
    group_fields: Dict[str, List[str]],
    query: str,
    method: str = None,
    additional_data: Dict[str, Any] = None,
    use_additional_data: bool = False
) -> Dict:
    """
    发送LLM填单请求

    Args:
        api_base_url: API基础URL
        api_key: API密钥
        page_name: 页面名称
        group_fields: 字段组与字段的映射关系
        query: 用户对话内容
        method: LLM调用方法，可选 "with_structured_output", "bind_tools_non_stream",
                "bind_tools_stream", "custom_fc_non_stream", "custom_fc_stream",
                "pydantic_parser", "json_parser"
        additional_data: 附加数据，包含预填充的字段值
        use_additional_data: 是否使用附加数据

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

    if method:
        payload["method"] = method

    if use_additional_data and additional_data:
        payload["additional_data"] = additional_data
        payload["use_additional_data"] = True

    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()


def extract_field_value(field_data: Any) -> Any:
    """从字段数据中提取值（value字段）
    
    处理两种结构：
    1. {"type": "...", "value": {"value": "...", "label": "..."}} - 下拉选项
    2. {"type": "...", "value": "..."} - 文本字段
    """
    if isinstance(field_data, dict):
        value = field_data.get("value", "")
        # 如果是下拉选项，value里面还有嵌套
        if isinstance(value, dict):
            return value.get("value", "")
        return value
    return field_data


def extract_field_label(field_data: Any) -> str:
    """从字段数据中提取标签（label字段）
    
    处理两种结构：
    1. {"type": "...", "value": {"value": "...", "label": "..."}} - 下拉选项
    2. {"type": "...", "value": "..."} - 文本字段（没有label，返回value）
    """
    if isinstance(field_data, dict):
        value = field_data.get("value", "")
        # 如果是下拉选项，value里面还有嵌套的label
        if isinstance(value, dict):
            return value.get("label", "")
        # 文本字段，返回value本身
        return str(value) if value else ""
    return ""


def extract_field_display_value(field_data: Any) -> str:
    """从字段数据中提取显示值（用于构建字段组名称等）
    
    支持两种输入格式：
    1. 原始API返回: {"type": "...", "value": {"value": "...", "label": "..."}}
    2. 简化存储: {"value": "...", "label": "..."}
    
    对于下拉选项，返回label（如"保养预约"）
    对于文本字段，返回value
    """
    if isinstance(field_data, dict):
        # 检查是否是简化格式（直接有label字段）
        if "label" in field_data and "type" not in field_data:
            return field_data.get("label", "")
        
        # 原始API格式
        value = field_data.get("value", "")
        if isinstance(value, dict):
            return value.get("label", "")
        return str(value) if value else ""
    return str(field_data) if field_data else ""


def step1_get_basic_fields(
    api_base_url: str,
    api_key: str,
    page_name: str,
    query: str,
    method: str = None,
    additional_data: Dict[str, Any] = None,
    use_additional_data: bool = False
) -> Dict:
    """第一步：获取一级事件类型和服务记录类型"""
    print("\n" + "=" * 80)
    print("【步骤1】获取一级事件类型和服务记录类型")
    if method:
        print(f"使用方法: {method}")
    if use_additional_data and additional_data:
        print(f"使用附加数据: {list(additional_data.keys())}")
    print("=" * 80)

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
            query=query,
            method=method,
            additional_data=additional_data,
            use_additional_data=use_additional_data
        )
        
        if response.get("code") == 200 or response.get("success"):
            result = response.get("data", {}).get("result", {})
            print("\n✓ 步骤1成功")
            
            # 打印接口返回的完整原始内容
            print("\n【步骤1接口返回的完整原始内容】")
            print("=" * 80)
            print(json.dumps(response, ensure_ascii=False, indent=2))
            print("=" * 80)
            
            # 打印提取的result数据
            print("\n【步骤1提取的result数据】")
            print("-" * 80)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print("-" * 80)
            
            print("\n提取结果:")
            
            step1_result = {}
            for field_name in ["一级事件类型", "服务记录类型"]:
                field_data = result.get(field_name, {})
                # 存储提取后的值，而不是原始数据
                step1_result[field_name] = {
                    "value": extract_field_value(field_data),
                    "label": extract_field_label(field_data)
                }
                value = extract_field_value(field_data)
                label = extract_field_label(field_data)
                print(f"  - {field_name}: {label} ({value})")
            
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
    step1_result: Dict,
    method: str = None,
    additional_data: Dict[str, Any] = None,
    use_additional_data: bool = False
) -> Dict:
    """第二步：获取详细字段信息"""
    print("\n" + "=" * 80)
    print("【步骤2】获取详细字段信息")
    if method:
        print(f"使用方法: {method}")
    if use_additional_data and additional_data:
        print(f"使用附加数据: {list(additional_data.keys())}")
    print("=" * 80)

    # 提取显示值（用于构建字段组名称）
    service_record_type = extract_field_display_value(
        step1_result.get("服务记录类型", {})
    )
    level1_event_type = extract_field_display_value(
        step1_result.get("一级事件类型", {})
    )

    print(f"服务记录类型: {service_record_type}")
    print(f"一级事件类型: {level1_event_type}")

    # 构建字段组请求
    service_group_name = f"服务记录-{service_record_type}" if service_record_type else None
    level23_field_name = f"{level1_event_type}_二三级事件类型" if level1_event_type else None

    group_fields = {}

    if service_group_name:
        group_fields[service_group_name] = []
        print(f"\n将请求字段组: {service_group_name} (所有字段)")

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
            query=query,
            method=method,
            additional_data=additional_data,
            use_additional_data=use_additional_data
        )
        
        if response.get("code") == 200 or response.get("success"):
            result = response.get("data", {}).get("result", {})
            output_templates = response.get("data", {}).get("output_templates", {})
            
            print("\n✓ 步骤2成功")
            
            # 打印接口返回的完整原始内容
            print("\n【步骤2接口返回的完整原始内容】")
            print("=" * 80)
            print(json.dumps(response, ensure_ascii=False, indent=2))
            print("=" * 80)
            
            # 打印提取的result数据
            print("\n【步骤2提取的result数据】")
            print("-" * 80)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print("-" * 80)
            
            # 打印输出模板
            if output_templates:
                print("\n【输出模板（已替换字段值）】")
                print("-" * 80)
                for template_name, template_data in output_templates.items():
                    print(f"\n模板名称: {template_name}")
                    print(f"描述: {template_data.get('description', '')}")
                    print(f"内容:\n{template_data.get('template', '')}")
                print("-" * 80)
            
            print(f"\n提取到 {len(result)} 个字段:")
            
            for field_name, field_data in result.items():
                value = extract_field_value(field_data)
                label = extract_field_label(field_data)
                if isinstance(field_data, dict):
                    print(f"  - {label}({field_name}): {value}")
                else:
                    print(f"  - {field_name}: {value}")
            
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
    
    for key, value in step1_result.items():
        merged[key] = extract_field_value(value)
    
    for key, value in step2_result.items():
        merged[key] = extract_field_value(value)
    
    return merged


def format_final_result(result: Dict) -> str:
    """格式化最终结果为可读文本"""
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("【最终填单结果】")
    lines.append("=" * 80)
    
    # 分类显示
    categories = {
        "事件类型": ["一级事件类型", "服务记录类型"],
        "二三级事件": [k for k in result.keys() if "二三级" in k],
        "客户信息": ["customer_name", "contact_phone"],
        "车辆信息": ["vehicle_system", "vin_code", "vehicle_type", "mileage", "purchase_date"],
        "故障信息": ["fault_description", "warning_light_status", "startup_issue_type", 
                     "battery_warning_type", "brake_warning_type"],
        "位置信息": ["vehicle_location", "current_location", "destination"],
        "救援信息": ["rescue_type", "rescue_arrangement", "eta", "expected_time", 
                     "need_towing", "need_rescue", "is_safe_parked"],
        "其他": []
    }
    
    used_keys = set()
    for category, keys in categories.items():
        category_data = []
        for key in keys:
            if key in result and result[key]:
                category_data.append(f"  {key}: {result[key]}")
                used_keys.add(key)
        
        if category_data:
            lines.append(f"\n{category}:")
            lines.extend(category_data)
    
    # 显示未分类的字段
    other_keys = set(result.keys()) - used_keys
    if other_keys:
        lines.append("\n其他字段:")
        for key in sorted(other_keys):
            lines.append(f"  {key}: {result[key]}")
    
    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="分步测试LLM填单工作流")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API Key")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE_URL, help="API基础URL")
    parser.add_argument("--page-name", default=PAGE_NAME, help="页面名称")
    parser.add_argument("--conversation", help="对话内容（直接传入）")
    parser.add_argument("--conversation-file", help="对话内容文件路径")
    parser.add_argument("--scenario", choices=["rescue", "maintenance", "quality"],
                        default="rescue", help="测试场景")
    parser.add_argument("--method", choices=[
        "with_structured_output", "bind_tools_non_stream", "bind_tools_stream",
        "custom_fc_non_stream", "custom_fc_stream", "pydantic_parser", "json_parser"
    ], help="LLM调用方法")
    parser.add_argument("--test-all-methods", action="store_true",
                        help="测试所有可用的LLM方法")
    parser.add_argument("--additional-data", help="附加数据JSON文件路径")
    parser.add_argument("--use-additional-data", action="store_true",
                        help="使用附加数据")
    parser.add_argument("--output", help="输出结果到JSON文件")
    args = parser.parse_args()

    # 确定对话内容
    if args.conversation:
        conversation = args.conversation
    elif args.conversation_file:
        with open(args.conversation_file, 'r', encoding='utf-8') as f:
            conversation = f.read()
    else:
        scenarios = {
            "rescue": TEST_CONVERSATION_RESCUE,
            "maintenance": TEST_CONVERSATION_MAINTENANCE,
            "quality": TEST_CONVERSATION_QUALITY
        }
        conversation = scenarios.get(args.scenario, TEST_CONVERSATION_RESCUE)

    # 加载附加数据
    additional_data = None
    if args.use_additional_data and args.additional_data:
        with open(args.additional_data, 'r', encoding='utf-8') as f:
            additional_data = json.load(f)

    # 测试所有方法
    if args.test_all_methods:
        methods = [
            "with_structured_output", "bind_tools_non_stream", "bind_tools_stream",
            "custom_fc_non_stream", "custom_fc_stream", "pydantic_parser", "json_parser"
        ]
        print("=" * 80)
        print("测试所有LLM调用方法")
        print("=" * 80)

        results = {}
        for method in methods:
            print(f"\n{'='*80}")
            print(f"测试方法: {method}")
            print(f"{'='*80}")

            step1_result = step1_get_basic_fields(
                api_base_url=args.base_url,
                api_key=args.api_key,
                page_name=args.page_name,
                query=conversation,
                method=method,
                additional_data=additional_data,
                use_additional_data=args.use_additional_data
            )

            if step1_result:
                step2_result = step2_get_detailed_fields(
                    api_base_url=args.base_url,
                    api_key=args.api_key,
                    page_name=args.page_name,
                    query=conversation,
                    step1_result=step1_result,
                    method=method,
                    additional_data=additional_data,
                    use_additional_data=args.use_additional_data
                )
                results[method] = {
                    "step1": step1_result,
                    "step2": step2_result,
                    "success": True
                }
            else:
                results[method] = {"success": False, "error": "步骤1失败"}

        # 输出所有方法测试结果对比
        print("\n" + "=" * 80)
        print("所有方法测试结果对比")
        print("=" * 80)
        for method, result in results.items():
            status = "✓ 成功" if result.get("success") else "✗ 失败"
            print(f"{method}: {status}")

        # 保存结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {args.output}")

        return

    # 单方法测试
    print("=" * 80)
    print("分步测试LLM填单工作流")
    print("=" * 80)
    print(f"API Base URL: {args.base_url}")
    print(f"页面名称: {args.page_name}")
    print(f"测试场景: {args.scenario}")
    if args.method:
        print(f"使用方法: {args.method}")
    if args.use_additional_data and additional_data:
        print(f"使用附加数据: {list(additional_data.keys())}")
    print(f"\n测试对话内容:\n{conversation[:200]}...")
    print("=" * 80)

    # 执行步骤1
    step1_result = step1_get_basic_fields(
        api_base_url=args.base_url,
        api_key=args.api_key,
        page_name=args.page_name,
        query=conversation,
        method=args.method,
        additional_data=additional_data,
        use_additional_data=args.use_additional_data
    )

    if not step1_result:
        print("\n✗ 步骤1失败，终止测试")
        sys.exit(1)

    # 执行步骤2
    step2_result = step2_get_detailed_fields(
        api_base_url=args.base_url,
        api_key=args.api_key,
        page_name=args.page_name,
        query=conversation,
        step1_result=step1_result,
        method=args.method,
        additional_data=additional_data,
        use_additional_data=args.use_additional_data
    )

    # 合并结果
    final_result = merge_results(step1_result, step2_result)

    # 输出格式化结果
    print(format_final_result(final_result))
    
    # 输出JSON格式
    print("\n【JSON格式】")
    print(json.dumps(final_result, ensure_ascii=False, indent=2))
    
    print(f"\n总计提取字段数: {len(final_result)}")
    
    # 保存到文件
    if args.output:
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "scenario": args.scenario,
            "page_name": args.page_name,
            "conversation": conversation,
            "result": final_result
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {args.output}")
    
    print("\n测试完成!")


if __name__ == "__main__":
    main()
