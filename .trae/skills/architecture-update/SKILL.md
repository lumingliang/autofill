---
name: "architecture-update"
description: "Ensures architecture constraints are documented after implementing new features. Invoke when user creates new architectural patterns, logging mechanisms, API designs, or any infrastructure changes that should be recorded in tech-constraints.md."
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

## Required Actions

After implementing any architectural feature, you MUST:

### 1. Update tech-constraints.md

Add a new section or update existing sections in `.trae/docs/tech-constraints.md`:

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

### 2. Update Chapter Mapping

Add the new feature to the chapter mapping table in Section 18.1:

```markdown
| 功能模块 | 对应章节 |
|---------|---------|
| {feature_name} | 第 {N} 章 |
```

### 3. Verify Examples

Ensure all code examples in the documentation:
- [ ] Match the actual implementation
- [ ] Can be copy-pasted and work correctly
- [ ] Follow the project's coding standards
- [ ] Include both ✅ correct and ❌ incorrect examples

### 4. Check Related Skills

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

- [ ] New section added to tech-constraints.md
- [ ] Chapter mapping updated
- [ ] Code examples verified against actual implementation
- [ ] Both correct (✅) and incorrect (❌) examples provided
- [ ] Related Skills updated (if applicable)
- [ ] Documentation follows existing format and style
- [ ] No duplicate or conflicting information

## Common Mistakes to Avoid

1. **Forgetting to update documentation** - Always document immediately after implementation
2. **Inconsistent examples** - Ensure docs match actual code
3. **Missing error examples** - Always show what NOT to do
4. **Vague constraints** - Be specific with "必须" and "禁止"
5. **Wrong chapter numbers** - Check existing chapters before adding new ones

## Reference

- Full documentation: `.trae/docs/tech-constraints.md`
- Existing skills: `.trae/skills/`
- Example implementations: `app/core/`, `app/api/`
