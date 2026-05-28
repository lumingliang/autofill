# Scripts 目录结构说明

本目录包含项目的各种脚本工具，按功能分类组织。

## 目录结构

```
scripts/
├── rule_management/          # 规则管理相关脚本
│   ├── api_tests/           # API接口测试脚本
│   │   └── test_rule_management_api.py    # 规则管理全量API测试
│   ├── curl_import/         # CURL导入相关
│   │   ├── curl_import_unified.py         # 统一CURL导入引擎CLI
│   │   ├── test_curl_import_service.py    # CURL导入服务测试
│   │   ├── test_cascade_curl_dynamic.py   # 级联CURL动态测试
│   │   └── configs/         # CURL导入配置文件
│   │       ├── test_curl_import_full.json
│   │       ├── test_curl_import.json
│   │       └── test_curl_save.json
│   ├── csv_import/          # CSV导入相关
│   │   └── test_csv_import_core.py        # CSV导入核心功能测试
│   ├── rule_engine/         # 规则引擎相关
│   │   └── test_rule_engine.py            # 规则引擎完整测试
│   └── utils/               # 工具脚本
│       ├── create_test_rule.py            # 创建测试规则
│       └── create_fields_v2.py            # 创建字段V2
│
├── database/                # 数据库相关脚本
│   ├── db_schema_manager.py               # 数据库Schema管理
│   ├── migrate_to_seekdb.py               # 迁移到SeekDB
│   └── aerich_fake_init.py                # Aerich假初始化
│
├── llm/                     # LLM相关测试
│   ├── test_step_llm_fill.py              # 步骤LLM填充测试
│   └── test_step_llm_fill_simple.py       # 简化版LLM填充测试
│
├── feedback/                # 反馈相关
│   └── test_summary_feedback.py           # 摘要反馈测试
│
├── dropdown/                # 下拉选项相关
│   ├── test_dropdown_api.py               # 下拉选项API测试
│   └── generate_dropdown_csv.py           # 生成下拉选项CSV
│
├── api/                     # API相关脚本
│   ├── migrate_api_code.py                # 迁移API代码
│   ├── regenerate_api_codes.py            # 重新生成API代码
│   └── test_api_permission.py             # API权限测试
│
├── init/                    # 初始化脚本
│   ├── init_system_prompts.py             # 初始化系统提示词
│   └── reset_passwords.py                 # 重置密码
│
├── misc/                    # 其他脚本
│   └── get_api_key.py                     # 获取API Key
│
├── data/                    # 数据文件
└── test_data/               # 测试数据
```

## 使用说明

### 运行规则管理API测试
```bash
python scripts/rule_management/api_tests/test_rule_management_api.py
```

### 运行CURL导入
```bash
python scripts/rule_management/curl_import/curl_import_unified.py
```

### 运行CSV导入测试
```bash
python scripts/rule_management/csv_import/test_csv_import_core.py
```

## 注意事项

1. 所有脚本都使用绝对路径引用项目根目录，确保可以从任意位置运行
2. 配置文件统一放在 `configs/` 子目录下
3. 测试数据统一放在 `test_data/` 目录下
