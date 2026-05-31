import os
import sys
import time
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.config.test_config import config
from tests.utils.test_framework import TestModuleResult
from tests.utils.db_backup import db_backup
from tests.test_cases.test_admin_login import test_admin_login
from tests.test_cases.test_tenant_management import test_create_tenant, test_get_tenant_list, test_update_tenant
from tests.test_cases.test_user_management import test_create_tenant_admin, test_create_test_user, test_get_user_list
from tests.test_cases.test_role_management import test_create_role, test_get_role_list, test_update_role_authorized, test_get_role_authorized
from tests.test_cases.test_permission_validation import (
    test_tenant_admin_login, test_get_user_info, test_get_user_menu, test_get_user_api,
    test_test_user_login, test_normal_user_permission, test_update_password
)
from tests.test_cases.test_cleanup import cleanup_test_data

def print_module_result(result: TestModuleResult):
    print(f"\n{'='*60}")
    print(f"【{result.name}】")
    print(f"{'='*60}")
    for case in result.cases:
        if case.passed:
            print(f"  ✓ {case.name}")
        else:
            print(f"  ✗ {case.name}")
    print(f"\n通过: {result.passed}/{result.total} | 失败: {result.failed}")

def print_summary(results: list):
    total_modules = len(results)
    total_cases = sum(r.total for r in results)
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)
    
    print(f"\n{'='*60}")
    print(f"【测试结果汇总】")
    print(f"{'='*60}")
    print(f"模块总数: {total_modules}")
    print(f"用例总数: {total_cases}")
    print(f"通过: {total_passed}")
    print(f"失败: {total_failed}")
    print(f"{'='*60}")
    
    if total_failed > 0:
        print("\n失败的模块:")
        for r in results:
            if r.failed > 0:
                print(f"  - {r.name}: {r.failed} 个失败")
        return False
    return True

def restart_backend_service():
    print("="*60)
    print("正在重启后端服务...")
    print("="*60)
    
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    start_script = os.path.join(project_dir, "start.sh")
    
    try:
        result = subprocess.run(
            [start_script, "be", "restart"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print("等待服务启动...")
        time.sleep(5)
        
        max_wait = 20
        for i in range(max_wait):
            try:
                import requests
                response = requests.get(f"{config.base_url}/api/v1/base/userinfo", timeout=2)
                print(f"✓ 后端服务就绪 (耗时 {i+5} 秒)")
                return True
            except:
                time.sleep(1)
        
        print("⚠ 后端服务可能未完全就绪，继续测试...")
        return True
            
    except subprocess.TimeoutExpired:
        print("⚠ 后端服务重启超时，尝试继续...")
        return True
    except Exception as e:
        print(f"⚠ 后端服务重启异常: {e}，继续测试...")
        return True

def run_system_management_module() -> TestModuleResult:
    from tests.utils.test_framework import BaseTestModule
    
    module = BaseTestModule("系统管理模块")
    
    module.add_test(test_admin_login, "1.超管登录")
    module.add_test(test_get_tenant_list, "2.查看租户列表")
    module.add_test(test_create_tenant, "3.创建租户")
    module.add_test(test_create_tenant_admin, "4.创建租户管理员")
    module.add_test(test_tenant_admin_login, "5.租户管理员登录")
    module.add_test(test_get_user_info, "6.获取用户信息")
    module.add_test(test_get_user_menu, "7.获取用户菜单")
    module.add_test(test_get_user_api, "8.获取用户API")
    module.add_test(test_get_role_list, "9.查看角色列表")
    module.add_test(test_create_role, "10.创建角色")
    module.add_test(test_get_role_authorized, "11.查看角色权限")
    module.add_test(test_update_role_authorized, "12.更新角色权限")
    module.add_test(test_get_user_list, "13.查看用户列表")
    
    return module.run()

def run_autofill_module() -> TestModuleResult:
    from tests.utils.test_framework import BaseTestModule
    
    module = BaseTestModule("AutoFill模块")
    module.add_test(lambda: True, "AutoFill功能占位测试")
    print("\n  ⚠ AutoFill模块测试尚未实现")
    return module.run()

def run_rule_management_module() -> TestModuleResult:
    from tests.utils.test_framework import BaseTestModule
    
    module = BaseTestModule("规则管理模块")
    module.add_test(lambda: True, "规则管理功能占位测试")
    print("\n  ⚠ 规则管理模块测试尚未实现")
    return module.run()

def main():
    print("="*60)
    print("API 自动化测试框架")
    print("="*60)
    
    timestamp = int(time.time()) % 100000
    
    config.current_tenant.name = f"测试租户{timestamp}"
    config.current_tenant.domain = f"tenant{timestamp}"
    config.tenant_admin.username = f"tadmin{timestamp}"
    config.tenant_admin.email = f"tadmin{timestamp}@test.com"
    config.test_user.username = f"tuser{timestamp}"
    config.test_user.email = f"tuser{timestamp}@test.com"
    config.test_role.name = f"角色{timestamp}"
    
    switches = config.switches
    print(f"\n模块开关配置:")
    print(f"  系统管理模块: {'✓' if switches.system_management else '✗'}")
    print(f"  AutoFill模块: {'✓' if switches.autofill else '✗'}")
    print(f"  规则管理模块: {'✓' if switches.rule_management else '✗'}")
    print(f"\n本次测试数据:")
    print(f"  租户: {config.current_tenant.domain}")
    print(f"  管理员: {config.tenant_admin.username}")
    print(f"  用户: {config.test_user.username}")
    print(f"  角色: {config.test_role.name}")
    
    print(f"\n{'='*60}")
    print("【第一步：重启后端服务】")
    print(f"{'='*60}")
    restart_backend_service()
    
    results: list[TestModuleResult] = []
    all_passed = False
    
    if switches.system_management:
        result = run_system_management_module()
        results.append(result)
        print_module_result(result)
    
    if switches.autofill:
        result = run_autofill_module()
        results.append(result)
        print_module_result(result)
    
    if switches.rule_management:
        result = run_rule_management_module()
        results.append(result)
        print_module_result(result)
    
    if not results:
        print("\n⚠ 没有启用的测试模块，请修改环境变量 TEST_MODULE_*=true")
        return
    
    all_passed = print_summary(results)
    
    print(f"\n{'='*60}")
    print("【第三步：清理测试数据】")
    print(f"{'='*60}")
    cleanup_test_data()
    
    if all_passed:
        print("\n✓ 所有测试通过")
        sys.exit(0)
    else:
        print("\n✗ 存在失败的测试")
        sys.exit(1)

if __name__ == "__main__":
    main()
