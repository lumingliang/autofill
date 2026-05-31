from typing import Optional, Callable, List
from dataclasses import dataclass

@dataclass
class TestCaseResult:
    name: str
    passed: bool
    message: str = ""

@dataclass
class TestModuleResult:
    name: str
    total: int
    passed: int
    failed: int
    cases: List[TestCaseResult]
    
    def is_all_passed(self) -> bool:
        return self.failed == 0

class BaseTestModule:
    def __init__(self, name: str):
        self.name = name
        self.test_cases: List[tuple] = []
        self.setup_func: Optional[Callable] = None
        self.teardown_func: Optional[Callable] = None
        self.retry_on_failure: bool = True
        self.max_retries: int = 1
    
    def add_test(self, test_func: Callable, test_name: str = ""):
        if not test_name:
            test_name = test_func.__name__
        self.test_cases.append((test_func, test_name))
    
    def set_setup(self, setup_func: Callable):
        self.setup_func = setup_func
    
    def set_teardown(self, teardown_func: Callable):
        self.teardown_func = teardown_func
    
    def run(self) -> TestModuleResult:
        cases = []
        passed = 0
        failed = 0
        
        if self.setup_func:
            if not self.setup_func():
                return TestModuleResult(
                    name=self.name,
                    total=len(self.test_cases),
                    passed=0,
                    failed=len(self.test_cases),
                    cases=[TestCaseResult(name="setup", passed=False, message="Setup failed")]
                )
        
        for test_func, test_name in self.test_cases:
            test_passed = False
            error_msg = ""
            
            for attempt in range(self.max_retries):
                try:
                    result = test_func()
                    if result:
                        test_passed = True
                        break
                    else:
                        error_msg = f"测试返回 False"
                        if attempt < self.max_retries - 1:
                            print(f"  ⚠ {test_name} 失败，尝试重试 ({attempt + 1}/{self.max_retries})")
                except Exception as e:
                    import traceback
                    error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                    if attempt < self.max_retries - 1:
                        print(f"  ⚠ {test_name} 异常: {e}，尝试重试 ({attempt + 1}/{self.max_retries})")
            
            if test_passed:
                cases.append(TestCaseResult(name=test_name, passed=True))
                passed += 1
            else:
                if not error_msg:
                    error_msg = "测试失败"
                cases.append(TestCaseResult(name=test_name, passed=False, message=error_msg))
                failed += 1
        
        if self.teardown_func:
            try:
                self.teardown_func()
            except Exception as e:
                print(f"  ⚠ Teardown 异常: {e}")
        
        return TestModuleResult(
            name=self.name,
            total=len(self.test_cases),
            passed=passed,
            failed=failed,
            cases=cases
        )
