

## 20. 代码清理规范

### 20.1 核心原则

> **⚠️ 重要约束**: 重构或改造功能后，必须立即删除旧代码，禁止保留兼容性代码。

#### 为什么不要保留旧代码

```
❌ 错误观念："保留旧代码以防万一"
❌ 错误观念："保留兼容性让调用方平滑过渡"
❌ 错误观念："先留着，以后再说"

✅ 正确做法：改造完成 → 验证通过 → 立即删除旧代码
```

**保留旧代码的危害：**
- 代码库膨胀，维护成本增加
- 新开发者困惑（不知道用哪个版本）
- 隐藏 bug（旧代码可能仍有引用）
- 技术债务累积

### 20.2 重构后清理清单

#### 必须删除的内容

```markdown
## 重构后清理检查清单

### 文件清理
- [ ] 旧版服务实现文件
- [ ] 旧版 API 路由文件
- [ ] 旧版类型定义文件
- [ ] 旧版工具函数文件
- [ ] 旧版测试文件（已被新测试替代）

### 代码清理
- [ ] 移除旧版导入语句
- [ ] 移除旧版路由注册
- [ ] 移除旧版配置项
- [ ] 更新引用到新实现

### 文档清理
- [ ] 删除旧版文档
- [ ] 更新引用链接
- [ ] 添加变更说明
```

### 20.3 清理流程

```
1. 实现新功能
   ↓
2. 验证新功能可用（测试通过）
   ↓
3. 立即删除旧代码
   ↓
4. 验证项目仍能正常运行
   ↓
5. 提交代码（包含删除操作）
```

### 20.4 示例：Agent 重构清理

**重构前：**
```
app/services/
├── query_agent/              # 旧版实现
│   ├── __init__.py
│   ├── agent.py
│   ├── nodes.py
│   ├── parser.py
│   ├── types.py
│   ├── utils.py
│   └── prompts.py
└── agent/                    # 新版实现
    ├── __init__.py
    ├── base/
    ├── core/
    └── agents/

app/api/public/
├── query_agent.py            # 旧版 API
└── agents.py                 # 新版 API
```

**重构后（正确做法）：**
```
app/services/
└── agent/                    # 只保留新版
    ├── __init__.py
    ├── base/
    ├── core/
    └── agents/

app/api/public/
└── agents.py                 # 只保留新版
```

**清理操作：**
```bash
# 删除旧版服务
rm -rf app/services/query_agent/

# 删除旧版 API
rm app/api/public/query_agent.py

# 更新路由注册（移除旧版导入和注册）
# vim app/api/public/__init__.py
```

### 20.5 Git 提交规范

**删除代码的提交信息：**
```
chore: remove deprecated query_agent implementation

- Delete app/services/query_agent/ directory
- Delete app/api/public/query_agent.py
- Update public router to remove old imports

The new agent architecture in app/services/agent/
fully replaces the old implementation.
```

### 20.6 禁止事项

```python
# ❌ 错误：保留旧版导入
# app/api/public/__init__.py
from .query_agent import query_agent_public_router  # 旧版
from .agents import agents_router                    # 新版

public_router.include_router(query_agent_public_router)  # 不要保留
public_router.include_router(agents_router)              # 只保留新版

# ❌ 错误：条件编译/运行时切换
if USE_NEW_AGENT:
    from .agents import QueryAgent
else:
    from .query_agent import QueryAgent  # 不要保留

# ❌ 错误：注释掉旧代码而不是删除
# def old_function():  # 不要注释，直接删除
#     pass

# ✅ 正确：只保留新版
from .agents import agents_router
public_router.include_router(agents_router)
```

### 20.7 文档章节对应关系

| 场景 | 操作 |
|------|------|
| 重构服务 | 删除旧服务目录 |
| 重构 API | 删除旧路由文件 + 更新注册 |
| 重构工具函数 | 删除旧工具文件 |
| 重构类型定义 | 删除旧类型文件 |

### 20.8 Skill 关联

- **architecture-update**: 架构变更时执行清理
- **test-management**: 删除旧测试文件

---

## 21. 约束文档章节映射表（完整版）

| 功能模块 | 对应章节 | 说明 |
|---------|---------|------|
| 前端技术约束 | 第 1 章 | Vue/React 开发规范 |
| 后端技术约束 | 第 2 章 | FastAPI/Python 规范 |
| API 认证与多租户 | 第 3 章 | JWT/API Key 认证 |
| 数据库约束 | 第 4 章 | Tortoise ORM 规范 |
| API 设计约束 | 第 5 章 | RESTful API 设计 |
| 前端组件开发 | 第 6 章 | 组件化开发规范 |
| 文件上传 | 第 7 章 | 上传安全规范 |
| 错误处理 | 第 8 章 | 异常处理规范 |
| 日志约束 | 第 9 章 | 日志记录规范 |
| 配置约束 | 第 10 章 | 配置管理规范 |
| 代码生成 | 第 11 章 | 代码生成器规范 |
| 禁止事项清单 | 第 13 章 | 绝对不能做的事 |
| 代码复用架构 | 第 14 章 | 复用设计原则 |
| 检查清单 | 第 15 章 | 代码审查清单 |
| 日志记录规范 | 第 16 章 | 详细日志规范 |
| 公开接口设计 | 第 17 章 | API Key 接口规范 |
| 架构更新约束 | 第 18 章 | 文档更新要求 |
| 测试文件管理 | 第 19 章 | 测试组织规范 |
| 代码清理规范 | 第 20 章 | 重构后清理要求 |
| 架构设计 | [architecture.md](./architecture.md) | 整体架构文档 |

---

*文档最后更新: 2026-05-02*
*版本: v2.0*
