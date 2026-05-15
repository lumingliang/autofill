# 字段管理功能操作指南

## 一、功能概述

字段管理模块用于创建和管理智能填单系统的字段定义，支持多种字段类型，包括文本输入、下拉单选、下拉多选等。本文档重点介绍如何通过浏览器界面创建父字段和级联子字段，并从 CURL 请求导入选项数据。

## 二、CURL 导入流程设计

### 2.1 两步骤导入流程

系统采用**两步骤 CURL 导入流程**，将 CURL 命令解析与字段映射配置分离，提供更清晰的配置体验：

**步骤一：输入 CURL 命令**
- 点击"从 curl 导入"按钮
- 在对话框中输入 CURL 命令
- 点击"确定"解析 CURL 命令

**步骤二：配置字段映射**
- 系统自动弹出"配置字段映射"对话框
- 根据 API 响应数据结构配置 JSONPath
- 可选：启用展平功能并配置展平参数
- 点击"确定"生成 OpenAPI Schema

### 2.2 设计优势

| 设计特点 | 说明 |
|----------|------|
| 分离关注点 | CURL 解析与字段映射配置分离，降低复杂度 |
| 灵活配置 | 可根据实际 API 响应结构调整 JSONPath |
| 实时反馈 | 配置完成后可立即同步验证 |
| 展平支持 | 支持多级嵌套数据的展平配置 |

### 2.3 JSONPath 配置说明

JSONPath 用于从 API 响应中提取选项数据，常见配置：

| API 响应字段 | JSONPath 配置 | 说明 |
|--------------|---------------|------|
| `$.data[*].label` / `$.data[*].value` | `$.data[*].label` / `$.data[*].value` | 标准格式 |
| `$.data[*].summary` / `$.data[*].option_value` | `$.data[*].summary` / `$.data[*].option_value` | 本系统 API 格式 |
| `$.result[*].name` / `$.result[*].id` | `$.result[*].name` / `$.result[*].id` | 自定义格式 |

**重要提示：** 配置 JSONPath 时必须与实际 API 响应字段名匹配，否则同步时会获取不到数据。

## 三、API 接口说明

### 3.1 获取一级菜单列表

**接口信息**
- **URL**: `/api/autofill/dropdown/first_level`
- **方法**: `POST`
- **认证**: Bearer Token

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| app_name | string | 是 | 应用名称，如 `test_app` |
| class_name | string | 否 | 分类名称，如 `事件类型` |

**Curl 示例**

```bash
curl -X POST 'http://localhost:9999/api/autofill/dropdown/first_level' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR' \
  -d '{
    "app_name": "test_app",
    "class_name": "事件类型"
  }'
```

**响应示例**

```json
{
  "code": 200,
  "msg": "OK",
  "data": [
    {
      "id": 1,
      "option_value": "EVT001",
      "summary": "道路救援",
      "class_name": "事件类型"
    },
    {
      "id": 2,
      "option_value": "EVT002",
      "summary": "保养预约",
      "class_name": "事件类型"
    },
    {
      "id": 3,
      "option_value": "EVT003",
      "summary": "质量问题",
      "class_name": "事件类型"
    }
  ]
}
```

### 3.2 获取二三级菜单树形结构

**接口信息**
- **URL**: `/api/autofill/dropdown/submenus_tree`
- **方法**: `POST`
- **认证**: Bearer Token

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| app_name | string | 是 | 应用名称，如 `test_app` |
| class_name | string | 否 | 分类名称，如 `事件类型` |
| first_level_value | string | 是 | 一级菜单选项值（编码），如 `EVT001` |

**Curl 示例**

```bash
curl -X POST 'http://localhost:9999/api/autofill/dropdown/submenus_tree' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR' \
  -d '{
    "app_name": "test_app",
    "class_name": "事件类型",
    "first_level_value": "EVT001"
  }'
```

**响应示例**

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "first_level": {
      "id": 1,
      "option_value": "EVT001",
      "summary": "道路救援",
      "class_name": "事件类型"
    },
    "children": [
      {
        "id": 10,
        "option_value": "EVT001-01",
        "summary": "现场救援",
        "children": [
          {
            "id": 100,
            "option_value": "EVT001-01-01",
            "summary": "电池亏电"
          }
        ]
      }
    ]
  }
}
```

## 四、创建父字段（一级下拉字段）

### 4.1 操作步骤

1. **进入字段管理页面**
   - 访问地址：`http://localhost:3200/autofill/field_spec`
   - 确保已登录并有相应权限

2. **点击"新建字段"按钮**
   - 在页面右上角找到"新建字段"按钮并点击

3. **填写字段基本信息**

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| 所属租户 | 选择字段所属的租户 | 测试租户A |
| 关联字段组 | 选择字段所属的字段组 | 服务记录-道路救援请求 |
| 字段名 | 字段的唯一标识 | `event_type_test` |
| 字段标签 | 字段的显示名称 | `事件类型测试` |
| 字段类型 | 选择字段类型 | 下拉单选 |

4. **配置 OpenAPI Schema（从 CURL 导入）**

   点击"从 curl 导入"按钮，输入以下 CURL 命令：

```bash
curl -X POST 'http://localhost:9999/api/autofill/dropdown/first_level' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR' \
  -d '{
    "app_name": "test_app",
    "class_name": "事件类型"
  }'
```

   点击"确定"后，系统会解析 CURL 命令并弹出"配置字段映射"对话框。

5. **配置字段映射**

   在"配置字段映射"对话框中，根据 API 响应数据结构配置 JSONPath：

| 配置项 | 默认值 | 实际配置值 | 说明 |
|--------|--------|------------|------|
| 标签字段 JSONPath | `$.data[*].label` | `$.data[*].summary` | API 返回的标签字段名 |
| 值字段 JSONPath | `$.data[*].value` | `$.data[*].option_value` | API 返回的值字段名 |
| 启用展平 | 关闭 | 根据需要 | 多级数据需要展平时启用 |

   **注意：** 必须根据实际 API 响应字段名配置 JSONPath，否则同步时会获取不到数据。

   点击"确定"后，系统会自动生成 OpenAPI Schema，包含以下关键配置：

```yaml
openapi: 3.0.3
info:
  title: Generated API
  version: 1.0.0
servers:
- url: http://localhost:9999
paths:
  /api/autofill/dropdown/first_level:
    post:
      summary: Generated from curl
      x-api-params:
        headers:
          Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR
        app_name: test_app
        class_name: 事件类型
      x-field-mapping:
        label_path: $.data[*].summary
        value_path: $.data[*].option_value
```

   **关键配置说明：**

| 配置项 | 说明 |
|--------|------|
| `x-api-params` | API 请求参数，包括 headers 和 body 参数 |
| `x-field-mapping.label_path` | 从响应中提取选项标签的 JSONPath |
| `x-field-mapping.value_path` | 从响应中提取选项值的 JSONPath |

6. **同步选项**

   点击"同步选项"按钮，系统会根据配置的 Schema 调用 API 获取数据，并自动填充到选项列表中。

   同步成功后，选项列表会显示：
```markdown
## 道路救援
- 选项值: EVT001

## 保养预约
- 选项值: EVT002

## 质量问题
- 选项值: EVT003
```

7. **保存字段**

   点击"确定"按钮保存字段配置。

### 4.2 验证父字段选项同步

创建成功后，可以通过以下方式验证选项是否同步：

1. **在字段编辑页面查看选项列表**
   - 重新打开字段编辑对话框
   - 查看"选项列表"区域是否显示从 API 获取的选项

2. **通过 API 查询字段详情**
   - 调用字段详情接口验证 options 字段

3. **在填单页面测试**
   - 进入测试填单页面
   - 选择该字段，查看下拉选项是否正确显示

## 五、创建级联子字段

### 5.1 操作步骤

1. **编辑父字段**
   - 在字段列表中找到已创建的父字段
   - 点击"编辑"按钮

2. **添加级联子字段**

   点击"添加级联子字段"按钮，配置级联参数：

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| 字段名生成规则 | 子字段名的生成模式 | `parent.$.data[*].label + -二级类型` |
| 字段标签后缀 | 添加到父选项标签的后缀 | `-二级类型` |
| 启用展平 | 是否展平多级数据 | 根据需要选择 |

3. **配置级联 API Schema（从 CURL 导入）**

   点击"从 curl 导入"按钮，输入以下 CURL 命令：

```bash
curl -X POST 'http://localhost:9999/api/autofill/dropdown/submenus_tree' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR' \
  -d '{
    "app_name": "test_app",
    "class_name": "事件类型",
    "first_level_value": "{parent_value}"
  }'
```

   **注意：** `{parent_value}` 是占位符，表示父字段的选中值。

   生成的 Schema 示例：

```yaml
openapi: 3.0.3
info:
  title: Generated API
  version: 1.0.0
servers:
- url: http://localhost:9999
paths:
  /api/autofill/dropdown/submenus_tree:
    post:
      summary: Generated from curl
      x-api-params:
        headers:
          Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR
        app_name: test_app
        class_name: 事件类型
        first_level_value: '{parent_value}'
      x-field-mapping:
        label_path: $.data.children[*].summary
        value_path: $.data.children[*].option_value
```

4. **配置展平参数（可选）**

   如果数据结构是多级嵌套的，需要配置展平参数：

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| label_path_level1 | 第一级标签路径 | `$.data.children[*].summary` |
| label_path_level2 | 第二级标签路径 | `$.children[*].summary` |
| label_path_level3 | 第三级标签路径 | `$.children[*].summary` |
| label_separator | 标签拼接符 | `-` |
| value_path_level1 | 第一级值路径 | `$.data.children[*].option_value` |
| value_path_level2 | 第二级值路径 | `$.children[*].option_value` |
| value_path_level3 | 第三级值路径 | `$.children[*].option_value` |
| value_separator | 值拼接符 | `-` |

5. **同步级联字段**

   点击"同步级联字段"按钮，系统会：
   - 遍历父字段的所有选项
   - 对每个选项调用级联 API 获取子选项
   - 自动创建对应的子字段

6. **保存配置**

   点击"确定"按钮保存级联配置。

### 5.2 级联字段命名规则

子字段的命名遵循以下规则：

- **字段名模式**: `parent.$.data[*].label + -二级类型`
- **实际生成的字段名**: `道路救援-二级类型`、`保养预约-二级类型` 等
- **字段标签**: 父选项标签 + 后缀，如 `道路救援-二级类型`

### 5.3 验证级联字段

1. **查看生成的子字段**
   - 在字段列表中搜索以父字段名开头的字段
   - 确认每个父选项都对应一个子字段

2. **验证子字段选项**
   - 编辑子字段，查看选项列表是否正确
   - 确认选项与 API 返回的数据一致

3. **测试级联功能**
   - 进入测试填单页面
   - 选择父字段的某个选项
   - 验证对应的子字段是否显示正确的级联选项

## 六、展平功能说明

### 6.1 什么是展平

展平功能用于将多级嵌套的数据结构转换为扁平化的选项列表。例如：

**原始嵌套数据：**
```json
{
  "children": [
    {
      "summary": "现场救援",
      "option_value": "EVT001-01",
      "children": [
        {"summary": "电池亏电", "option_value": "EVT001-01-01"}
      ]
    }
  ]
}
```

**展平后：**
```
- 现场救援-电池亏电 (EVT001-01-EVT001-01-01)
```

### 6.2 展平配置参数

| 参数 | 说明 |
|------|------|
| label_path_level1/2/3 | 各级数据的 JSONPath |
| label_separator | 各级标签之间的连接符 |
| value_path_level1/2/3 | 各级值的 JSONPath |
| value_separator | 各级值之间的连接符 |

### 6.3 展平示例

假设 API 返回以下数据：
```json
{
  "data": {
    "first_level": {"summary": "道路救援"},
    "children": [
      {
        "summary": "现场救援",
        "option_value": "EVT001-01",
        "children": [
          {"summary": "电池亏电", "option_value": "EVT001-01-01"}
        ]
      }
    ]
  }
}
```

配置展平参数：
```yaml
label_path_level1: "$.data.children[*].summary"
label_path_level2: "$.children[*].summary"
label_separator: "-"
value_path_level1: "$.data.children[*].option_value"
value_path_level2: "$.children[*].option_value"
value_separator: "-"
```

展平结果：
```
label: "现场救援-电池亏电"
value: "EVT001-01-EVT001-01-01"
```

## 七、常见问题

### 7.1 同步选项失败

**可能原因：**
- API 地址或认证信息错误
- JSONPath 配置不正确
- API 返回数据格式不符合预期

**解决方法：**
- 检查 OpenAPI Schema 中的 servers URL
- 验证 Authorization Header 是否正确
- 使用 JSONPath 测试工具验证路径表达式

### 7.2 级联字段未生成

**可能原因：**
- 父字段没有选项
- 级联 API 调用失败
- 字段名生成规则有误

**解决方法：**
- 确认父字段已同步选项
- 检查级联 API 的 Schema 配置
- 验证字段名生成规则语法

### 7.3 展平结果不正确

**可能原因：**
- JSONPath 路径配置错误
- 数据层级与配置不匹配

**解决方法：**
- 使用 JSONPath 测试工具验证各级路径
- 检查实际返回的数据结构
- 调整 level1/level2/level3 的路径配置

## 八、最佳实践

1. **命名规范**
   - 字段名使用小写字母和下划线
   - 字段标签使用中文，清晰表达含义
   - 级联子字段使用后缀区分层级

2. **API 配置**
   - 使用固定的 API Key 进行认证
   - 在 Schema 中明确标注 x-api-params 和 x-field-mapping
   - 测试 API 响应格式后再配置字段

3. **数据同步**
   - 定期同步选项数据以保持最新
   - 同步前备份现有选项配置
   - 验证同步结果后再保存

4. **级联配置**
   - 先创建并验证父字段
   - 再配置级联子字段
   - 逐级测试级联功能
