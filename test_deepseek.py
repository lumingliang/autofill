#!/usr/bin/env python3
"""测试 DeepSeek-R1-0528 模型是否可用"""
import requests
import json

API_KEY = "ms-919b1188-52f3-4654-b3bd-c46ab3bcf738"
API_BASE = "https://api-inference.modelscope.cn/v1"
MODEL = "deepseek-ai/DeepSeek-R1-0528"

def test_model():
    """测试模型调用"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, can you help me?"}
        ],
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    print("=" * 80)
    print(f"测试模型: {MODEL}")
    print(f"API Base: {API_BASE}")
    print("=" * 80)
    
    try:
        print("\n发送请求...")
        response = requests.post(
            f"{API_BASE}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ 模型调用成功!")
            print("\n响应内容:")
            print("-" * 80)
            
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                print(f"回复: {content}")
            
            print("-" * 80)
            print(f"完整响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"\n❌ 模型调用失败")
            print(f"错误: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False

if __name__ == "__main__":
    test_model()
