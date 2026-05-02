"""
测试 CurlParser 功能

这个测试不需要数据库，可以独立运行验证解析功能。
"""
import json
from app.services.agent import CurlParser


def test_post_json():
    """测试 POST JSON 请求"""
    print("\n测试 1: POST JSON 请求")
    curl = """curl -X POST 'http://api.example.com/search' -H 'Content-Type: application/json' -d '{"name": "体验中心", "city": "上海", "page": 1}'"""

    parsed = CurlParser.parse(curl)

    assert parsed.url == "http://api.example.com/search"
    assert parsed.method == "POST"
    assert parsed.headers.get("Content-Type") == "application/json"
    assert parsed.body_params.get("name") == "体验中心"
    assert parsed.body_params.get("city") == "上海"
    assert parsed.body_params.get("page") == 1  # 整数类型

    print(f"  ✅ URL: {parsed.url}")
    print(f"  ✅ Method: {parsed.method}")
    print(f"  ✅ Body Params: {parsed.body_params}")
    print(f"  ✅ Param Schemas: {len(parsed.param_schemas)} 个")


def test_get_with_query():
    """测试 GET 带查询参数"""
    print("\n测试 2: GET 带查询参数")
    curl = """curl 'http://api.example.com/search?keyword=体验中心&city=上海&limit=10'"""

    parsed = CurlParser.parse(curl)

    assert parsed.method == "GET"
    assert parsed.query_params.get("keyword") == "体验中心"
    assert parsed.query_params.get("city") == "上海"
    assert parsed.query_params.get("limit") == 10  # 整数类型

    print(f"  ✅ URL: {parsed.url}")
    print(f"  ✅ Query Params: {parsed.query_params}")


def test_complex_headers():
    """测试复杂 Headers"""
    print("\n测试 3: 复杂 Headers")
    curl = """curl -X POST 'http://api.example.com/api' \
        -H 'Authorization: Bearer token123' \
        -H 'Content-Type: application/json' \
        -H 'X-Request-ID: abc-123' \
        -d '{"data": "test"}'"""

    parsed = CurlParser.parse(curl)

    assert parsed.headers.get("Authorization") == "Bearer token123"
    assert parsed.headers.get("Content-Type") == "application/json"
    assert parsed.headers.get("X-Request-ID") == "abc-123"

    print(f"  ✅ Headers: {list(parsed.headers.keys())}")


def test_form_data():
    """测试 Form Data"""
    print("\n测试 4: Form Data")
    curl = """curl -X POST 'http://api.example.com/form' \
        -H 'Content-Type: application/x-www-form-urlencoded' \
        -d 'name=张三&age=25&active=true'"""

    parsed = CurlParser.parse(curl)

    assert parsed.body_params.get("name") == "张三"
    assert parsed.body_params.get("age") == "25"
    assert parsed.body_params.get("active") == "true"

    print(f"  ✅ Body Params: {parsed.body_params}")


def test_rebuild_curl():
    """测试重建 curl"""
    print("\n测试 5: 重建 curl")
    curl = """curl -X POST 'http://api.example.com/search' -H 'Content-Type: application/json' -d '{"name": "test", "city": "上海"}'"""

    parsed = CurlParser.parse(curl)
    params = {"name": "体验中心", "city": "北京"}

    new_curl = CurlParser.build_curl(parsed, params)

    print(f"  原始: {curl[:60]}...")
    print(f"  参数: {params}")
    print(f"  重建: {new_curl[:60]}...")

    assert "体验中心" in new_curl
    assert "北京" in new_curl
    print("  ✅ 重建成功")


def test_no_params():
    """测试无参数 curl"""
    print("\n测试 6: 无参数 curl")
    curl = """curl 'http://api.example.com/health'"""

    parsed = CurlParser.parse(curl)

    assert parsed.method == "GET"
    assert len(parsed.param_schemas) == 0

    print(f"  ✅ 无参数，直接执行")


def test_type_inference():
    """测试类型推断"""
    print("\n测试 7: 类型推断")
    curl = """curl 'http://api.example.com/search?id=123&price=99.99&active=true&name=test'"""

    parsed = CurlParser.parse(curl)

    assert parsed.query_params.get("id") == 123  # int
    assert parsed.query_params.get("price") == 99.99  # float
    assert parsed.query_params.get("active") == True  # bool
    assert parsed.query_params.get("name") == "test"  # string

    print(f"  ✅ id: {type(parsed.query_params.get('id')).__name__} = {parsed.query_params.get('id')}")
    print(f"  ✅ price: {type(parsed.query_params.get('price')).__name__} = {parsed.query_params.get('price')}")
    print(f"  ✅ active: {type(parsed.query_params.get('active')).__name__} = {parsed.query_params.get('active')}")


def main():
    """主测试函数"""
    print("=" * 60)
    print("CurlParser 功能测试")
    print("=" * 60)

    tests = [
        test_post_json,
        test_get_with_query,
        test_complex_headers,
        test_form_data,
        test_rebuild_curl,
        test_no_params,
        test_type_inference,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
