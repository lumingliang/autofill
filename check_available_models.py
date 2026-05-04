#!/usr/bin/env python3
"""查看 ModelScope API Key 的可用模型"""
import requests
import sys

API_KEY = "ms-919b1188-52f3-4654-b3bd-c46ab3bcf738"
API_BASE = "https://api-inference.modelscope.cn/v1"

def check_available_models():
    """获取可用模型列表"""
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    try:
        response = requests.get(
            f"{API_BASE}/models",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            
            print(f"✅ API Key 有效")
            print(f"\n可用模型列表 ({len(models)} 个):")
            print("-" * 80)
            
            for model in models:
                model_id = model.get("id", "N/A")
                owned_by = model.get("owned_by", "N/A")
                print(f"  - {model_id} (提供商: {owned_by})")
            
            return True
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_model(model_name: str):
    """测试特定模型是否可用"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ 模型 '{model_name}' 可用")
            return True
        else:
            print(f"❌ 模型 '{model_name}' 测试失败: {response.status_code}")
            print(f"错误: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("ModelScope API 可用模型检查")
    print("=" * 80)
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-4:]}")
    print(f"API Base: {API_BASE}")
    print("=" * 80)
    
    # 获取可用模型列表
    check_available_models()
    
    print("\n" + "=" * 80)
    print("测试特定模型:")
    print("=" * 80)
    
    # 测试一些常见模型
    test_models = [
        "deepseek-ai/DeepSeek-R1-0528",
        "Qwen/Qwen3-32B",
        "qwen/Qwen2.5-72B-Instruct",
        "LLM-Research/c4ai-command-r-plus-08-2024"
    ]
    
    for model in test_models:
        test_model(model)
        print()
