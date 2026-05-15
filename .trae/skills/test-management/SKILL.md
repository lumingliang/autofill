---
name: "test-management"
description: "Manages test file organization and creation. Invoke when user creates, moves, or deletes test files to ensure they follow the project's test directory structure."
---

# Test File Management Skill

## When to Invoke

**CRITICAL: Must invoke this skill when:**
- User creates a new test file
- User moves test files between directories
- User asks about test file organization
- User wants to delete test files
- User asks "测试文件放在哪里"
- User creates temporary/debug test scripts

## Test Directory Structure

All test files MUST be placed in the `tests/` directory with the following structure:

```
tests/
├── __init__.py
├── unit/                    # 单元测试 - 测试单个函数/类
│   ├── __init__.py
│   └── test_*.py
├── integration/             # 集成测试 - 测试多个组件交互
│   ├── __init__.py
│   └── test_*.py
├── e2e/                     # 端到端测试 - 测试完整业务流程
│   ├── __init__.py
│   └── test_*.py
└── scripts/                 # 临时/调试脚本
    ├── __init__.py
    └── test_*.py
```

## Test Category Guidelines

### 1. Unit Tests (`tests/unit/`)

**Purpose:** Test individual functions, classes, or modules in isolation

**Characteristics:**
- Fast execution (< 100ms per test)
- No external dependencies (use mocks)
- Test one thing at a time
- High code coverage

**Examples:**
```python
# tests/unit/test_query_agent.py
class TestCurlParser:
    """测试 Curl 解析器"""
    
    def test_parse_simple_get(self):
        """测试简单的 GET 请求"""
        curl = "curl https://api.example.com/users"
        result = CurlParser.parse(curl)
        assert result.url == "https://api.example.com/users"
        assert result.method == "GET"
```

**When to place here:**
- Testing utility functions
- Testing parsers/formatters
- Testing business logic
- Testing model validation

### 2. Integration Tests (`tests/integration/`)

**Purpose:** Test interaction between multiple components

**Characteristics:**
- May use real database (test database)
- Test API endpoints
- Test service interactions
- Slower than unit tests

**Examples:**
```python
# tests/integration/test_public_api.py
async def test_autofill_api():
    """测试智能填单 API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/public/autofill",
            json={"query": "测试数据"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
```

**When to place here:**
- Testing API endpoints
- Testing database operations
- Testing service integrations
- Testing authentication/authorization

### 3. E2E Tests (`tests/e2e/`)

**Purpose:** Test complete user workflows

**Characteristics:**
- Test full business scenarios
- May involve multiple API calls
- Test real-world use cases
- Slowest but most comprehensive

**Examples:**
```python
# tests/e2e/test_agent_workflow.py
async def test_complete_agent_workflow():
    """测试完整的 Agent 工作流程"""
    # 1. 创建会话
    session = await create_session()
    
    # 2. 发送消息
    response = await send_message(session, "查询上海门店")
    
    # 3. 验证结果
    assert "门店" in response
    assert response["status"] == "success"
```

**When to place here:**
- Testing complete user stories
- Testing multi-step workflows
- Testing business scenarios

### 4. Test Scripts (`tests/scripts/`)

**Purpose:** Temporary/debug scripts for development

**Characteristics:**
- One-time use
- Debugging purposes
- Ad-hoc testing
- Not part of CI/CD

**Examples:**
```python
# tests/scripts/test_debug_api.py
#!/usr/bin/env python3
"""
调试脚本 - 测试特定 API 问题
创建时间: 2024-01-15
创建人: developer
目的: 调试接口响应格式问题
"""

import httpx

async def debug_api():
    # 临时调试代码
    pass

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_api())
```

**When to place here:**
- Debugging specific issues
- Testing new features manually
- One-time verification scripts
- Temporary experiments

## Naming Conventions

### Test Files

```
test_<module_name>.py          # 测试对应模块
test_<feature_name>.py         # 测试特定功能
test_<scenario_name>.py        # 测试特定场景
```

**Examples:**
- `test_query_agent.py` - 测试 QueryAgent 模块
- `test_curl_parser.py` - 测试 Curl 解析功能
- `test_byd_dealer_search.py` - 测试比亚迪门店搜索场景

### Test Functions/Classes

```python
# 测试类
class Test<ModuleName>:          # 如: TestQueryAgent
    
    # 测试方法
    def test_<function_name>_<scenario>(self):  # 如: test_parse_valid_curl
        pass
    
    def test_<function_name>_<edge_case>(self):  # 如: test_parse_invalid_curl
        pass
```

## Creating New Test Files

### Step-by-Step Process

1. **Determine Test Category**
   ```
   Is it testing a single function?     → tests/unit/
   Is it testing API endpoints?         → tests/integration/
   Is it testing complete workflows?    → tests/e2e/
   Is it temporary/debug?               → tests/scripts/
   ```

2. **Create File with Proper Naming**
   ```bash
   # Example: Creating unit test for curl parser
   touch tests/unit/test_curl_parser.py
   ```

3. **Add File Header**
   ```python
   """
   <Module/Feature Name> 测试
   
   测试范围:
   - <测试点1>
   - <测试点2>
   
   作者: <name>
   创建时间: <date>
   """
   ```

4. **Implement Tests**
   ```python
   import pytest
   from app.services.query_agent import CurlParser
   
   class TestCurlParser:
       """Curl 解析器测试"""
       
       def test_parse_simple_get(self):
           """测试简单 GET 请求解析"""
           # Arrange
           curl = "curl https://api.example.com/users"
           
           # Act
           result = CurlParser.parse(curl)
           
           # Assert
           assert result.url == "https://api.example.com/users"
           assert result.method == "GET"
   ```

## Moving Test Files

When moving test files:

1. **Update Imports**
   ```python
   # Before (in root directory)
   from app.services.query_agent import CurlParser
   
   # After (in tests/unit/)
   from app.services.query_agent import CurlParser  # Same, project root is in path
   ```

2. **Verify Tests Still Pass**
   ```bash
   cd /Users/lu/code/code/py/autofill
   python -m pytest tests/unit/test_moved_file.py -v
   ```

## Deleting Test Files

**Before deleting, verify:**

1. **Is it a temporary script?**
   - `tests/scripts/` files can be safely deleted after use
   - Add timestamp to filename for clarity: `test_debug_20240115.py`

2. **Is it duplicated?**
   - Check if functionality is tested elsewhere
   - Keep the most comprehensive version

3. **Is it obsolete?**
   - Check if tested feature still exists
   - Check if test is covered by newer tests

**Safe to delete:**
- Old debug scripts in `tests/scripts/`
- Duplicated tests
- Tests for removed features
- Temporary verification scripts

**Keep:**
- All tests in `tests/unit/`, `tests/integration/`, `tests/e2e/`
- Tests that are part of CI/CD pipeline

## Best Practices

### DO

✅ Place tests in appropriate category directory
✅ Name files clearly: `test_<what_is_being_tested>.py`
✅ Add docstrings explaining test purpose
✅ Use fixtures for common setup
✅ Clean up resources after tests
✅ Add `__init__.py` to new test directories

### DON'T

❌ Create test files in project root
❌ Name tests vaguely: `test1.py`, `test_new.py`
❌ Mix test categories in same file
❌ Leave temporary scripts in root directory
❌ Delete tests without verifying coverage

## Example: Creating a New Test

**Scenario:** Adding test for new BYD dealer service

```bash
# 1. Create file in appropriate directory
touch tests/unit/test_byd_dealer_service.py

# 2. Add content
cat > tests/unit/test_byd_dealer_service.py << 'EOF'
"""
BYD 经销商服务测试

测试范围:
- 经销商查询
- 经销商信息验证
- 搜索过滤功能
"""

import pytest
from app.services.byd_dealer_service import BYDDealerService


class TestBYDDealerService:
    """BYD 经销商服务测试"""
    
    @pytest.fixture
    def service(self):
        return BYDDealerService()
    
    def test_search_by_name(self, service):
        """测试按名称搜索经销商"""
        results = service.search(name="上海")
        assert len(results) > 0
        assert all("上海" in r.name for r in results)
    
    def test_search_by_city(self, service):
        """测试按城市搜索经销商"""
        results = service.search(city="北京")
        assert len(results) > 0
        assert all(r.city == "北京" for r in results)
EOF
```

## Verification Checklist

After creating/moving test files:

- [ ] File is in correct directory (`unit/`, `integration/`, `e2e/`, `scripts/`)
- [ ] File follows naming convention: `test_*.py`
- [ ] Directory has `__init__.py`
- [ ] Tests can be discovered by pytest
- [ ] Tests run successfully
- [ ] No test files in project root

## Related Files

- Test config: `pyproject.toml` (pytest configuration)
- Test data: `docs/tests/data/`
- Test docs: `docs/tests/`
