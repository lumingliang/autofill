import os
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

@dataclass
class AccountConfig:
    username: str
    password: str
    token: Optional[str] = None

@dataclass
class TenantConfig:
    id: Optional[int] = None
    name: str = ""
    domain: str = ""
    description: str = ""
    admin_role_id: Optional[int] = None

@dataclass
class TestUserConfig:
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    password: str = ""
    alias: str = ""
    role_ids: List[int] = field(default_factory=list)

@dataclass
class TestRoleConfig:
    id: Optional[int] = None
    name: str = ""
    desc: str = ""
    menu_ids: List[int] = field(default_factory=list)
    api_codes: List[str] = field(default_factory=list)

@dataclass
class ModuleSwitch:
    system_management: bool = False
    autofill: bool = False
    rule_management: bool = False

@dataclass
class TestConfig:
    base_url: str
    
    admin: AccountConfig
    
    current_tenant: TenantConfig = field(default_factory=TenantConfig)
    
    tenant_admin: TestUserConfig = field(default_factory=TestUserConfig)
    test_user: TestUserConfig = field(default_factory=TestUserConfig)
    test_role: TestRoleConfig = field(default_factory=TestRoleConfig)
    
    switches: ModuleSwitch = field(default_factory=ModuleSwitch)

def get_from_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)

def get_int_from_env(key: str, default: int = 0) -> int:
    val = os.getenv(key, str(default))
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def get_bool_from_env(key: str, default: bool = False) -> bool:
    val = os.getenv(key, str(default)).lower()
    return val in ("true", "1", "yes", "on")

def load_config() -> TestConfig:
    return TestConfig(
        base_url=get_from_env("TEST_BASE_URL", "http://localhost:9999/api"),
        admin=AccountConfig(
            username=get_from_env("TEST_ADMIN_USERNAME", "admin"),
            password=get_from_env("TEST_ADMIN_PASSWORD", "123456"),
        ),
        current_tenant=TenantConfig(
            name=get_from_env("TEST_TENANT_NAME", "测试公司A"),
            domain=get_from_env("TEST_TENANT_DOMAIN", "test-company-a.com"),
            description=get_from_env("TEST_TENANT_DESC", "测试租户A"),
        ),
        tenant_admin=TestUserConfig(
            username=get_from_env("TEST_TENANT_ADMIN_USERNAME", "testadmin"),
            email=get_from_env("TEST_TENANT_ADMIN_EMAIL", "testadmin@test-company-a.com"),
            password=get_from_env("TEST_TENANT_ADMIN_PASSWORD", "123456"),
            alias=get_from_env("TEST_TENANT_ADMIN_ALIAS", "测试管理员"),
        ),
        test_user=TestUserConfig(
            username=get_from_env("TEST_USER_USERNAME", "testuser1"),
            email=get_from_env("TEST_USER_EMAIL", "testuser1@test-company-a.com"),
            password=get_from_env("TEST_USER_PASSWORD", "123456"),
            alias=get_from_env("TEST_USER_ALIAS", "测试用户1"),
        ),
        test_role=TestRoleConfig(
            name=get_from_env("TEST_ROLE_NAME", "普通用户"),
            desc=get_from_env("TEST_ROLE_DESC", "租户内普通用户角色"),
        ),
        switches=ModuleSwitch(
            system_management=get_bool_from_env("TEST_MODULE_SYSTEM_MANAGEMENT", True),
            autofill=get_bool_from_env("TEST_MODULE_AUTOFILL", False),
            rule_management=get_bool_from_env("TEST_MODULE_RULE_MANAGEMENT", False),
        ),
    )

config = load_config()
