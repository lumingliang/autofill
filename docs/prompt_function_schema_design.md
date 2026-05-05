# Prompt 与 Function Calling Schema 组装设计方案

## 1. 设计目标

为智能填单系统提供统一的 Prompt 组装和 Function Calling Schema 生成能力，支持：
- 纯文本 Prompt 模式（用于直接 LLM 调用）
- Function Calling 模式（用于 OpenAI/Claude 等模型的函数调用）
- 多字段组合并查询场景

## 2. 核心组件

### 2.1 PromptService (app/services/autofill/prompt_service.py)

#### 2.1.1 build_fields_instructions(fields)
**功能**：组装字段指令文本

**输入**：字段明细列表 `List[FieldSpec]`

**输出**：字段指令字符串

**处理逻辑**：
```
对于每个字段：
  如果是 text 类型：
    - 格式："- {field_label}（字段名：`{field_name}`）：{fill_instruction}"
    - 如果有 corrections，追加"人工补充规则"
  
  如果是 select 类型：
    - 格式："- {field_label}（字段名：`{field_name}`）：{global_instruction}\n可选值：\n  - {option1}\n  - {option2}..."
    - 每个选项包含 label、fill_instruction、corrections
    - 追加"只能从上述选项中选择一个值"
```

#### 2.1.2 build_function_schema(field_group, fields)
**功能**：生成 OpenAI Function Calling Schema

**输入**：
- `field_group`: 字段组配置
- `fields`: 字段明细列表

**输出**：Function Calling Schema (Dict)

**Schema 结构**：
```json
{
  "type": "function",
  "function": {
    "name": "extract_form_data",
    "description": "从对话中提取表单数据",
    "parameters": {
      "type": "object",
      "properties": {
        "field_name1": {
          "type": "string",
          "description": "字段描述"
        },
        "field_name2": {
          "type": "string",
          "description": "字段描述",
          "enum": ["选项1", "选项2"]
        }
      },
      "required": ["field_name1", "field_name2"]
    }
  }
}
```

**处理逻辑**：
- text 类型：生成 `{"type": "string", "description": ...}`
- select 类型：生成 `{"type": "string", "description": ..., "enum": [...]}`
- 所有字段默认都是 required

#### 2.1.3 assemble_prompt(field_group, fields, query)
**功能**：组装完整 Prompt

**输入**：
- `field_group`: 字段组配置（包含 prompt_template_base）
- `fields`: 字段明细列表
- `query`: 用户查询内容

**处理逻辑**：
1. 使用字段组的 `prompt_template_base` 作为模板
2. 替换模板变量：
   - `{{fields_instructions}}` → 字段指令文本
   - `{{query}}` → 用户查询内容
3. 返回组装后的 Prompt

**默认模板**：
```
你是一个智能填单助手。请根据以下对话内容，提取指定字段的信息。

需要提取的字段：
{{fields_instructions}}

对话内容：
{{query}}

请严格按照字段要求提取信息，并以JSON格式返回结果。
```

## 3. 接口层实现

### 3.1 /autofill/field_group (GET/POST)

**功能**：查询字段组配置，返回完整 Schema 信息

**请求参数**：
- `page_name`: 页面名称（必填）
- `group_names`: 字段组名称列表（可选）
- `field_names`: 字段名称列表（可选，用于筛选）

**返回结构**：
```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "group_name": "default",
      "group_code": "fg_xxx",
      "field_specs": [...],
      "prompt_info": {
        "template_base": "...",
        "fields_instructions": "...",
        "assembled_prompt": "..."
      },
      "function_calling": {
        "schema": {...},
        "json_schema": "..."
      }
    }
  ]
}
```

**组装逻辑**：
1. 查询字段组及其关联字段
2. 调用 `build_fields_instructions()` 生成字段指令
3. 调用 `build_function_schema()` 生成 Function Schema
4. 调用 `assemble_prompt()` 生成示例 Prompt

### 3.2 /autofill/field_groups/schema (GET/POST) - 合并接口

**功能**：查询多个字段组的完整 Schema，支持合并输出

**请求参数**：
- `page_name`: 页面名称（必填）
- `group_names`: 字段组名称列表（可选）
- `field_names`: 字段名称列表（可选）

**使用场景**：
1. **只传 group_names**：返回这些字段组下所有字段的完整信息
2. **传 group_names + field_names**：仅返回指定字段的完整信息
3. **只传 field_names**：返回包含这些字段的所有字段组信息

**返回结构**：
```json
{
  "code": 200,
  "data": {
    "field_groups": [...],
    "fields_summary": {
      "total_fields": 13,
      "field_names": [...]
    },
    "combined_schema": {
      "prompt_info": {
        "template_base": "...",
        "fields_instructions": "...",
        "assembled_prompt": "..."
      },
      "function_calling": {
        "schema": {...},
        "json_schema": "..."
      }
    }
  }
}
```

**合并 Schema 组装逻辑**：
1. 收集所有字段（去重）
2. 使用第一个字段组的模板作为基础
3. 调用 `build_fields_instructions()` 生成合并后的字段指令
4. 构建合并后的 Function Schema：
   ```python
   {
     "name": "fill_form",
     "description": "自动填单函数",
     "parameters": {
       "type": "object",
       "properties": {
         "field1": {...},
         "field2": {...}
       },
       "required": ["field1", "field2"]
     }
   }
   ```
5. 调用 `assemble_prompt()` 生成合并后的 Prompt

## 4. 数据流分析

### 4.1 单字段组查询流程
```
请求 → 查询字段组 → 查询关联字段 → 
build_fields_instructions() → build_function_schema() → assemble_prompt() → 
组装返回数据
```

### 4.2 多字段组合并查询流程
```
请求 → 查询多个字段组 → 查询各组关联字段 → 字段去重 → 
build_fields_instructions(所有字段) → 
_build_field_param(逐个字段) → 合并 Function Schema → 
assemble_prompt(使用第一个字段组模板) → 
组装返回数据（包含 combined_schema）
```

## 5. 关键设计决策

### 5.1 为什么使用 label 作为 enum 值？
在 `build_function_schema()` 中，select 类型的 enum 使用的是选项的 `label` 而不是 `value`。

**原因**：
- LLM 更容易理解和匹配人类可读的 label
- 减少 LLM 返回 value（如数字ID）但需要映射到 label 的复杂性

### 5.2 合并 Schema 的模板选择
当合并多个字段组时，使用第一个字段组的 `prompt_template_base` 作为基础模板。

**原因**：
- 多字段组场景通常有主次之分
- 简化实现，避免模板冲突
- 调用方可以通过调整 group_names 顺序控制使用哪个模板

### 5.3 字段去重机制
在合并接口中，使用 `all_field_ids` Set 来确保同一字段不会重复添加。

**场景**：一个字段可能属于多个字段组，合并时需要去重。

## 6. 接口验证结果

### 6.1 /autofill/field_group
| 测试项 | 结果 |
|--------|------|
| 返回 prompt_info | ✅ |
| 返回 function_calling | ✅ |
| 支持 group_names 列表 | ✅ |
| 支持 field_names 筛选 | ✅ |

### 6.2 /autofill/field_groups/schema
| 测试项 | 结果 |
|--------|------|
| 只传 group_names | ✅ |
| group_names + field_names | ✅ |
| 只传 field_names | ✅ |
| 返回 combined_schema | ✅ |
| 合并后的 Prompt 正确 | ✅ |
| 合并后的 Function Schema 正确 | ✅ |

## 7. 使用示例

### 7.1 查询单个字段组
```bash
curl -X POST "http://localhost:9999/api/autofill/field_group" \
  -H "Authorization: Bearer {api_key}" \
  -d '{
    "page_name": "用户信息页",
    "group_names": ["default"]
  }'
```

### 7.2 查询多个字段并合并 Schema
```bash
curl -X POST "http://localhost:9999/api/autofill/field_groups/schema" \
  -H "Authorization: Bearer {api_key}" \
  -d '{
    "page_name": "用户信息页",
    "group_names": ["default"],
    "field_names": ["一级事件类型", "智能网联-二三级"]
  }'
```

### 7.3 返回的 Combined Schema 示例
```json
{
  "combined_schema": {
    "prompt_info": {
      "template_base": "你是一个智能填单助手...",
      "fields_instructions": "- 一级事件类型...\n- 智能网联-二三级...",
      "assembled_prompt": "你是一个智能填单助手...\n\n需要提取的字段：\n- 一级事件类型..."
    },
    "function_calling": {
      "schema": {
        "name": "fill_form",
        "description": "自动填单函数",
        "parameters": {
          "type": "object",
          "properties": {
            "一级事件类型": {
              "type": "string",
              "description": "请选择一级事件类型",
              "enum": ["智能网联", "产品咨询", "4S店", ...]
            },
            "智能网联-二三级": {
              "type": "string",
              "description": "...",
              "enum": ["APP问题 - 无法登录", ...]
            }
          },
          "required": ["一级事件类型", "智能网联-二三级"]
        }
      }
    }
  }
}
```
