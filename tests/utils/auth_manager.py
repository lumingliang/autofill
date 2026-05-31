from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class TestData:
    admin_token: Optional[str] = None
    tenant_admin_token: Optional[str] = None
    test_user_token: Optional[str] = None
    
    tenant_id: Optional[int] = None
    tenant_admin_role_id: Optional[int] = None
    tenant_admin_user_id: Optional[int] = None
    test_role_id: Optional[int] = None
    test_user_id: Optional[int] = None
    
    def reset_tenant_data(self):
        self.tenant_id = None
        self.tenant_admin_role_id = None
        self.tenant_admin_user_id = None
        self.test_role_id = None
        self.test_user_id = None
    
    def reset_user_tokens(self):
        self.admin_token = None
        self.tenant_admin_token = None
        self.test_user_token = None
    
    def reset_all(self):
        self.reset_tenant_data()
        self.reset_user_tokens()

test_data = TestData()
