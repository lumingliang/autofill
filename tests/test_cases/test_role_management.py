from tests.config.test_config import config
from tests.utils.api_client import ApiClient, ApiResponse
from tests.utils.auth_manager import test_data

def get_role_id_by_name(role_name: str, client: ApiClient) -> int:
    """根据角色名获取角色ID"""
    response = client.get("/v1/role/list", params={"page": 1, "page_size": 100})
    api_response = ApiResponse(response)
    if api_response.is_success():
        data = api_response.data
        if isinstance(data, list):
            roles = data
        else:
            roles = data.get("data", [])
        for role in roles:
            if role.get("name") == role_name:
                return role.get("id")
    return 0

def test_create_role():
    client = ApiClient(config.base_url)
    client.set_token(test_data.tenant_admin_token)
    
    print("\n=== 测试创建角色 ===")
    response = client.post("/v1/role/create", json={
        "name": config.test_role.name,
        "desc": config.test_role.desc,
        "tenant_id": test_data.tenant_id,
    })
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        test_data.test_role_id = get_role_id_by_name(config.test_role.name, client)
        print(f"✓ 创建角色成功，角色ID: {test_data.test_role_id}")
        return test_data.test_role_id > 0
    else:
        print(f"✗ 创建角色失败: {api_response.message}")
        return False

def test_get_role_list():
    client = ApiClient(config.base_url)
    client.set_token(test_data.tenant_admin_token)
    
    print("\n=== 测试查看角色列表 ===")
    response = client.get("/v1/role/list", params={"page": 1, "page_size": 10})
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        data = api_response.data
        if isinstance(data, list):
            roles = data
        else:
            roles = data.get("data", [])
        print(f"✓ 获取角色列表成功，共 {len(roles)} 个角色")
        return True
    else:
        print(f"✗ 获取角色列表失败: {api_response.message}")
        return False

def test_update_role_authorized():
    client = ApiClient(config.base_url)
    client.set_token(test_data.tenant_admin_token)
    
    if not test_data.test_role_id:
        test_data.test_role_id = get_role_id_by_name(config.test_role.name, client)
    
    if not test_data.test_role_id:
        print("✗ 未找到角色ID，跳过测试")
        return False
    
    print("\n=== 测试更新角色权限 ===")
    response = client.post("/v1/role/authorized", json={
        "id": test_data.test_role_id,
        "menu_ids": [],
        "api_codes": [],
    })
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        print("✓ 更新角色权限成功（无权限时返回成功）")
        return True
    else:
        print(f"✗ 更新角色权限失败: {api_response.message}")
        return False

def test_get_role_authorized():
    client = ApiClient(config.base_url)
    client.set_token(test_data.tenant_admin_token)
    
    if not test_data.test_role_id:
        test_data.test_role_id = get_role_id_by_name(config.test_role.name, client)
    
    if not test_data.test_role_id:
        print("✗ 未找到角色ID，跳过测试")
        return False
    
    print("\n=== 测试查看角色权限 ===")
    response = client.get("/v1/role/authorized", params={"id": test_data.test_role_id})
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        role_data = api_response.data
        if isinstance(role_data, dict):
            menus_count = len(role_data.get("menus", []))
            apis_count = len(role_data.get("apis", []))
            print(f"✓ 获取角色权限成功，菜单数: {menus_count}，API数: {apis_count}")
        else:
            print(f"✓ 获取角色权限成功")
        return True
    else:
        print(f"✗ 获取角色权限失败: {api_response.message}")
        return False

def run_create():
    results = []
    results.append(test_create_role())
    results.append(test_get_role_list())
    return all(results)

def run_update_permission():
    results = []
    results.append(test_update_role_authorized())
    results.append(test_get_role_authorized())
    return all(results)

if __name__ == "__main__":
    test_create_role()
    test_get_role_list()
    test_update_role_authorized()
    test_get_role_authorized()
