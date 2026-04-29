#!/usr/bin/env python3
"""
直接调用 LLM 代理接口测试
模拟三方服务调用
"""

import asyncio
import json
import httpx


# API 配置
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
BASE_URL = "http://localhost:9999/api"  # 后端服务端口

# 客服对话数据
customer_dialogue = """张先生: 你好，我的车最近充电老是充到80%就停了，而且底盘偶尔有咯噔咯噔的响声，这怎么回事？
客服小慧: 张先生您好，很抱歉给您带来困扰。为了更准确地为您排查，我需要先核实一下您的车辆信息 。请问您的车辆型号和购车日期是什么？
张先生: 是2024款的极越01超长续航版，去年11月提的车，到现在大 概跑了1.2万公里。
客服小慧: 好的，谢谢。请问您的车牌号或车架号后6位是多少？我这边帮您建档。
张先 生: 车牌是粤A12345D，车架号后6位是253718。
客服小慧: 已记录。您提到充电到80%停止，是使用家用充电桩还是公共快充桩？每次都这样吗？
张先生: 家用慢充和外面的快充都试过，快充时基本到80%就跳枪，慢充偶尔能充到100%，但最近几次也都停在80%。
客服小慧: 了解了。请问充电时仪表盘有故障灯或提示吗？底盘异响主要出现什么路况？
张先生: 充电时会报一个"高压系统异常，请联系服务商"的提示。异响的话，基本低速过减 速带或者颠簸路面时会有，速度起来就没了。
客服小慧: 收到。根据您的描述，初步判断可能与电池管理系统 （BMS）或充电协议有关，异响则可能是底盘螺栓扭矩不足或悬挂衬套磨损。建议您尽快进站进行专业检测。
张先生: 那我现在能约明天下午去检查吗？我在广州天河区。
客服小慧: 好的。为您查询一下广州天河中路的极 越授权服务中心，明天下午14:00有空位，您方便吗？
张先生: 可以，就14:00吧。需要带什么资料吗？
客服 小慧: 请携带车主本人身份证、行驶证和购车发票（或电子发票），我们会为您优先安排新能源三电系统检测与 底盘检查。
张先生: 好，谢谢！万一发现问题，维修要多久？我只有后天空闲。
客服小慧: 常规检测约1小时，如果需要更换底盘部件或BMS软件升级，当天一般能完成。您可现场与工程师确认明细，我们会加急处理，争取不耽误您用车。
张先生: 行，那我明天准时到。
客服小慧: 好的，已为您预约成功。祝您生活愉快，再见"""

# Function Schema
function_schema = {
    "type": "function",
    "function": {
        "name": "extract_customer_service_info",
        "description": "从客服对话中提取客户信息、车辆问题、预约信息等结构化数据",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_info": {
                    "type": "object",
                    "description": "客户基本信息",
                    "properties": {
                        "name": {"type": "string", "description": "客户姓名"},
                        "phone": {"type": "string", "description": "客户电话（如有）"}
                    },
                    "required": ["name"]
                },
                "vehicle_info": {
                    "type": "object",
                    "description": "车辆信息",
                    "properties": {
                        "model": {"type": "string", "description": "车辆型号"},
                        "purchase_date": {"type": "string", "description": "购车日期"},
                        "mileage": {"type": "string", "description": "当前里程"},
                        "license_plate": {"type": "string", "description": "车牌号"},
                        "vin_last6": {"type": "string", "description": "车架号后6位"}
                    },
                    "required": ["model"]
                },
                "issues": {
                    "type": "array",
                    "description": "客户反馈的问题列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "description": "问题类型"},
                            "description": {"type": "string", "description": "问题描述"},
                            "symptoms": {"type": "array", "items": {"type": "string"}, "description": "症状列表"},
                            "error_message": {"type": "string", "description": "错误提示信息（如有）"}
                        },
                        "required": ["type", "description"]
                    }
                },
                "preliminary_diagnosis": {
                    "type": "object",
                    "description": "初步诊断信息",
                    "properties": {
                        "possible_causes": {"type": "array", "items": {"type": "string"}, "description": "可能原因"},
                        "suggested_checks": {"type": "array", "items": {"type": "string"}, "description": "建议检查项目"}
                    }
                },
                "appointment": {
                    "type": "object",
                    "description": "预约信息",
                    "properties": {
                        "service_center": {"type": "string", "description": "服务中心名称"},
                        "address": {"type": "string", "description": "服务中心地址"},
                        "appointment_time": {"type": "string", "description": "预约时间"},
                        "required_documents": {"type": "array", "items": {"type": "string"}, "description": "所需携带材料"},
                        "estimated_duration": {"type": "string", "description": "预计时长"}
                    }
                },
                "service_satisfaction": {
                    "type": "object",
                    "description": "服务满意度相关信息",
                    "properties": {
                        "urgency_level": {"type": "string", "enum": ["紧急", "一般", "可等待"], "description": "紧急程度"},
                        "customer_emotion": {"type": "string", "enum": ["满意", "一般", "不满", "愤怒"], "description": "客户情绪"}
                    }
                }
            },
            "required": ["customer_info", "vehicle_info", "issues"]
        }
    }
}


async def test_health_check():
    """测试健康检查接口"""
    print("=" * 80)
    print("测试健康检查接口")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/llm/proxy/health",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )

        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        return response.status_code == 200


async def test_proxy_api():
    """测试代理接口"""
    print("\n" + "=" * 80)
    print("测试代理接口 - 客服对话结构化提取")
    print("=" * 80)

    # 请求数据
    request_data = {
        "query": customer_dialogue,
        "function_schema": function_schema,
        "context": "这是极越汽车客服对话，需要提取客户信息、车辆问题、预约信息等",
        "app_key": API_KEY
    }

    print(f"\n请求数据:")
    print(f"- Query 长度: {len(customer_dialogue)} 字符")
    print(f"- Function Schema: {function_schema['function']['name']}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/llm/proxy",
                json=request_data,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                timeout=120.0  # 设置较长的超时时间
            )

            print(f"\n状态码: {response.status_code}")
            result = response.json()

            if result.get("code") == 200:
                print(f"\n✅ 调用成功!")
                print(f"\n提取结果:")
                print("-" * 80)
                print(json.dumps(result.get("data"), ensure_ascii=False, indent=2))

                # 验证关键字段
                data = result.get("data", {})
                print("\n" + "=" * 80)
                print("结果验证:")
                print("=" * 80)
                print(f"   ✅ 客户姓名: {data.get('customer_info', {}).get('name', 'N/A')}")
                print(f"   ✅ 车辆型号: {data.get('vehicle_info', {}).get('model', 'N/A')}")
                print(f"   ✅ 车牌号: {data.get('vehicle_info', {}).get('license_plate', 'N/A')}")
                print(f"   ✅ 问题数量: {len(data.get('issues', []))}")
                print(f"   ✅ 预约时间: {data.get('appointment', {}).get('appointment_time', 'N/A')}")

                return True
            else:
                print(f"\n❌ 调用失败!")
                print(f"错误码: {result.get('code')}")
                print(f"错误信息: {result.get('msg')}")
                return False

        except httpx.TimeoutException:
            print("\n❌ 请求超时!")
            return False
        except Exception as e:
            print(f"\n❌ 请求异常: {e}")
            return False


async def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("LLM 代理接口直接调用测试")
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-4:]}")
    print(f"Base URL: {BASE_URL}")
    print("=" * 80)

    # 测试健康检查
    health_ok = await test_health_check()

    if health_ok:
        # 测试代理接口
        proxy_ok = await test_proxy_api()

        print("\n" + "=" * 80)
        if proxy_ok:
            print("✅ 所有测试通过!")
        else:
            print("❌ 代理接口测试失败")
        print("=" * 80)
    else:
        print("\n❌ 健康检查失败，请检查服务是否运行")


if __name__ == "__main__":
    asyncio.run(main())
