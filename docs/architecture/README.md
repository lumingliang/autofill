# 架构文档目录

## 文档位置说明

项目的架构文档已统一迁移到 `.trae/docs/` 目录，作为 AI 辅助开发的核心参考文档。

### 主架构文档

**位置**: [`.trae/docs/architecture.md`](../../.trae/docs/architecture.md)

该文档包含：
- 项目整体架构设计
- 前端架构（Vue 3 + TypeScript）
- 后端架构（FastAPI + Python）
- 核心功能模块详解
- 数据流图
- 部署架构
- 扩展性设计
- 监控与运维

### 技术约束文档

**位置**: [`.trae/docs/tech-constraints.md`](../../.trae/docs/tech-constraints.md)

该文档包含：
- 前端技术约束
- 后端技术约束
- API 设计规范
- 数据库约束
- 日志记录规范
- 测试文件管理规范
- 等等

## 其他架构相关文档

本目录下还有其他专题架构文档：

| 文档 | 描述 |
|------|------|
| [autofill.md](./autofill.md) | 智能填单系统设计 |
| [autofill-implementation.md](./autofill-implementation.md) | 智能填单实现细节 |
| [kafka_ai_fill_design.md](./kafka_ai_fill_design.md) | Kafka 异步填单设计 |
| [mutil.md](./mutil.md) | 多租户设计 |
| [frontend-redesign.md](./frontend-redesign.md) | 前端重构设计 |

## 历史文档

- `architecture.md.old` - 旧版架构文档（已归档）

## 文档维护规范

1. **主架构文档**更新时，需同步检查 `.trae/docs/tech-constraints.md` 中的相关约束
2. 新增架构功能时，使用 `architecture-update` Skill 确保文档一致性
3. 废弃的文档请重命名为 `.old` 后缀保留，不要直接删除
