#!/usr/bin/env python3
"""
测试多字段组多字段填单功能
测试以下接口:
1. POST /api/autofill/field_group/upsert - 创建或更新字段组（含批量字段）
2. POST /api/autofill/llm/fill - LLM填单
3. POST /api/autofill/get_ai_fill_data - 获取AI填单数据
4. POST /api/autofill/field_group - 查询字段组配置
"""

import asyncio
import json
import sys
import os

import httpx
from typing import Dict, Any, List

# 测试配置
BASE_URL = "http://localhost:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"


class MultiGroupFillTest:
    """多字段组填单测试类"""

    def __init__(self, base_url: str = BASE_URL, api_key: str = API_KEY):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.test_results = []
        self.created_groups = []  # 记录创建的字段组
        self.session_id = "test_session_multi_group_001"  # 测试会话ID

    async def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                if method.upper() == "POST":
                    response = await client.post(url, headers=self.headers, json=data, timeout=30)
                else:
                    raise ValueError(f"不支持的 HTTP 方法: {method}")

                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                return {
                    "error": True,
                    "status_code": e.response.status_code,
                    "detail": e.response.text
                }
            except Exception as e:
                return {"error": True, "detail": str(e)}

    def log_result(self, test_name: str, success: bool, message: str = "", data: Any = None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "data": data
        }
        self.test_results.append(result)
        status = "✅ 通过" if success else "❌ 失败"
        print(f"\n{status} - {test_name}")
        if message:
            print(f"   消息: {message}")
        if data:
            print(f"   数据: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}...")

    # ==================== 测试1: 创建多个字段组 ====================

    async def test_create_customer_info_group(self):
        """测试1: 创建客户信息字段组（多个字段）"""
        test_name = "创建客户信息字段组"
        endpoint = "/api/autofill/field_group/upsert"

        data = {
            "page_name": "用户信息页",
            "group_name": "客户信息",
            "prompt_template_base": "请从对话中提取客户基本信息",
            "output_templates": {
                "default": {
                    "template": "客户: ${customer_name}, 电话: ${phone}, 城市: ${city}",
                    "description": "客户信息输出模板"
                }
            },
            "fields": [
                {
                    "field_name": "customer_name",
                    "field_label": "客户姓名",
                    "field_type": "text",
                    "fill_instruction": "请填写客户姓名"
                },
                {
                    "field_name": "phone",
                    "field_label": "联系电话",
                    "field_type": "text",
                    "fill_instruction": "请填写客户联系电话"
                },
                {
                    "field_name": "city",
                    "field_label": "所在城市",
                    "field_type": "text",
                    "fill_instruction": "请填写客户所在城市"
                },
                {
                    "field_name": "age",
                    "field_label": "年龄",
                    "field_type": "text",
                    "fill_instruction": "请填写客户年龄"
                }
            ]
        }

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            self.created_groups.append("客户信息")
            self.log_result(test_name, True, "成功创建客户信息字段组", result.get("data"))
        else:
            self.log_result(test_name, False, f"创建失败: {result.get('detail', result)}")

    async def test_create_vehicle_info_group(self):
        """测试2: 创建车辆信息字段组（多个字段）"""
        test_name = "创建车辆信息字段组"
        endpoint = "/api/autofill/field_group/upsert"

        data = {
            "page_name": "用户信息页",
            "group_name": "车辆信息",
            "prompt_template_base": "请从对话中提取车辆相关信息",
            "output_templates": {
                "default": {
                    "template": "车辆: ${brand} ${model}, 年份: ${year}, 车牌: ${plate_number}",
                    "description": "车辆信息输出模板"
                }
            },
            "fields": [
                {
                    "field_name": "brand",
                    "field_label": "车辆品牌",
                    "field_type": "text",
                    "fill_instruction": "请填写车辆品牌，如比亚迪、特斯拉等"
                },
                {
                    "field_name": "model",
                    "field_label": "车型",
                    "field_type": "text",
                    "fill_instruction": "请填写具体车型"
                },
                {
                    "field_name": "year",
                    "field_label": "车辆年份",
                    "field_type": "text",
                    "fill_instruction": "请填写车辆生产年份"
                },
                {
                    "field_name": "plate_number",
                    "field_label": "车牌号",
                    "field_type": "text",
                    "fill_instruction": "请填写车牌号码"
                },
                {
                    "field_name": "mileage",
                    "field_label": "行驶里程",
                    "field_type": "text",
                    "fill_instruction": "请填写车辆行驶里程"
                }
            ]
        }

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            self.created_groups.append("车辆信息")
            self.log_result(test_name, True, "成功创建车辆信息字段组", result.get("data"))
        else:
            self.log_result(test_name, False, f"创建失败: {result.get('detail', result)}")

    async def test_create_service_info_group(self):
        """测试3: 创建服务信息字段组（多个字段）"""
        test_name = "创建服务信息字段组"
        endpoint = "/api/autofill/field_group/upsert"

        data = {
            "page_name": "用户信息页",
            "group_name": "服务信息",
            "prompt_template_base": "请从对话中提取服务相关信息",
            "output_templates": {
                "default": {
                    "template": "服务类型: ${service_type}, 紧急程度: ${urgency}, 备注: ${remarks}",
                    "description": "服务信息输出模板"
                }
            },
            "fields": [
                {
                    "field_name": "service_type",
                    "field_label": "服务类型",
                    "field_type": "select_single",
                    "fill_instruction": "请选择服务类型",
                    "options": {
                        "source": "static",
                        "items": [
                            {"value": "维修", "label": "维修"},
                            {"value": "保养", "label": "保养"},
                            {"value": "救援", "label": "救援"},
                            {"value": "咨询", "label": "咨询"}
                        ]
                    }
                },
                {
                    "field_name": "urgency",
                    "field_label": "紧急程度",
                    "field_type": "select_single",
                    "fill_instruction": "请选择紧急程度",
                    "options": {
                        "source": "static",
                        "items": [
                            {"value": "高", "label": "高"},
                            {"value": "中", "label": "中"},
                            {"value": "低", "label": "低"}
                        ]
                    }
                },
                {
                    "field_name": "remarks",
                    "field_label": "备注",
                    "field_type": "text",
                    "fill_instruction": "请填写其他备注信息"
                }
            ]
        }

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            self.created_groups.append("服务信息")
            self.log_result(test_name, True, "成功创建服务信息字段组", result.get("data"))
        else:
            self.log_result(test_name, False, f"创建失败: {result.get('detail', result)}")

    # ==================== 测试2: 查询字段组配置 ====================

    async def test_query_field_groups(self):
        """测试4: 查询所有字段组配置"""
        test_name = "查询字段组配置"
        endpoint = "/api/autofill/field_group"

        data = {
            "page_name": "用户信息页",
            "group_names": ["客户信息", "车辆信息", "服务信息"]
        }

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            groups = result.get("data", [])
            if len(groups) >= 3:
                self.log_result(test_name, True, f"成功查询到 {len(groups)} 个字段组", groups)
            else:
                self.log_result(test_name, False, f"查询到的字段组数量不足: {len(groups)}", groups)
        else:
            self.log_result(test_name, False, f"查询失败: {result.get('detail', result)}")

    # ==================== 测试3: LLM填单 ====================

    async def test_llm_fill_single_group(self):
        """测试5: 单字段组LLM填单"""
        test_name = "单字段组LLM填单"
        endpoint = "/api/autofill/llm/fill"

        conversation = """
客服: 您好，请问有什么可以帮您？
用户: 你好，我的车需要保养。
客服: 好的，请问您贵姓？
用户: 我姓李。
客服: 李先生，请问您的联系电话是？
用户: 13912345678。
客服: 请问您在哪个城市？
用户: 我在上海。
"""

        data = {
            "page_name": "用户信息页",
            "group_names": ["客户信息"],
            "field_names": ["customer_name", "phone", "city"],
            "query": conversation.strip()
        }

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            fill_result = result.get("data", {}).get("result", {})
            self.log_result(test_name, True, "LLM填单成功", fill_result)
        else:
            self.log_result(test_name, False, f"LLM填单失败: {result.get('detail', result)}")

    async def test_llm_fill_multiple_groups(self):
        """测试6: 多字段组LLM填单"""
        test_name = "多字段组LLM填单"
        endpoint = "/api/autofill/llm/fill"

        conversation = """
客服: 您好，欢迎致电客服中心，请问有什么可以帮您？
用户: 你好，我的车在路上抛锚了，需要救援。

客服: 好的，请问您的姓名和联系电话？
用户: 我叫王五，电话是13800138000。

客服: 王先生，请问您现在在哪里？
用户: 我在北京朝阳区。

客服: 收到。请问您的车辆是什么品牌和型号？
用户: 比亚迪汉EV，2022款。

客服: 请问车牌号是多少？
用户: 京A12345。

客服: 请问车辆行驶了多少公里？
用户: 大概3万公里。

客服: 好的，请问需要什么类型的服务？
用户: 需要拖车救援。

客服: 明白，这是紧急情况吗？
用户: 是的，比较急，车在路中间。
"""

        data = {
            "page_name": "用户信息页",
            "group_names": ["客户信息", "车辆信息", "服务信息"],
            "field_names": ["customer_name", "phone", "city", "brand", "model", "plate_number", "mileage", "service_type", "urgency"],
            "query": conversation.strip()
        }

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            fill_result = result.get("data", {}).get("result", {})
            filled_count = len([v for v in fill_result.values() if v])
            self.log_result(test_name, True, f"LLM填单成功，填充了 {filled_count} 个字段", fill_result)
        else:
            self.log_result(test_name, False, f"LLM填单失败: {result.get('detail', result)}")

    # ==================== 测试4: 获取AI填单数据 ====================

    async def test_get_ai_fill_data(self):
        """测试7: 获取AI填单数据"""
        test_name = "获取AI填单数据"
        endpoint = "/api/autofill/get_ai_fill_data"

        conversation = """
客服: 您好，请问有什么可以帮您？
用户: 我想咨询一下保养套餐。
客服: 好的，请问您贵姓？
用户: 我姓张。
客服: 张先生，请问您的联系电话？
用户: 13700137000。
客服: 请问您在哪个城市？
用户: 广州。
"""

        data = {
            "page_name": "用户信息页",
            "group_names": ["客户信息"],
            "query": conversation.strip(),
            "session_id": self.session_id
        }

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            task_id = result.get("data", {}).get("task_id")
            self.log_result(test_name, True, f"成功创建填单任务，task_id: {task_id}", result.get("data"))
            return task_id
        else:
            self.log_result(test_name, False, f"获取AI填单数据失败: {result.get('detail', result)}")
            return None

    async def test_get_ai_fill_data_result(self, task_id: str):
        """测试8: 获取AI填单结果"""
        if not task_id:
            self.log_result("获取AI填单结果", False, "task_id为空，跳过测试")
            return

        test_name = "获取AI填单结果"
        endpoint = "/api/autofill/get_ai_fill_data_result"

        data = {
            "task_id": task_id
        }

        # 等待几秒让任务完成
        await asyncio.sleep(3)

        result = await self.make_request("POST", endpoint, data=data)

        if result.get("code") == 200:
            fill_result = result.get("data", {})
            self.log_result(test_name, True, "成功获取填单结果", fill_result)
        else:
            self.log_result(test_name, False, f"获取填单结果失败: {result.get('detail', result)}")

    # ==================== 运行所有测试 ====================

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 70)
        print("多字段组多字段填单功能测试")
        print("=" * 70)
        print(f"API Key: {self.api_key}")
        print(f"Base URL: {self.base_url}")
        print(f"测试页面: 用户信息页")

        # 阶段1: 创建字段组
        print("\n" + "=" * 70)
        print("阶段1: 创建多个字段组")
        print("=" * 70)
        await self.test_create_customer_info_group()
        await self.test_create_vehicle_info_group()
        await self.test_create_service_info_group()

        # 阶段2: 查询字段组
        print("\n" + "=" * 70)
        print("阶段2: 查询字段组配置")
        print("=" * 70)
        await self.test_query_field_groups()

        # 阶段3: LLM填单
        print("\n" + "=" * 70)
        print("阶段3: LLM填单测试")
        print("=" * 70)
        await self.test_llm_fill_single_group()
        await self.test_llm_fill_multiple_groups()

        # 阶段4: AI填单数据
        print("\n" + "=" * 70)
        print("阶段4: AI填单数据测试")
        print("=" * 70)
        task_id = await self.test_get_ai_fill_data()
        await self.test_get_ai_fill_data_result(task_id)

        # 测试总结
        print("\n" + "=" * 70)
        print("测试总结")
        print("=" * 70)
        total = len(self.test_results)
        passed = len([r for r in self.test_results if r["success"]])
        failed = total - passed

        print(f"总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"成功率: {passed/total*100:.1f}%" if total > 0 else "N/A")

        if failed > 0:
            print("\n失败的测试:")
            for r in self.test_results:
                if not r["success"]:
                    print(f"  - {r['test_name']}: {r['message']}")

        return failed == 0


async def main():
    """主函数"""
    tester = MultiGroupFillTest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
