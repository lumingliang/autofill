from tests.config.test_config import config
from tests.utils.api_client import ApiClient, ApiResponse
from tests.utils.auth_manager import test_data

def test_create_tenant():
    client = ApiClient(config.base_url)
    client.set_token(test_data.admin_token)
    
    print("\n=== 测试创建租户 ===")
    response = client.post("/v1/tenant/create", json={
        "name": config.current_tenant.name,
        "domain": config.current_tenant.domain,
        "description": config.current_tenant.description,
    })
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        data = api_response.data
        if isinstance(data, dict):
            tenant_data = data.get("tenant", {})
            test_data.tenant_id = tenant_data.get("id")
            test_data.tenant_admin_role_id = data.get("admin_role_id")
        else:
            test_data.tenant_id = data.get("id")
            test_data.tenant_admin_role_id = None
        print(f"✓ 创建租户成功，租户ID: {test_data.tenant_id}")
        return True
    else:
        print(f"✗ 创建租户失败: {api_response.message}")
        return False

def test_get_tenant_list():
    client = ApiClient(config.base_url)
    client.set_token(test_data.admin_token)
    
    print("\n=== 测试查看租户列表 ===")
    response = client.get("/v1/tenant/list", params={"page": 1, "page_size": 10})
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        data = api_response.data
        if isinstance(data, list):
            tenants = data
        else:
            tenants = data.get("data", data)
        print(f"✓ 获取租户列表成功，共 {len(tenants)} 个租户")
        return True
    else:
        print(f"✗ 获取租户列表失败: {api_response.message}")
        return False

def test_update_tenant():
    client = ApiClient(config.base_url)
    client.set_token(test_data.admin_token)
    
    print("\n=== 测试更新租户 ===")
    response = client.post("/v1/tenant/update", json={
        "id": test_data.tenant_id,
        "name": f"{config.current_tenant.name}-已更新",
        "description": "更新后的描述",
    })
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        print("✓ 更新租户成功")
        return True
    else:
        print(f"✗ 更新租户失败: {api_response.message}")
        return False

def run():
    results = []
    results.append(test_create_tenant())
    results.append(test_get_tenant_list())
    results.append(test_update_tenant())
    return all(results)

if __name__ == "__main__":
    run()
