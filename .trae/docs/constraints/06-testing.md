# 测试文件管理约束

> 本文档包含测试文件组织的所有约束规则。

---

## 1. 测试目录结构

> **⚠️ 重要约束**: 所有测试文件必须放在 `tests/` 目录下，禁止在项目根目录创建测试文件。

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

---

## 2. 测试分类规范

### 2.1 单元测试 (`tests/unit/`)

**适用场景：**
- 测试单个函数或类
- 测试工具函数、解析器
- 测试业务逻辑
- 测试模型验证

**特点：**
- 执行速度快 (< 100ms)
- 无外部依赖（使用 mock）
- 高代码覆盖率

```python
# ✅ 正确：单元测试示例
# tests/unit/test_curl_parser.py
class TestCurlParser:
    """Curl 解析器测试"""
    
    def test_parse_simple_get(self):
        """测试简单的 GET 请求"""
        curl = "curl https://api.example.com/users"
        result = CurlParser.parse(curl)
        
        assert result.url == "https://api.example.com/users"
        assert result.method == "GET"
```

### 2.2 集成测试 (`tests/integration/`)

**适用场景：**
- 测试 API 端点
- 测试数据库操作
- 测试服务集成
- 测试认证授权

**特点：**
- 可能使用真实数据库
- 测试组件间交互
- 比单元测试慢

```python
# ✅ 正确：集成测试示例
# tests/integration/test_public_api.py
async def test_autofill_api():
    """测试智能填单 API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/public/autofill",
            json={"query": "测试数据"}
        )
        assert response.status_code == 200
```

### 2.3 端到端测试 (`tests/e2e/`)

**适用场景：**
- 测试完整用户故事
- 测试多步骤工作流
- 测试业务场景

**特点：**
- 测试完整业务流程
- 涉及多个 API 调用
- 最慢但最全面

---

## 3. 测试文件命名规范

| 类型 | 命名格式 | 示例 |
|------|---------|------|
| 单元测试 | `test_{module}.py` | `test_curl_parser.py` |
| 集成测试 | `test_{feature}_api.py` | `test_user_api.py` |
| 端到端测试 | `test_{scenario}.py` | `test_user_workflow.py` |

---

## 4. 禁止事项清单

- ❌ 禁止在项目根目录创建测试文件
- ❌ 禁止测试文件放在 `app/` 目录下
- ❌ 禁止测试代码混入业务代码

---

*详细内容请查看 [tech-constraints-core.md](../tech-constraints-core.md)*
*最后更新: 2026-05-05*
