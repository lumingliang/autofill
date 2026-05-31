from tests.config.test_config import config
from tests.utils.api_client import ApiClient, ApiResponse
from tests.utils.auth_manager import test_data

def test_admin_login():
    client = ApiClient(config.base_url)
    
    print("\n=== 测试超级管理员登录 ===")
    response = client.post("/v1/base/access_token", json={
        "username": config.admin.username,
        "password": config.admin.password,
    })
    
    api_response = ApiResponse(response)
    if api_response.is_success():
        test_data.admin_token = api_response.data.get("access_token")
        print(f"✓ 登录成功")
        return True
    else:
        print(f"✗ 登录失败: {api_response.message}")
        return False

def run():
    return test_admin_login()

if __name__ == "__main__":
    run()
