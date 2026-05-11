# 智能填单系统 - 脚本使用说明

本文档介绍 `scripts/useful` 目录下各个脚本的功能和使用方法。

## 目录

1. [test_llm_fill_workflow_v2.py](#test_llm_fill_workflow_v2py) - 分步测试LLM填单工作流（增强版）
2. [test_llm_fill_workflow.py](#test_llm_fill_workflowpy) - 分步测试LLM填单工作流（基础版）
3. [create_service_record_structure.py](#create_service_record_structurepy) - 创建服务记录类型字段结构
4. [create_event_fields.py](#create_event_fieldspy) - 创建事件类型字段结构
5. [import_template_fields.py](#import_template_fieldspy) - 导入模板字段
6. [export_templates.py](#export_templatespy) - 导出模板数据

---

## test_llm_fill_workflow_v2.py

### 功能说明

分步测试LLM填单工作流的增强版脚本，支持多种测试场景和自定义对话内容。

**测试流程：**
1. **第一步**：获取一级事件类型和服务记录类型
2. **第二步**：根据服务记录类型获取对应字段组的所有字段 + 根据一级事件类型获取二三级事件类型

### 特性

- 支持自定义测试用例（从文件读取或命令行传入）
- 支持多种对话场景（道路救援、保养预约、质量问题等）
- 详细的执行日志和结果格式化输出
- 支持保存结果到JSON文件
- 打印接口返回的完整原始内容
- 显示替换字段值后的输出模板

### 使用方法

#### 基础用法

```bash
# 使用默认测试用例（道路救援场景）
python test_llm_fill_workflow_v2.py

# 使用保养预约场景
python test_llm_fill_workflow_v2.py --scenario maintenance

# 使用质量问题场景
python test_llm_fill_workflow_v2.py --scenario quality

# 从文件读取对话内容
python test_llm_fill_workflow_v2.py --conversation-file conversation.txt

# 直接传入对话内容
python test_llm_fill_workflow_v2.py --conversation "用户：我的车无法启动..."

# 保存结果到文件
python test_llm_fill_workflow_v2.py --output result.json
```

#### 指定LLM调用方法

```bash
# 使用结构化输出模式（推荐，最稳定）
python test_llm_fill_workflow_v2.py --method with_structured_output

# 使用工具绑定模式（非流式）
python test_llm_fill_workflow_v2.py --method bind_tools_non_stream

# 使用工具绑定模式（流式）
python test_llm_fill_workflow_v2.py --method bind_tools_stream

# 使用Pydantic解析器
python test_llm_fill_workflow_v2.py --method pydantic_parser

# 使用JSON解析器
python test_llm_fill_workflow_v2.py --method json_parser

# 使用纯文本模式（直接返回原始LLM响应）
python test_llm_fill_workflow_v2.py --method plain

# 测试所有可用的方法（对比不同方法的效果）
python test_llm_fill_workflow_v2.py --test-all-methods
```

#### 使用附加数据（预填充字段）

```bash
# 使用附加数据（需要先创建 additional_data.json 文件）
python test_llm_fill_workflow_v2.py \
    --use-additional-data \
    --additional-data additional_data.json

# 附加数据 + 指定场景
python test_llm_fill_workflow_v2.py \
    --scenario rescue \
    --use-additional-data \
    --additional-data additional_data.json
```

创建 `additional_data.json` 文件示例：
```json
{
  "customer_name": "张三",
  "contact_phone": "13800138000",
  "vehicle_system": "比亚迪汉EV",
  "vin_code": "LGXC14EAXN1234567"
}
```

#### 使用自定义系统提示词

```bash
# 使用自定义系统提示词覆盖字段组默认模板
python test_llm_fill_workflow_v2.py \
    --system-prompt "你是一个专业的汽车客服助手，擅长处理道路救援请求。请仔细分析对话内容，提取关键信息。"

# 结合场景和方法使用
python test_llm_fill_workflow_v2.py \
    --scenario maintenance \
    --method with_structured_output \
    --system-prompt "你是一个专业的汽车保养顾问，请从对话中提取保养相关信息。"
```

#### 返回字段填写理由

```bash
# 获取字段填写理由（了解每个字段值的提取依据）
python test_llm_fill_workflow_v2.py --include-reason

# 结合其他参数使用
python test_llm_fill_workflow_v2.py \
    --scenario quality \
    --method with_structured_output \
    --include-reason \
    --output result_with_reason.json
```

#### 组合使用多个参数

```bash
# 完整示例：指定场景 + 方法 + 附加数据 + 系统提示词 + 理由 + 输出文件
python test_llm_fill_workflow_v2.py \
    --scenario rescue \
    --method with_structured_output \
    --use-additional-data \
    --additional-data additional_data.json \
    --system-prompt "你是一个专业的道路救援客服助手。" \
    --include-reason \
    --output complete_result.json

# 简洁示例：指定场景 + 方法 + 输出
python test_llm_fill_workflow_v2.py \
    --scenario maintenance \
    --method with_structured_output \
    --output maintenance_result.json

# 对比测试：同一对话使用不同方法
python test_llm_fill_workflow_v2.py \
    --conversation "用户：我的车发动机故障灯亮了，怎么办？" \
    --test-all-methods
```

#### 自定义API配置

```bash
# 使用自定义API配置
python test_llm_fill_workflow_v2.py \
    --api-key YOUR_API_KEY \
    --base-url http://localhost:9999 \
    --page-name 用户信息页

# 指定特定页面进行测试
python test_llm_fill_workflow_v2.py \
    --page-name "客户信息页" \
    --scenario rescue

# 使用 plain 模式（直接返回原始响应）
python test_llm_fill_workflow_v2.py --method plain

# 测试所有可用的LLM方法
python test_llm_fill_workflow_v2.py --test-all-methods

# 使用附加数据（预填充字段值）
python test_llm_fill_workflow_v2.py \
    --use-additional-data \
    --additional-data additional_data.json

# 使用自定义系统提示词
python test_llm_fill_workflow_v2.py \
    --system-prompt "你是一个专业的客服助手，擅长处理客户咨询..."

# 返回字段填写理由
python test_llm_fill_workflow_v2.py --include-reason

# 组合使用多个参数
python test_llm_fill_workflow_v2.py \
    --scenario rescue \
    --method with_structured_output \
    --include-reason \
    --output result.json
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--api-key` | API密钥 | af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR |
| `--base-url` | API基础URL | http://localhost:9999 |
| `--page-name` | 页面名称 | 用户信息页 |
| `--scenario` | 测试场景 (rescue/maintenance/quality) | rescue |
| `--conversation-file` | 对话内容文件路径 | - |
| `--conversation` | 直接传入对话内容 | - |
| `--method` | LLM调用方法（见下方说明） | - |
| `--test-all-methods` | 测试所有可用的LLM方法 | False |
| `--additional-data` | 附加数据JSON文件路径 | - |
| `--use-additional-data` | 是否使用附加数据 | False |
| `--system-prompt` | 自定义系统提示词 | - |
| `--include-reason` | 返回字段填写理由 | False |
| `--output` | 结果保存路径 | - |

### LLM调用方法说明

`--method` 参数支持以下值：

| 方法名 | 说明 |
|--------|------|
| `with_structured_output` | 使用结构化输出模式（推荐） |
| `bind_tools_non_stream` | 使用工具绑定模式（非流式） |
| `bind_tools_stream` | 使用工具绑定模式（流式） |
| `custom_fc_non_stream` | 自定义函数调用（非流式） |
| `custom_fc_stream` | 自定义函数调用（流式） |
| `pydantic_parser` | 使用Pydantic解析器 |
| `json_parser` | 使用JSON解析器 |
| `plain` | 纯文本模式，直接返回原始响应 |

### 附加数据格式

当使用 `--use-additional-data` 时，JSON文件格式如下：

```json
{
  "customer_name": "张三",
  "contact_phone": "13800138000",
  "vehicle_system": "比亚迪汉EV"
}
```

附加数据中的字段值会在LLM填单时作为预填充值使用。

### 输出说明

脚本会输出以下内容：
1. **步骤1接口返回的完整原始内容** - 完整的API响应JSON
2. **步骤1提取的result数据** - 一级事件类型和服务记录类型
3. **步骤2接口返回的完整原始内容** - 完整的API响应JSON
4. **步骤2提取的result数据** - 详细字段数据
5. **输出模板（已替换字段值）** - 处理后的模板内容
6. **最终填单结果** - 分类整理的字段结果

---

## test_llm_fill_workflow.py

### 功能说明

分步测试LLM填单工作流的基础版脚本，使用固定的道路救援测试用例。

### 使用方法

```bash
# 使用默认配置
python test_llm_fill_workflow.py

# 自定义API配置
python test_llm_fill_workflow.py --api-key YOUR_API_KEY --base-url http://localhost:9999
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--api-key` | API密钥 | af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR |
| `--base-url` | API基础URL | http://localhost:9999 |

---

## create_service_record_structure.py

### 功能说明

创建服务记录类型字段结构和字段组，包括：
1. 创建"服务记录类型"字段（下拉单选），选项为各个模板
2. 为每个模板创建字段组，绑定模板中使用的字段
3. 设置字段组的输出模板

### 数据文件

- **模板CSV**: `test_csv_data/templates_export.csv`
- **字段CSV**: `test_csv_data/template_fields.csv`

### CSV文件格式

**templates_export.csv**:
```csv
name,template_content
道路救援请求,【客户信息】${customer_name}...
保养预约,【客户信息】${customer_name}...
```

**template_fields.csv**:
```csv
field_name,field_label,field_type,fill_instruction
customer_name,客户姓名,text,客户的姓名或称呼
contact_phone,联系电话,text,客户的主要联系电话号码
```

### 使用方法

```bash
# 使用默认配置
python create_service_record_structure.py

# 自定义API配置
python create_service_record_structure.py --api-key YOUR_API_KEY --base-url http://localhost:9999

# 指定CSV文件路径
python create_service_record_structure.py \
    --templates-csv /path/to/templates.csv \
    --fields-csv /path/to/fields.csv
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--api-key` | API密钥 | af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR |
| `--base-url` | API基础URL | http://localhost:9999 |
| `--templates-csv` | 模板CSV文件路径 | test_csv_data/templates_export.csv |
| `--fields-csv` | 字段CSV文件路径 | test_csv_data/template_fields.csv |

---

## create_event_fields.py

### 功能说明

从CSV文件创建事件类型字段结构：
1. 创建一级事件类型字段（下拉单选）
2. 为每个一级事件类型创建对应的二三级事件类型字段（展平为二级选项）

### 数据文件

- **事件类型CSV**: `test_csv_data/event_types.csv`

### CSV文件格式

```csv
一级事件类型,一级事件类型ID,一级事件类型填写说明,二级事件类型,二级事件类型ID,三级事件类型,三级事件类型ID,三级事件类型填写说明
救援,EVT009,用户车辆发生故障...,道路救援,EVT009001,拖车服务,EVT009001001,用户车辆故障无法行驶...
救援,EVT009,用户车辆发生故障...,道路救援,EVT009001,现场抢修,EVT009001002,用户车辆轮胎更换...
```

### 使用方法

```bash
# 使用默认配置
python create_event_fields.py

# 自定义API配置
python create_event_fields.py --api-key YOUR_API_KEY --base-url http://localhost:9999

# 指定CSV文件路径
python create_event_fields.py --csv-path /path/to/event_types.csv
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--api-key` | API密钥 | af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR |
| `--base-url` | API基础URL | http://localhost:9999 |
| `--csv-path` | 事件类型CSV文件路径 | test_csv_data/event_types.csv |

---

## import_template_fields.py

### 功能说明

从CSV文件导入模板字段作为文本类型字段。

### 数据文件

- **字段CSV**: `test_csv_data/template_fields.csv`

### CSV文件格式

```csv
field_name,field_label,field_type,fill_instruction
customer_name,客户姓名,text,客户的姓名或称呼
contact_phone,联系电话,text,客户的主要联系电话号码
vehicle_system,车系,text,车辆的品牌和型号系列
```

### 使用方法

```bash
# 使用默认配置
python import_template_fields.py

# 自定义API配置
python import_template_fields.py --api-key YOUR_API_KEY --base-url http://localhost:9999

# 指定CSV文件路径
python import_template_fields.py --csv-path /path/to/fields.csv
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--api-key` | API密钥 | af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR |
| `--base-url` | API基础URL | http://localhost:9999 |
| `--csv-path` | 字段CSV文件路径 | test_csv_data/template_fields.csv |

---

## export_templates.py

### 功能说明

导出总结模板数据到CSV文件。

### 使用方法

```bash
python export_templates.py
```

运行后会提示输入浏览器中的token值，然后从API获取模板数据并导出到CSV文件。

### 获取Token方法

1. 打开浏览器开发者工具（F12）
2. 切换到 Application/Storage 标签
3. 找到 Local Storage 或 Cookies
4. 复制 token 值

### 输出文件

导出文件路径：`templates_export.csv`

### CSV输出格式

```csv
id,name,app_name,tenant_id,class_name,summary,template_content,created_at,updated_at
```

---

## 通用配置说明

### 默认API配置

所有脚本使用以下默认配置：

```python
DEFAULT_API_BASE_URL = "http://localhost:9999"
DEFAULT_API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"
PAGE_NAME = "用户信息页"
```

### 环境要求

- Python 3.8+
- requests 库
- 智能填单系统API服务已启动

### 安装依赖

```bash
pip install requests
```

---

## 使用流程示例

### 完整初始化流程

```bash
# 1. 导入基础字段
python import_template_fields.py

# 2. 创建事件类型字段结构
python create_event_fields.py

# 3. 创建服务记录类型字段结构
python create_service_record_structure.py

# 4. 测试LLM填单工作流
python test_llm_fill_workflow_v2.py --scenario rescue
```

### 测试不同场景

```bash
# 道路救援场景
python test_llm_fill_workflow_v2.py --scenario rescue

# 保养预约场景
python test_llm_fill_workflow_v2.py --scenario maintenance

# 质量问题场景
python test_llm_fill_workflow_v2.py --scenario quality

# 自定义对话
python test_llm_fill_workflow_v2.py --conversation-file my_conversation.txt
```

---

## 故障排查

### 常见问题

1. **连接被拒绝**
   - 检查API服务是否已启动
   - 检查 `--base-url` 配置是否正确

2. **401 未授权**
   - 检查 `--api-key` 是否正确
   - 确认API密钥是否已过期

3. **404 页面不存在**
   - 检查 `--page-name` 是否正确
   - 确认页面已在系统中创建

4. **CSV文件找不到**
   - 检查CSV文件路径是否正确
   - 确认文件编码为UTF-8

### 调试模式

所有脚本都会打印详细的执行日志，包括：
- 请求参数
- 响应状态码
- 错误信息

可以通过查看日志定位问题。
