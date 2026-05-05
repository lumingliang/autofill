---
name: "architecture-update"
description: "Ensures architecture constraints are documented after implementing new features. Invoke when user creates new architectural patterns, logging mechanisms, API designs, or any infrastructure changes that should be recorded in tech-constraints.md or related constraint documents."
---

# Architecture Update Skill

## When to Invoke

**CRITICAL: Must invoke this skill when:**
- Implementing new logging mechanisms or changing logging patterns
- Creating new API types (public APIs, webhooks, etc.)
- Adding new exception handling patterns
- Changing directory structures or code organization
- Implementing performance optimizations
- Adding new security measures
- Creating new middleware or cross-cutting concerns
- Any architectural decision that affects how code should be written

## Documentation Structure

The project now uses a **分层文档结构** to avoid the large file problem:

```
.trae/docs/
├── README.md                      # 文档导航索引
├── tech-constraints-core.md       # 核心约束精简版 (~500行)
├── tech-constraints.md            # 完整约束文档 (~3400行)
└── constraints/                   # 分领域详细文档
    ├── 01-frontend.md             # 前端约束
    ├── 02-backend.md              # 后端约束
    ├── 03-database.md             # 数据库约束
    ├── 04-api-design.md           # API设计约束
    ├── 05-logging.md              # 日志约束
    ├── 06-testing.md              # 测试约束
    └── 07-code-style.md           # 代码风格约束
```

## Required Actions

After implementing any architectural feature, you MUST:

### 1. Determine Which Document to Update

| Feature Type | Primary Document | Also Update |
|-------------|------------------|-------------|
| Frontend (Vue/Pinia/Components) | `constraints/01-frontend.md` | `tech-constraints-core.md` |
| Backend (Python/FastAPI) | `constraints/02-backend.md` | `tech-constraints-core.md` |
| Database (Tortoise ORM) | `constraints/03-database.md` | `tech-constraints-core.md` |
| API Design (RESTful/Auth) | `constraints/04-api-design.md` | `tech-constraints-core.md` |
| Logging | `constraints/05-logging.md` | `tech-constraints-core.md` |
| Testing | `constraints/06-testing.md` | - |
| Code Style (Import) | `constraints/07-code-style.md` | `tech-constraints-core.md` |
| Cross-cutting concerns | `tech-constraints.md` | Relevant constraint files |

### 2. Update the Constraint Document

Add a new section or update existing sections:

```markdown
## {N}. {Feature Name}规范

### {N}.1 使用规范

> **⚠️ 重要约束**: {关键约束说明}

```python
# ✅ 正确：{正确用法}
{code_example}

# ❌ 错误：{错误用法}
{code_example}
```

### {N}.2 配置示例

{配置说明}
```

### 3. Update Core Constraints (if applicable)

If the feature is **core/critical**, also update `tech-constraints-core.md`:
- Add to "核心约束速览" section
- Add to "快速检查清单"
- Add to "禁止事项清单"

### 4. Update Chapter Mapping

Add the new feature to the chapter mapping tables in:
- `README.md` - 章节映射表
- `tech-constraints-core.md` - 章节映射表
- `tech-constraints.md` - Section 21 (约束文档章节映射表)

```markdown
| 功能模块 | 对应章节 |
|---------|---------|
| {feature_name} | constraints/{N}-{name}.md |
```

### 5. Verify Examples

Ensure all code examples in the documentation:
- [ ] Match the actual implementation
- [ ] Can be copy-pasted and work correctly
- [ ] Follow the project's coding standards
- [ ] Include both ✅ correct and ❌ incorrect examples

### 6. Check Related Skills

If a related Skill exists, update it:
- [ ] Skill description reflects new capabilities
- [ ] Usage examples are current
- [ ] Trigger conditions cover new scenarios

## Documentation Structure

### Standard Sections

Each new architectural feature should include:

1. **Overview** - What problem it solves
2. **Usage Constraints** - Rules for using the feature
3. **Code Examples** - Correct and incorrect usage
4. **Configuration** - How to configure (if applicable)
5. **Integration** - How it integrates with other features
6. **Migration Guide** - How to migrate existing code (if breaking change)

### Example Template

```markdown
## {N}. {Feature Name}

### {N}.1 Overview

{Feature description and purpose}

### {N}.2 Usage Constraints

> **⚠️ 重要约束**: {Critical constraint}

```python
# ✅ 正确：{Description}
{correct_code}

# ❌ 错误：{Description}
{incorrect_code}
```

### {N}.3 Configuration

```python
# {Config file}
{configuration_example}
```

### {N}.4 Integration with Other Features

- {Integration point 1}
- {Integration point 2}
```

## Verification Checklist

Before completing the task:

- [ ] Correct document(s) identified and updated
- [ ] `tech-constraints-core.md` updated (if core feature)
- [ ] `README.md` chapter mapping updated
- [ ] Code examples verified against actual implementation
- [ ] Both correct (✅) and incorrect (❌) examples provided
- [ ] Related Skills updated (if applicable)
- [ ] Documentation follows existing format and style
- [ ] No duplicate or conflicting information

## Common Mistakes to Avoid

1. **Forgetting to update documentation** - Always document immediately after implementation
2. **Updating wrong document** - Use the layered structure, don't just update the wrong file
3. **Inconsistent examples** - Ensure docs match actual code
4. **Missing error examples** - Always show what NOT to do
5. **Vague constraints** - Be specific with "必须" and "禁止"
6. **Wrong chapter numbers** - Check existing chapters before adding new ones

## Reference

- Documentation index: `.trae/docs/README.md`
- Core constraints: `.trae/docs/tech-constraints-core.md`
- Constraint files: `.trae/docs/constraints/`
- Existing skills: `.trae/skills/`
- Example implementations: `app/core/`, `app/api/`
