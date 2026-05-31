from tests.config.test_config import config
from tests.utils.api_client import ApiClient, ApiResponse
from tests.utils.auth_manager import test_data

def cleanup_test_tenant():
    """清理测试租户及其相关数据"""
    client = ApiClient(config.base_url)
    
    print("\n=== 清理测试数据 ===")
    
    if not test_data.admin_token:
        response = client.post("/v1/base/access_token", json={
            "username": config.admin.username,
            "password": config.admin.password,
        })
        api_response = ApiResponse(response)
        if api_response.is_success():
            test_data.admin_token = api_response.data.get("access_token")
    
    client.set_token(test_data.admin_token)
    
    if test_data.tenant_id:
        print(f"正在删除测试租户 (ID: {test_data.tenant_id})...")
        
        response = client.delete("/v1/tenant/delete", params={"tenant_id": test_data.tenant_id})
        api_response = ApiResponse(response)
        if api_response.is_success():
            print(f"✓ 已删除测试租户")
        else:
            print(f"⚠ 删除租户失败: {api_response.message}")
    else:
        print("⚠ 无测试租户需要清理")

def cleanup_test_data():
    """对外暴露的清理函数"""
    try:
        cleanup_test_tenant()
    except Exception as e:
        print(f"⚠ 清理测试数据时出错: {e}")
