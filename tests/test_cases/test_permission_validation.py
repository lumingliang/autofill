from tests.config.test_config import config
from tests.utils.api_client import ApiClient, ApiResponse
from tests.utils.auth_manager import test_data

def test_tenant_admin_login():
    client = ApiClient(config.base_url)
    
    print("\n=== 测试租户管理员登录 ===")
    response = client.post("/v1/base/access_token", json={
        "username": config.tenant_admin.username,
        "password": config.tenant_admin.password,
    })
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        test_data.tenant_admin_token = api_response.data.get("access_token")
        print(f"✓ 租户管理员登录成功")
        return True
    else:
        print(f"✗ 租户管理员登录失败: {api_response.message}")
        return False

def test_get_user_info():
    client = ApiClient(config.base_url)
    client.set_token(test_data.tenant_admin_token)
    
    print("\n=== 测试获取用户信息 ===")
    response = client.get("/v1/base/userinfo")
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        print("✓ 获取用户信息成功")
        return True
    else:
        print(f"✗ 获取用户信息失败: {api_response.message}")
        return False

def test_get_user_menu():
    client = ApiClient(config.base_url)
    client.set_token(test_data.tenant_admin_token)
    
    print("\n=== 测试获取用户菜单 ===")
    response = client.get("/v1/base/usermenu")
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        menus = api_response.data
        print(f"✓ 获取用户菜单成功，菜单数: {len(menus)}")
        return True
    else:
        print(f"✗ 获取用户菜单失败: {api_response.message}")
        return False

def test_get_user_api():
    client = ApiClient(config.base_url)
    client.set_token(test_data.tenant_admin_token)
    
    print("\n=== 测试获取用户API权限 ===")
    response = client.get("/v1/base/userapi")
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        apis = api_response.data
        print(f"✓ 获取用户API权限成功，API数: {len(apis)}")
        return True
    else:
        print(f"✗ 获取用户API权限失败: {api_response.message}")
        return False

def test_test_user_login():
    client = ApiClient(config.base_url)
    
    print("\n=== 测试普通用户登录 ===")
    response = client.post("/v1/base/access_token", json={
        "username": config.test_user.username,
        "password": config.test_user.password,
    })
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        test_data.test_user_token = api_response.data.get("access_token")
        print(f"✓ 普通用户登录成功")
        return True
    else:
        print(f"✗ 普通用户登录失败: {api_response.message}")
        return False

def test_normal_user_permission():
    client = ApiClient(config.base_url)
    client.set_token(test_data.test_user_token)
    
    print("\n=== 测试普通用户权限验证 ===")
    
    success_count = 0
    
    response = client.get("/v1/base/userinfo")
    if ApiResponse(response).is_success():
        print("✓ 普通用户可访问用户信息")
        success_count += 1
    
    response = client.get("/v1/base/usermenu")
    if ApiResponse(response).is_success():
        print("✓ 普通用户可访问用户菜单")
        success_count += 1
    
    response = client.get("/v1/user/list")
    if ApiResponse(response).is_forbidden():
        print("✓ 普通用户无权限访问用户列表（正确）")
        success_count += 1
    else:
        print("⚠ 普通用户意外获得用户列表访问权限")
    
    return success_count == 3

def test_update_password():
    client = ApiClient(config.base_url)
    client.set_token(test_data.test_user_token)
    
    print("\n=== 测试修改密码 ===")
    response = client.post("/v1/base/update_password", json={
        "old_password": config.test_user.password,
        "new_password": "newpassword123",
    })
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        print("✓ 修改密码成功")
        
        response = client.post("/v1/base/access_token", json={
            "username": config.test_user.username,
            "password": "newpassword123",
        })
        if ApiResponse(response).is_success():
            print("✓ 新密码登录成功")
            config.test_user.password = "newpassword123"
            return True
        else:
            print("✗ 新密码登录失败")
            return False
    else:
        print(f"✗ 修改密码失败: {api_response.message}")
        return False

def run_admin_validation():
    results = []
    results.append(test_tenant_admin_login())
    results.append(test_get_user_info())
    results.append(test_get_user_menu())
    results.append(test_get_user_api())
    return all(results)

def run_user_validation():
    results = []
    results.append(test_test_user_login())
    results.append(test_normal_user_permission())
    results.append(test_update_password())
    return all(results)

if __name__ == "__main__":
    test_tenant_admin_login()
    test_get_user_info()
    test_get_user_menu()
    test_get_user_api()
