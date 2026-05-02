import asyncio
import httpx
import json

async def test_proxy_with_chat_history():
    """测试代理接口处理聊天记录并生成结构化数据"""
    async with httpx.AsyncClient() as client:
        api_key = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
        
        # 测试场景1：从单条消息提取信息
        print("=" * 60)
        print("测试场景1：从单条消息提取人员信息")
        print("=" * 60)
        
        proxy_data = {
            "query": "请提取以下信息：姓名张三，年龄25岁，邮箱zhangsan@example.com",
            "tools": [
                {
                    "name": "extract_person_info",
                    "description": "提取人员信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "姓名"},
                            "age": {"type": "integer", "description": "年龄"},
                            "email": {"type": "string", "description": "邮箱"}
                        },
                        "required": ["name", "age", "email"]
                    }
                }
            ],
            "system_prompt": "你是一个信息提取助手，请从用户输入中提取结构化信息。",
            "preferred_methods": ["with_structured_output", "custom_fc_non_stream", "json_parser"]
        }
        
        try:
            response = await client.post(
                'http://localhost:9999/api/llm/proxy',
                json=proxy_data,
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=60
            )
            result = response.json()
            print(f"状态码: {response.status_code}")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get('code') == 200:
                data = result.get('data', {})
                print(f"\n✓ 测试场景1通过")
                print(f"  使用方法: {data.get('_meta', {}).get('method_used')}")
                extracted_data = {k: v for k, v in data.items() if not k.startswith('_')}
                print(f"  提取的数据: {json.dumps(extracted_data, indent=2, ensure_ascii=False)}")
            else:
                print(f"\n✗ 测试场景1失败: {result.get('msg')}")
        except Exception as e:
            print(f"\n✗ 测试场景1异常: {e}")

        # 测试场景2：从对话记录提取订单信息
        print("\n" + "=" * 60)
        print("测试场景2：从对话记录提取订单信息")
        print("=" * 60)
        
        chat_history = """
用户：我想订购一台笔记本电脑
客服：好的，请问您需要什么配置的？
用户：MacBook Pro 16英寸，32GB内存，1TB硬盘
客服：好的，请问您的收货地址是？
用户：北京市朝阳区建国路88号，联系人：李四，电话：13800138000
"""
        
        proxy_data2 = {
            "query": chat_history,
            "tools": [
                {
                    "name": "extract_order_info",
                    "description": "提取订单信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string", "description": "产品名称"},
                            "specifications": {"type": "string", "description": "产品规格"},
                            "customer_name": {"type": "string", "description": "客户姓名"},
                            "phone": {"type": "string", "description": "联系电话"},
                            "address": {"type": "string", "description": "收货地址"}
                        },
                        "required": ["product_name", "customer_name", "phone", "address"]
                    }
                }
            ],
            "system_prompt": "你是一个订单信息提取助手，请从对话记录中提取订单相关信息。",
            "preferred_methods": ["with_structured_output", "custom_fc_non_stream", "json_parser"]
        }
        
        try:
            response = await client.post(
                'http://localhost:9999/api/llm/proxy',
                json=proxy_data2,
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=60
            )
            result = response.json()
            print(f"状态码: {response.status_code}")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get('code') == 200:
                data = result.get('data', {})
                print(f"\n✓ 测试场景2通过")
                print(f"  使用方法: {data.get('_meta', {}).get('method_used')}")
                extracted_data = {k: v for k, v in data.items() if not k.startswith('_')}
                print(f"  提取的数据: {json.dumps(extracted_data, indent=2, ensure_ascii=False)}")
            else:
                print(f"\n✗ 测试场景2失败: {result.get('msg')}")
        except Exception as e:
            print(f"\n✗ 测试场景2异常: {e}")

        # 测试场景3：提取情感分析结果
        print("\n" + "=" * 60)
        print("测试场景3：情感分析")
        print("=" * 60)
        
        proxy_data3 = {
            "query": "这家餐厅的服务太差了，等了一个小时才上菜，而且味道也不怎么样，非常失望！",
            "tools": [
                {
                    "name": "sentiment_analysis",
                    "description": "分析文本情感",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sentiment": {
                                "type": "string", 
                                "description": "情感倾向",
                                "enum": ["positive", "negative", "neutral"]
                            },
                            "confidence": {
                                "type": "number", 
                                "description": "置信度(0-1)"
                            },
                            "key_points": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "关键观点"
                            }
                        },
                        "required": ["sentiment", "confidence", "key_points"]
                    }
                }
            ],
            "system_prompt": "你是一个情感分析助手，请分析用户评论的情感倾向。",
            "preferred_methods": ["with_structured_output", "json_parser"]
        }
        
        try:
            response = await client.post(
                'http://localhost:9999/api/llm/proxy',
                json=proxy_data3,
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=60
            )
            result = response.json()
            print(f"状态码: {response.status_code}")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get('code') == 200:
                data = result.get('data', {})
                print(f"\n✓ 测试场景3通过")
                print(f"  使用方法: {data.get('_meta', {}).get('method_used')}")
                extracted_data = {k: v for k, v in data.items() if not k.startswith('_')}
                print(f"  提取的数据: {json.dumps(extracted_data, indent=2, ensure_ascii=False)}")
            else:
                print(f"\n✗ 测试场景3失败: {result.get('msg')}")
        except Exception as e:
            print(f"\n✗ 测试场景3异常: {e}")

if __name__ == '__main__':
    asyncio.run(test_proxy_with_chat_history())
