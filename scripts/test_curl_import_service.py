#!/usr/bin/env python3
"""
测试 CurlImportService 的变量替换功能
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.services.rule_management.curl_import_service import CurlImportService


# 测试配置 - 与用户提供的配置相同
TEST_CONFIG = {
    "description": "事件类型级联请求导入(2层)",
    "output_file": "event_type_cascade_output.csv",
    "yaml_file": "event_type_cascade_config.yaml",
    "global_vars": {
        "API_KEY": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
        "BASE_URL": "http://localhost:9999",
        "CLASS_NAME": "事件类型"
    },
    "data_root_path": "$.data",
    "level_config": {
        "level1": {
            "source": {"type": "request", "index": 0},
            "fields": [
                {"csv_header": "level1", "jsonpath": "$.option_value"},
                {"csv_header": "level1_summary", "jsonpath": "$.summary"},
                {"csv_header": "level1_id", "jsonpath": "$.id"}
            ],
            "children_jsonpath": "$.children",
            "params": {}
        },
        "level2": {
            "source": {"type": "request", "index": 1},
            "fields": [
                {"csv_header": "level2", "jsonpath": "$.option_value"},
                {"csv_header": "level2_summary", "jsonpath": "$.summary"}
            ],
            "children_jsonpath": "$.children",
            "params": {
                "parent_value": "level1.level1"
            }
        },
        "level3": {
            "source": {"type": "children", "from_level": "level2"},
            "fields": [
                {"csv_header": "level3", "jsonpath": "$.option_value"},
                {"csv_header": "level3_summary", "jsonpath": "$.summary"}
            ],
            "children_jsonpath": None,
            "params": {}
        }
    },
    "curl_commands": [
        """curl -X POST "http://localhost:9999/api/autofill/dropdown/first_level" \
  -H "Authorization: Bearer {API_KEY}" \
  -d '{"class_name": "事件类型"}'""",
        """curl -X POST "http://localhost:9999/api/autofill/dropdown/submenus_tree" \
  -H "Authorization: Bearer {API_KEY}" \
  -d '{"first_level_value": "{parent_value}", "class_name": "事件类型"}'"""
    ]
}


async def test_curl_import():
    """测试 CURL 导入服务"""
    print("=" * 60)
    print("测试 CurlImportService 变量替换功能")
    print("=" * 60)
    
    # 创建服务实例
    service = CurlImportService(TEST_CONFIG)
    
    print(f"\n📋 配置信息:")
    print(f"   模式: {service.mode}")
    print(f"   请求数: {len(service.curl_commands)}")
    print(f"   层级数: {len(service.level_names)}")
    print(f"   全局变量: {service.global_vars}")
    
    # 测试变量替换功能
    print("\n" + "=" * 60)
    print("测试变量替换")
    print("=" * 60)
    
    # 测试 headers 替换
    test_headers = {
        "Authorization": "Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    replaced_headers = service.replace_variables(test_headers, service.global_vars)
    print(f"\n原始 headers: {test_headers}")
    print(f"替换后 headers: {replaced_headers}")
    
    # 验证替换是否正确
    expected_auth = f"Bearer {TEST_CONFIG['global_vars']['API_KEY']}"
    if replaced_headers.get("Authorization") == expected_auth:
        print("✅ Headers 变量替换正确!")
    else:
        print(f"❌ Headers 变量替换失败!")
        print(f"   期望: {expected_auth}")
        print(f"   实际: {replaced_headers.get('Authorization')}")
        return False
    
    # 测试 URL 替换
    test_url = "{BASE_URL}/api/test"
    replaced_url = service.replace_variables(test_url, service.global_vars)
    print(f"\n原始 URL: {test_url}")
    print(f"替换后 URL: {replaced_url}")
    
    expected_url = f"{TEST_CONFIG['global_vars']['BASE_URL']}/api/test"
    if replaced_url == expected_url:
        print("✅ URL 变量替换正确!")
    else:
        print(f"❌ URL 变量替换失败!")
        return False
    
    # 测试 JSON 数据替换
    test_json = {
        "class_name": "{CLASS_NAME}",
        "api_key": "{API_KEY}"
    }
    replaced_json = service.replace_variables(test_json, service.global_vars)
    print(f"\n原始 JSON: {test_json}")
    print(f"替换后 JSON: {replaced_json}")
    
    if replaced_json.get("class_name") == TEST_CONFIG['global_vars']['CLASS_NAME']:
        print("✅ JSON 变量替换正确!")
    else:
        print(f"❌ JSON 变量替换失败!")
        return False
    
    # 执行实际的 CURL 请求测试
    print("\n" + "=" * 60)
    print("执行实际 CURL 请求测试")
    print("=" * 60)
    
    try:
        result = await service.fetch_data()
        print(f"\n✅ 请求成功!")
        print(f"   表头: {result['headers']}")
        print(f"   数据行数: {result['row_count']}")
        print(f"   模式: {result['mode']}")
        
        if result['data']:
            print(f"\n前3行数据:")
            for i, row in enumerate(result['data'][:3]):
                print(f"   行{i+1}: {row}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_curl_import())
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过!")
    else:
        print("❌ 测试失败!")
        sys.exit(1)
