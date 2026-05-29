from tests.config.test_config import config
from tests.utils.api_client import ApiClient, ApiResponse
from tests.utils.auth_manager import test_data

def get_user_id_by_username(username: str, client: ApiClient) -> int:
    """根据用户名获取用户ID"""
    response = client.get("/v1/user/list", params={"page": 1, "page_size": 100})
    api_response = ApiResponse(response)
    if api_response.is_success():
        data = api_response.data
        if isinstance(data, list):
            users = data
        else:
            users = data.get("data", [])
        for user in users:
            if user.get("username") == username:
                return user.get("id")
    return 0

def test_create_tenant_admin():
    client = ApiClient(config.base_url)
    client.set_token(test_data.admin_token)
    
    print("\n=== 测试创建租户管理员 ===")
    response = client.post("/v1/user/create", json={
        "username": config.tenant_admin.username,
        "email": config.tenant_admin.email,
        "password": config.tenant_admin.password,
        "alias": config.tenant_admin.alias,
        "role_ids": [test_data.tenant_admin_role_id],
        "tenant_id": test_data.tenant_id,
    })
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        test_data.tenant_admin_user_id = get_user_id_by_username(config.tenant_admin.username, client)
        print(f"✓ 创建租户管理员成功，用户ID: {test_data.tenant_admin_user_id}")
        return True
    else:
        print(f"✗ 创建租户管理员失败: {api_response.message}")
        return False

def test_create_test_user():
    client = ApiClient(config.base_url)
    client.set_token(test_data.tenant_admin_token)
    
    print("\n=== 测试创建普通用户 ===")
    response = client.post("/v1/user/create", json={
        "username": config.test_user.username,
        "email": config.test_user.email,
        "password": config.test_user.password,
        "alias": config.test_user.alias,
        "role_ids": [test_data.test_role_id] if test_data.test_role_id else [],
        "tenant_id": test_data.tenant_id,
    })
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        test_data.test_user_id = get_user_id_by_username(config.test_user.username, client)
        print(f"✓ 创建普通用户成功，用户ID: {test_data.test_user_id}")
        return True
    else:
        print(f"✗ 创建普通用户失败: {api_response.message}")
        return False

def test_get_user_list():
    client = ApiClient(config.base_url)
    client.set_token(test_data.tenant_admin_token)
    
    print("\n=== 测试查看用户列表 ===")
    response = client.get("/v1/user/list", params={"page": 1, "page_size": 10})
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        data = api_response.data
        if isinstance(data, list):
            users = data
        else:
            users = data.get("data", [])
        print(f"✓ 获取用户列表成功，共 {len(users)} 个用户")
        return True
    else:
        print(f"✗ 获取用户列表失败: {api_response.message}")
        return False

def run_create_admin():
    return test_create_tenant_admin()

def run_create_user():
    results = []
    results.append(test_create_test_user())
    results.append(test_get_user_list())
    return all(results)

if __name__ == "__main__":
    test_create_tenant_admin()
    test_create_test_user()
    test_get_user_list()
