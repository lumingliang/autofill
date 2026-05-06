#!/usr/bin/env python3
"""
调试脚本：检查字段组中的字段
"""
import json
import requests

BASE_URL = "http://localhost:9999/api"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"


def check_field_groups():
    """检查字段组配置"""
    url = f"{BASE_URL}/autofill/field_groups/schema"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 检查服务记录-拖车服务字段组
    data = {
        "page_name": "用户信息页",
        "group_names": ["服务记录-拖车服务"]
    }
    
    print("=" * 70)
    print("检查字段组: 服务记录-拖车服务")
    print("=" * 70)
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        result = resp.json()
        
        if result.get("code") == 200:
            fields = result.get("data", {}).get("fields", [])
            print(f"\n找到 {len(fields)} 个字段:")
            for field in fields:
                print(f"  - {field['field_name']} ({field['field_label']})")
        else:
            print(f"错误: {result.get('msg')}")
    except Exception as e:
        print(f"异常: {e}")


def test_fetch_field_groups():
    """测试 fetch_field_groups 函数"""
    from app.api.public.handlers.field_group_handlers import fetch_field_groups
    import asyncio
    
    async def run_test():
        print("\n" + "=" * 70)
        print("测试 fetch_field_groups 函数")
        print("=" * 70)
        
        # 测试 group_fields 参数
        group_fields = {
            "default": ["救援-二三级"],
            "服务记录-拖车服务": []
        }
        
        result = await fetch_field_groups(
            tenant_id=1,
            app_name="autofill",
            page_name="用户信息页",
            group_names=list(group_fields.keys()),
            field_names=["救援-二三级"],  # 这个会被 group_fields 覆盖
            group_fields=group_fields
        )
        
        print(f"\n返回的字段组数量: {len(result.get('field_groups', []))}")
        for fg in result.get('field_groups', []):
            print(f"\n字段组: {fg['group_name']}")
            print(f"  字段数量: {len(fg.get('field_specs', []))}")
            for field in fg.get('field_specs', []):
                print(f"    - {field['field_name']}")
        
        print(f"\n所有字段规格总数: {len(result.get('all_field_specs', []))}")
        for spec in result.get('all_field_specs', []):
            print(f"  - {spec['field_name']}")
    
    asyncio.run(run_test())


if __name__ == "__main__":
    check_field_groups()
    
    # 需要时再运行内部测试
    # test_fetch_field_groups()
