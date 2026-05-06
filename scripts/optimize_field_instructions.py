#!/usr/bin/env python3
"""
批量优化字段填写指引脚本

功能：
1. 遍历指定页面/字段组下的所有字段
2. 每批N个字段调用LLM接口优化填写指引
3. 自动更新优化后的指引到数据库

使用示例：
  # 优化整个页面的所有字段
  python optimize_field_instructions.py --page-name "用户信息页"
  
  # 优化指定字段组的所有字段
  python optimize_field_instructions.py --page-name "用户信息页" --group-name "default"
  
  # 优化单个字段
  python optimize_field_instructions.py --page-name "用户信息页" --field-name "scene_category"
  
  # 自定义每批处理的字段数量
  python optimize_field_instructions.py --page-name "用户信息页" --batch-size 5
"""
import argparse
import json
import sys
import time

import requests

# 配置
BASE_URL = "http://localhost:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"


def optimize_instructions(
    page_name: str,
    group_name: str = None,
    field_name: str = None,
    batch_size: int = 10,
    model: str = None
) -> dict:
    """
    调用接口优化字段填写指引
    
    Args:
        page_name: 页面名称（必填）
        group_name: 字段组名称（可选）
        field_name: 单个字段名称（可选）
        batch_size: 每批处理的字段数量（默认10）
        model: 使用的模型名称（可选）
    
    Returns:
        优化结果
    """
    url = f"{BASE_URL}/autofill/llm/optimize_instructions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "page_name": page_name,
        "batch_size": batch_size
    }
    
    if group_name:
        data["group_name"] = group_name
    
    if field_name:
        data["field_name"] = field_name
    
    if model:
        data["model"] = model
    
    print(f"\n{'=' * 70}")
    print("优化字段填写指引")
    print('=' * 70)
    print(f"页面名称: {page_name}")
    if group_name:
        print(f"字段组: {group_name}")
    if field_name:
        print(f"单个字段: {field_name}")
    print(f"每批处理: {batch_size} 个字段")
    if model:
        print(f"使用模型: {model}")
    
    print(f"\n请求: POST {url}")
    
    try:
        start_time = time.time()
        resp = requests.post(url, headers=headers, json=data, timeout=300)
        elapsed_time = time.time() - start_time
        
        print(f"状态码: {resp.status_code}")
        print(f"耗时: {elapsed_time:.2f} 秒")
        
        result = resp.json()
        
        if result.get("code") == 200:
            data = result.get("data", {})
            optimized_count = data.get("optimized_count", 0)
            total_count = data.get("total_count", 0)
            results = data.get("results", [])
            
            print(f"\n✅ 优化完成")
            print(f"  成功: {optimized_count} / {total_count}")
            
            if results:
                print(f"\n详细结果:")
                for item in results:
                    field_name = item.get("field_name")
                    field_label = item.get("field_label")
                    success = item.get("success")
                    
                    if success:
                        print(f"\n  ✅ {field_name} ({field_label})")
                        print(f"     原指引: {item.get('original_instruction', 'N/A')[:50]}...")
                        print(f"     新指引: {item.get('optimized_instruction', 'N/A')[:50]}...")
                    else:
                        print(f"\n  ❌ {field_name} ({field_label})")
                        print(f"     错误: {item.get('error', 'Unknown error')}")
            
            return data
        else:
            print(f"\n❌ 错误: {result.get('msg')}")
            return None
    
    except requests.exceptions.Timeout:
        print(f"\n❌ 请求超时")
        return None
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="批量优化字段填写指引",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 优化整个页面的所有字段
  python optimize_field_instructions.py --page-name "用户信息页"
  
  # 优化指定字段组的所有字段
  python optimize_field_instructions.py --page-name "用户信息页" --group-name "default"
  
  # 优化单个字段
  python optimize_field_instructions.py --page-name "用户信息页" --field-name "scene_category"
  
  # 自定义每批处理的字段数量
  python optimize_field_instructions.py --page-name "用户信息页" --batch-size 5
        """
    )
    
    parser.add_argument(
        "--page-name",
        required=True,
        help="页面名称（必填）"
    )
    
    parser.add_argument(
        "--group-name",
        default=None,
        help="字段组名称（可选，不传则优化页面下所有字段）"
    )
    
    parser.add_argument(
        "--field-name",
        default=None,
        help="单个字段名称（可选，传了则只优化该字段）"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="每批处理的字段数量（默认10个）"
    )
    
    parser.add_argument(
        "--model",
        default=None,
        help="使用的模型名称（可选，默认使用系统配置）"
    )
    
    args = parser.parse_args()
    
    # 执行优化
    result = optimize_instructions(
        page_name=args.page_name,
        group_name=args.group_name,
        field_name=args.field_name,
        batch_size=args.batch_size,
        model=args.model
    )
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
