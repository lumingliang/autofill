from tests.config.test_config import config
from tests.utils.api_client import ApiClient, ApiResponse
from tests.utils.auth_manager import test_data

class AuthService:
    def __init__(self):
        self.client = ApiClient(config.base_url)
    
    def login_admin(self) -> bool:
        response = self.client.post("/v1/base/access_token", json={
            "username": config.admin.username,
            "password": config.admin.password,
        })
        api_response = ApiResponse(response)
        if api_response.is_success():
            test_data.admin_token = api_response.data.get("access_token")
            return True
        return False
    
    def login_tenant_admin(self) -> bool:
        response = self.client.post("/v1/base/access_token", json={
            "username": config.tenant_admin.username,
            "password": config.tenant_admin.password,
        })
        api_response = ApiResponse(response)
        if api_response.is_success():
            test_data.tenant_admin_token = api_response.data.get("access_token")
            return True
        return False
    
    def login_test_user(self) -> bool:
        response = self.client.post("/v1/base/access_token", json={
            "username": config.test_user.username,
            "password": config.test_user.password,
        })
        api_response = ApiResponse(response)
        if api_response.is_success():
            test_data.test_user_token = api_response.data.get("access_token")
            return True
        return False
    
    def login_by_credentials(self, username: str, password: str) -> tuple[bool, str]:
        response = self.client.post("/v1/base/access_token", json={
            "username": username,
            "password": password,
        })
        api_response = ApiResponse(response)
        if api_response.is_success():
            return True, api_response.data.get("access_token", "")
        return False, ""
    
    def ensure_admin_login(self) -> bool:
        if test_data.admin_token:
            return True
        return self.login_admin()
    
    def ensure_tenant_admin_login(self) -> bool:
        if test_data.tenant_admin_token:
            return True
        return self.login_tenant_admin()
    
    def ensure_test_user_login(self) -> bool:
        if test_data.test_user_token:
            return True
        return self.login_test_user()
    
    def get_admin_client(self) -> ApiClient:
        self.ensure_admin_login()
        client = ApiClient(config.base_url)
        client.set_token(test_data.admin_token)
        return client
    
    def get_tenant_admin_client(self) -> ApiClient:
        self.ensure_tenant_admin_login()
        client = ApiClient(config.base_url)
        client.set_token(test_data.tenant_admin_token)
        return client
    
    def get_test_user_client(self) -> ApiClient:
        self.ensure_test_user_login()
        client = ApiClient(config.base_url)
        client.set_token(test_data.test_user_token)
        return client
    
    def get_client_with_token(self, token: str) -> ApiClient:
        client = ApiClient(config.base_url)
        client.set_token(token)
        return client

auth_service = AuthService()
