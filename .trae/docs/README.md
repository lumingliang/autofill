# 技术约束文档导航

> 本文档用于指导 AI 自动生成代码，必须严格遵守以下约束。

---

## 📚 文档列表

### 快速参考

| 文档 | 用途 | 大小 |
|------|------|------|
| [tech-constraints-core.md](./tech-constraints-core.md) | **核心约束** - 日常使用首选 | ~500行 |

### 分领域详细文档

| 文档 | 内容 |
|------|------|
| [constraints/01-frontend.md](./constraints/01-frontend.md) | 前端开发约束 (Vue3/Pinia/组件) |
| [constraints/02-backend.md](./constraints/02-backend.md) | 后端开发约束 (Python/FastAPI) |
| [constraints/03-database.md](./constraints/03-database.md) | 数据库约束 (Tortoise ORM) |
| [constraints/04-api-design.md](./constraints/04-api-design.md) | API 设计约束 (RESTful/认证/多租户) |
| [constraints/05-logging.md](./constraints/05-logging.md) | 日志记录约束 |
| [constraints/06-testing.md](./constraints/06-testing.md) | 测试文件管理约束 |
| [constraints/07-code-style.md](./constraints/07-code-style.md) | 代码风格约束 (Import规范等) |

---

## 🎯 使用指南

### 场景一：日常开发（推荐）

使用核心约束文档，快速查阅最常用的规则：

```
👉 查看: tech-constraints-core.md
```

### 场景二：新功能开发

根据开发领域选择对应的分领域文档：

- 开发前端页面 → `constraints/01-frontend.md`
- 开发后端 API → `constraints/02-backend.md` + `constraints/04-api-design.md`
- 设计数据模型 → `constraints/03-database.md`

---

## ⚠️ 核心约束速览

### 绝对禁止事项

**前端：**
- ❌ 禁止使用 Options API
- ❌ 禁止组件模板有多个根元素
- ❌ 禁止重复编写表格代码（必须使用 CrudTable）

**后端：**
- ❌ 禁止不使用类型注解
- ❌ 禁止直接查询关联表（必须使用 RelationQuery）
- ❌ 禁止在循环中查询数据库
- ❌ 禁止函数内 import
- ❌ 禁止外键约束
- ❌ 禁止无过滤的全表查询

### 架构分层依赖方向

```
API 层 → Controller 层 → Service 层 → Model 层
```

**禁止反向依赖！**

---

## 🔧 Skill 关联

以下 Skill 与约束文档关联：

| Skill | 关联文档 | 触发场景 |
|-------|---------|---------|
| `architecture-update` | 全部 | 架构变更时 |
| `test-management` | `constraints/06-testing.md` | 创建/移动测试文件时 |

---

## 📝 文档维护

当实现新的架构功能时，必须同步更新：

1. **tech-constraints-core.md** - 核心约束（如影响核心规则）
2. **对应分领域文档** - 如 `constraints/02-backend.md`

### 更新检查清单

- [ ] 检查是否需要更新核心约束 `tech-constraints-core.md`
- [ ] 更新对应分领域文档
- [ ] 确保示例代码与实际实现一致
- [ ] 更新文档最后更新时间

---

*最后更新: 2026-05-05*
