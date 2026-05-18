# 脚本工具集

本目录包含用于系统管理、数据导入和项目维护的工具脚本。

## 目录结构

```
scripts/
├── data/                           # 数据文件目录
│   ├── event_types.csv             # 事件类型数据（三级结构）
│   ├── phone_field_options.csv     # 400电话字段选项数据
│   ├── template_fields.csv         # 模板字段定义
│   └── templates_export.csv        # 服务记录模板
├── docs/                           # 文档目录
│   ├── README.md                   # 本文档
│   ├── dropdown.md                 # 下拉字段管理指南
│   └── field_management_guide.md   # 字段管理指南
├── cleanup_and_recreate.py         # 一键清理和重建所有字段
├── create_smart_fields.py          # 智能字段创建脚本（YAML配置）
├── create_service_record_structure.py # 服务记录结构创建脚本
├── create_fields_config.yaml       # 字段创建配置文件
├── get_api_key.py                  # 获取API Key工具
├── import_all_data.py              # 导入所有关键数据
├── reset_passwords.py              # 重置用户密码
├── test_step_llm_fill.py           # 测试LLM填单功能
└── verify_dropdown_import.py       # 验证下拉字段导入
```

## 数据文件说明

### 1. event_types.csv
事件类型数据，包含三级结构：
- 一级事件类型：道路救援、保养预约、质量问题
- 二级事件类型：如拖车服务、现场维修、常规保养等
- 三级事件类型：如标准拖车、紧急拖车、电瓶搭电等

用于创建级联下拉字段（主字段+次字段）。

### 2. phone_field_options.csv
400电话字段选项数据，包含：
- 三级报警、智能网联、投诉、建议、救援、4S店等选项
- 每个选项包含选项值、选项标签和填写说明

### 3. template_fields.csv
模板字段定义，包含100+个字段：
- 字段名、字段标签、填写说明
- 用于服务记录模板的字段创建

### 4. templates_export.csv
服务记录模板数据，包含10个模板：
- 道路救援请求、保养预约、漆面质量问题、异响投诉
- 车辆无法启动、制动系统报警、空调制冷异常
- 车机系统卡顿、动力电池故障、预约充电故障

每个模板包含模板内容和变量。

## 脚本使用说明

### 1. cleanup_and_recreate.py

**功能**：一键清理所有现有字段和字段组，然后重新创建所有数据。

**用法**：
```bash
cd scripts
python cleanup_and_recreate.py
```

**参数**：
- `--api-key`: API Key（默认使用内置key）
- `--base-url`: API基础URL（默认：http://localhost:9999）
- `--page-name`: 页面名称（默认：用户信息页）
- `--skip-cleanup`: 跳过清理步骤，只创建数据

**示例**：
```bash
python scripts/cleanup_and_recreate.py --skip-cleanup
python scripts/cleanup_and_recreate.py --base-url http://localhost:8080
```

**创建的数据**：
1. 事件类型字段组（级联字段）
   - 主字段：一级事件类型（3个选项：道路救援、保养预约、质量问题）
   - 次字段：3个二三级事件类型字段（每个一级分类对应一个次字段）

2. 400电话字段组
   - 字段：test_400_phone（10个选项）

3. 服务记录类型字段组
   - 服务记录类型字段（10个选项）
   - 10个模板字段组（共184个字段）

### 2. create_smart_fields.py

**功能**：基于YAML配置灵活创建主字段和次字段（级联字段）。

**用法**：
```bash
python scripts/create_smart_fields.py [config.yaml]
```

**配置文件示例**：
```yaml
# 测试场景1: level1主字段 + level2-level3次字段
api:
  base_url: "http://localhost:9999"
  api_key: "your_api_key"

page:
  page_name: "用户信息页"
  field_group_name: "scenario1"

csv:
  file_path: "data/event_types.csv"
  field_mapping:
    level1:
      name: "一级事件类型"
      id: "一级事件类型ID"
      instruction: "一级事件类型填写说明"
    level2:
      name: "二级事件类型"
      id: "二级事件类型ID"
      instruction: "二级事件类型填写说明"
    level3:
      name: "三级事件类型"
      id: "三级事件类型ID"
      instruction: "三级事件类型填写说明"

main_field:
  name: "事件类型"
  label: "事件类型"
  combine_levels: "level1"
  separator: "-"
  instruction_fields: "level1"

secondary_field:
  enabled: true
  suffix: "详细分类"
  combine_levels: "level2-level3"
  separator: "-"
  instruction_fields: "level2-level3"

id_generation:
  level1_prefix: "S1"
  digit_length: 3
  use_hierarchical_id: true
```

### 3. create_service_record_structure.py

**功能**：创建服务记录类型字段结构和字段组。

**用法**：
```bash
python scripts/create_service_record_structure.py [options]
```

**参数**：
- `--api-key`: API Key
- `--base-url`: API基础URL
- `--templates-csv`: 模板CSV文件路径
- `--fields-csv`: 字段CSV文件路径
- `--page-name`: 页面名称

**示例**：
```bash
python scripts/create_service_record_structure.py
python scripts/create_service_record_structure.py --page-name "新页面"
```

## 工作流程

### 首次导入数据

1. 确保后端服务已启动
2. 执行清理和重建脚本：
   ```bash
   python scripts/cleanup_and_recreate.py
   ```

### 更新数据

1. 修改相应的CSV数据文件
2. 执行脚本（会自动清理旧数据并创建新数据）：
   ```bash
   python scripts/cleanup_and_recreate.py
   ```

### 只创建不清理

如果只想添加新数据而不清理现有数据：
```bash
python scripts/cleanup_and_recreate.py --skip-cleanup
```

## 注意事项

1. **API地址**：默认使用 `http://localhost:9999`，如果服务运行在其他地址，请使用 `--base-url` 参数指定。

2. **页面名称**：默认使用 "用户信息页"，如果需要导入到其他页面，请使用 `--page-name` 参数指定。

3. **数据备份**：执行清理操作会删除该页面下的所有字段组，请确保已备份重要数据。

4. **CSV编码**：所有CSV文件使用UTF-8编码，包含中文内容。

5. **字段组命名**：
   - 事件类型："事件类型"
   - 400电话字段："400电话字段"
   - 服务记录类型："服务记录类型"
   - 模板字段组："服务记录-{模板名称}"

## 故障排除

### 1. API连接失败
- 检查后端服务是否已启动
- 检查 `--base-url` 参数是否正确

### 2. 权限错误
- 检查 `--api-key` 是否有效
- 确认API Key具有创建字段的权限

### 3. CSV文件读取失败
- 检查CSV文件路径是否正确
- 确认CSV文件使用UTF-8编码
- 检查CSV文件格式是否正确（包含表头）

## 扩展开发

### 添加新的数据类型

1. 准备CSV数据文件，放入 `data/` 目录
2. 创建新的脚本或修改现有脚本
3. 参考 `cleanup_and_recreate.py` 中的实现
4. 更新本文档说明

### 修改字段结构

1. 编辑相应的CSV数据文件
2. 如需修改字段创建逻辑，编辑对应的脚本
3. 测试并验证结果


## 测试命令

### test_step_llm_fill.py - 分步LLM填单测试

**功能**：测试基于session的分步填单流程，支持多种LLM调用方法。

**基本用法**：
```bash
python scripts/test_step_llm_fill.py
```

**可用方法**（--method 参数）：

```bash
# 1. with_structured_output - LangChain 官方结构化输出
python scripts/test_step_llm_fill.py --method with_structured_output

# 2. bind_tools_non_stream - bind_tools + 非流式
python scripts/test_step_llm_fill.py --method bind_tools_non_stream

# 3. bind_tools_stream - bind_tools + 流式
python scripts/test_step_llm_fill.py --method bind_tools_stream

# 4. custom_fc_non_stream - 自定义 Function Calling + 非流式
python scripts/test_step_llm_fill.py --method custom_fc_non_stream

# 5. custom_fc_stream - 自定义 Function Calling + 流式
python scripts/test_step_llm_fill.py --method custom_fc_stream

# 6. pydantic_parser - PydanticOutputParser
python scripts/test_step_llm_fill.py --method pydantic_parser

# 7. json_parser - JsonOutputParser
python scripts/test_step_llm_fill.py --method json_parser

# 8. plain - 纯文本模式（不提取结构化数据）
python scripts/test_step_llm_fill.py --method plain
```

**其他参数**：

```bash
# 指定测试场景（rescue/maintenance/quality/400）
python scripts/test_step_llm_fill.py --scenario rescue

# 指定 session_id
python scripts/test_step_llm_fill.py --session-id my_session_001

# 保存结果到文件
python scripts/test_step_llm_fill.py --output result.json

# 运行所有测试场景
python scripts/test_step_llm_fill.py --test-all

# 指定记忆轮数
python scripts/test_step_llm_fill.py --memory-rounds 5

# 指定API地址
python scripts/test_step_llm_fill.py --base-url http://localhost:9999

# 指定API Key
python scripts/test_step_llm_fill.py --api-key your_api_key

# 指定页面名称
python scripts/test_step_llm_fill.py --page-name "话务工作台"
```

**注意事项**：
- 超时时间已设置为1小时（3600秒），适用于长对话测试
- 默认测试场景为道路救援（rescue）
- 支持多轮对话记忆，可通过 `--memory-rounds` 指定保留轮数
