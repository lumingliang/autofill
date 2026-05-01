话务前端 -> 传递session_id/domain/app_name/通话记录/phone信息  -> 调用ai_agent平台 autofill接口 -> 调用dify平台

# Dify（不在当前项目中）
负责填单流程的编排
1. 查询三方用户信息接口, llm根据聊天记录从用户列表中选出用户信息
2. 获取字段组: xxx,没有则 根据聊天记录提取到经销商和服务店、查询三方列表接口 llm从列表中选出经销商、服务店信息
3. 获取字段组: 一级事件类型, 如果没有, 则 根据反馈途径（队列）查询一级事件类型列表， 写入对应的字段组。llm选出一级事件类型(即填单场景), 
4. 获取字段组: xxx 如果没有， 则据一级事件类型(填单场景)，查询三方二三级列表。  写入对应的字段组。 llm选出二三级
5. 获取字段组: xxx,如果没有事，则据一级事件类型(填单场景), 查询服务记录模板，查询处理类型、业务类型列表,组装提示词, 写入对应的字段组。lm选出最匹配的处理类型、业务类型、服务记录总结

# 三方 （不在当前项目中）
提供接口


# ai平台(当前项目的前后端)

## 应用管理app_name（现有）

## 填单页面管理 
page_name 表 需要绑定app_name /app_id 
curd
筛选框可以下拉应用列表

说明书 按钮：点击后，查询当前应用下的所有字段组/并且得到对应的字段明细，然后生成md格式的说明书，类似

```markdown

    # 话务工作台填单说明书

    ## 一、业务信息组

    > 组描述：{group_description}

    ### 1. 业务类型 (business_type)
    - 类型：下拉选择
    - 选项：...
    - 基础规则：...
    - 📌 人工批注：{human_annotations}

    ### 2. 客户姓名 (customer_name)
    ...
```


## 管理字段组配置
field_group_config (字段组配置表)

字段：
code 全局唯一标识(自动生成)
appname/ page_name /page_id / field_group_name / prompt_template
列如：APPname = 400客服 pagename = 话务工作台 字段组名称 = 一级事件类型 
prompt_template 示例
"你是一个填单助手。根据以下对话，按照字段指令填写：\n\n{{fields_instructions}}\n\n对话：{{conversation}}"

curd 
能够根据应用下拉+页面下拉查询到对应的字段组配置

## 字段明细 字段明细表 field_spec（核心）

字段名	类型	说明	示例
字段明细表 field_spec（核心）
field_group_id	bigint	关联字段组	1
field_name	varchar(64)	字段英文名（用于JSON输出）	"business_type"
field_label	varchar(128)	字段显示名称	"业务类型"
field_type	enum	select, text
base_description	text	基础描述（字段含义、取值规则）	"业务类型：新车销售、售后服务、投诉建议..."
human_annotations	text（MD格式）	人工批注累积（Markdown可读）	"⚠️ 注意：当用户提到'保养'时，就算没明确说'售后服务'，也应选'售后服务'。投诉类请优先选'投诉建议'。"

每个字段明细更新后，自动更新字段组里面的prompt_template信息，合理组装prompt 

# 对外接口

1. 根据app_name/page_name/字段组 或者 code 查询字段组配置的prompt_template等明细信息

1个app_name下有多个page_name，每个page_name下有多个field_group_name。
一个field_group_name下有多个field_spec
每个field_spec代表一个单独的填单字段
field_spec包括text和下拉选项两种类型
例如在400客服中需要设计一个服务记录字段组，包含业务类型、和服务记录两个字段。而服务记录包括:姓名、联系电话、vin码、拖车目的地等字段，服务记录设计出来多个字段是为了最后用服务记录模板进行填充为真正的服务记录文本:
模板内容大概是

车主${customer_name}（本人/家人/朋友/同事）X先生/女士${contact_phone}请求道路救援。车系：${vehicle_system}，车架号：${vin_code}。车辆故障现象：无法启动/事故/爆胎/缺油/搭电/其他。车辆当前位置：XX（详细地址）。是否安全停放：是/否，是否影响交通：是/否。车上人数：XX人。客户联系电话：${contact_phone}（备用电话：XX）。期望救援时间：立即/XX时间。拖车目的地：4S店/指定地址。已告知客户预计到达时间并安排救援。

这样先把聊天记录和fc调用的参数，都给到llm，就能返回一个json结构的提取的多个字段对吧

这里面字段spec如何设计？比如是填空题，例如姓名字段：会有一个填写的要求,根据聊天记录提取到的姓名，填写到姓名字段中。
选择题: 例如业务类型字段: 包括三个选项
售前投诉 1  当用户提到'投诉'时，就选'售后投诉'。  人工标注：当用户情绪非常不友好时，也应选'售后投诉'。
售后服务 2  当用户提到'保养'时，就选'售后服务'。 
售后建议 3  当然说明也可以为空，这样就只有选项约束
其中1、2、3是下拉选项的值。这些信息最终需要给fc调用，让大模型输出绝对json格式的字段值。并且保证是在选项里面的

最终希望给到调用方的json格式数据，类似：
{
  "business_type": "售后投诉",
  "service_record": {
    "customer_name": "张三",
    "contact_phone": "13800000000",
    "vin_code": "123456789012345678",
    "notice_time": "已告知客户预计到达时间并安排救援",
  }
}




因为这个其实就是类似企业的一本针对某个页面的填单说明书对吧？不会经常更新、而且即使是并发，也可以全局锁。保证一致性。给人类展示时，直接转成md格式非常容易阅读；同时如果外部想修改；基于pageindex也是比较容易操作json的说明书



针对您提出的三个核心问题，我给出一个**简洁、稳定、可落地**的最终设计方案。

---

## 一、output_template 多模板存储

一个字段组可能需要生成多个输出（例如：服务记录文本、工单标题、通知内容等）。解决方案：

### 在 `field_group` 表中增加 `output_templates` 字段（JSONB）

```sql
ALTER TABLE field_group ADD COLUMN output_templates JSONB NOT NULL DEFAULT '{}';
```

**存储结构示例**：
```json
{
  "service_record_text": {
    "template": "车主{{ customer_name }}（{{ relation }}）{{ contact_phone }}请求道路救援。车架号：{{ vin_code }}。拖车目的地：{{ tow_destination }}。{{ notice_content }}",
    "description": "用于生成最终的服务记录文本"
  },
  "ticket_title": {
    "template": "{{ business_type }} - {{ customer_name }} - {{ contact_phone }}",
    "description": "工单标题"
  },
  "email_subject": {
    "template": "【道路救援】{{ customer_name }}的救援请求",
    "description": "邮件主题"
  }
}
```

- **调用方式**：前端请求时可通过参数 `?template_key=service_record_text` 指定需要的模板，服务端渲染后只返回该模板结果；或者默认返回所有模板的渲染结果。
- **模板引擎**：使用简单占位符 `{{ field_name }}`，后端用 Python `string.Template` 或 `Jinja2` 渲染。字段名与扁平化的 `field_spec.field_name` 一致。

**优点**：一个字段组支持任意多个输出，互不干扰，扩展方便。

---

## 二、field_spec 的初始设置与同步（三方下拉选项）

核心需求：从三方接口加载下拉选项，存入 `field_spec.options`，并支持后续接口变更同步及人工标注追加。

### 2.1 `options` 字段结构（JSONB）

```json
{
  "source": "api",                    // "api" 或 "static"
  "api_identifier": "business_types", // 三方接口标识，用于后台同步
  "last_sync_at": "2025-05-01T10:00:00Z",
  "items": [
    {
      "value": 1,
      "label": "售后投诉",
      "base_annotation": "用户提到'投诉'或情绪激动时选此项",
      "corrections": [
        {
          "id": "c1",
          "text": "当用户反复要求转人工且语气愤怒，也应选此项",
          "created_by": "客服张三",
          "created_at": "2025-05-01T11:00:00Z"
        }
      ],
      "is_deleted": false
    },
    {
      "value": 2,
      "label": "售后服务",
      "base_annotation": "用户提到'保养'、'维修'时选此项",
      "corrections": [],
      "is_deleted": false
    }
  ]
}
```

### 2.2 初始化流程（创建字段时）

1. 运营在后台添加一个 `select` 类型字段，选择“选项来源”为“三方接口”，并指定接口标识（如 `business_types`）。
2. 后端根据接口标识调用三方 API 获取选项列表（假设返回 `[{value:1, name:"售后投诉"}, ...]`）。
3. 将返回的每个选项转换为 `{value, label, base_annotation:"", corrections:[], is_deleted:false}` 存入 `options.items`。
4. 设置 `source="api"`, `api_identifier`, `last_sync_at`。
5. 保存到 `field_spec`。

### 2.3 同步更新机制（定期或手动）

编写一个后台任务（例如每天凌晨执行或通过管理界面手动触发）：

- 查询所有 `field_type='select'` 且 `options->>'source' = 'api'` 的字段。
- 对每个字段，根据 `options->>'api_identifier'` 调用对应的三方接口，获取最新列表。
- 对于接口返回的每个新选项：
  - 如果本地 `items` 中存在相同 `value` 的项：
    - 更新其 `label`（如果接口改了名称），保留原有的 `base_annotation` 和 `corrections`，设置 `is_deleted = false`。
  - 如果不存在：
    - 新增项，`base_annotation` 为空，`corrections` 为空，`is_deleted = false`。
- 对于本地 `items` 中存在但接口返回中不存在的项：
  - 设置其 `is_deleted = true`（不物理删除，保留历史标注）。
- 更新 `last_sync_at`。

**SQL 更新示例（使用 jsonb_set）**：略复杂，建议在应用层读取、修改、写回，字段数量不大，性能可接受。

### 2.4 人工标注

- 运营可以在管理界面直接修改某个选项的 `base_annotation`。
- 也可以追加 `corrections`（通过弹窗提交）。
- 这些修改不会被同步任务覆盖（因为同步只更新 `label` 和新增/软删除，不会动 `base_annotation` 和 `corrections`）。

---

## 三、生成 LLM Function Calling 的参数

运行时，根据 `field_spec` 动态生成 `enum` 和 `description`。

**伪代码**：

```python
def build_field_description(field):
    if field.field_type == 'text':
        desc = field.fill_instruction or ""
        # 追加全局 corrections（如果有）
        if field.corrections:
            corrections_text = "；".join([c['text'] for c in field.corrections])
            desc += f"；人工补充规则：{corrections_text}"
        return desc
    elif field.field_type == 'select':
        options = field.options['items']
        # 只取 is_deleted != true 的选项
        valid_options = [opt for opt in options if not opt.get('is_deleted', False)]
        option_descs = []
        enum_values = []
        for opt in valid_options:
            label = opt['label']
            enum_values.append(label)
            base = opt.get('base_annotation', '')
            corrections_list = opt.get('corrections', [])
            corrections_text = "；".join([c['text'] for c in corrections_list])
            full = f"{label}：{base}"
            if corrections_text:
                full += f"；人工补充：{corrections_text}"
            option_descs.append(full)
        description = f"可选值：{'；'.join(option_descs)}"
        if field.fill_instruction:
            description = field.fill_instruction + " " + description
        return description, enum_values
```

生成的 Function 示例：

```json
{
  "name": "fill_service_record_group",
  "parameters": {
    "type": "object",
    "properties": {
      "business_type": {
        "type": "string",
        "description": "业务类型。可选值：售后投诉：用户提到'投诉'或情绪激动时选此项；人工补充：当用户反复要求转人工且语气愤怒，也应选此项；售后服务：用户提到'保养'、'维修'时选此项。",
        "enum": ["售后投诉", "售后服务"]
      }
    }
  }
}
```

---

## 四、表结构最终版 SQL

```sql
-- 字段组表
CREATE TABLE field_group (
    id SERIAL PRIMARY KEY,
    app_name VARCHAR(64) NOT NULL,
    page_name VARCHAR(64) NOT NULL,
    group_name VARCHAR(128) NOT NULL,
    prompt_template_base TEXT NOT NULL,  -- 包含 {{fields_instructions}} 和 {{conversation}}
    output_templates JSONB NOT NULL DEFAULT '{}',  -- 多模板存储
    is_active BOOLEAN DEFAULT TRUE,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(app_name, page_name, group_name)
);

-- 字段规格表
CREATE TABLE field_spec (
    id SERIAL PRIMARY KEY,
    group_id INT NOT NULL REFERENCES field_group(id) ON DELETE CASCADE,
    field_name VARCHAR(64) NOT NULL,
    field_label VARCHAR(128) NOT NULL,
    field_type VARCHAR(16) NOT NULL CHECK (field_type IN ('text', 'select')),
    is_required BOOLEAN DEFAULT FALSE,
    fill_instruction TEXT,
    options JSONB,                     -- select类型的选项配置（含标注、同步信息）
    corrections JSONB DEFAULT '[]'::JSONB,  -- text类型的全局批注
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(group_id, field_name)
);

-- 索引
CREATE INDEX idx_field_spec_group ON field_spec(group_id);
```

---

## 五、API 和调用流程

1. **前端请求填单**：
   ```
   POST /autofill
   {
     "app_name": "400客服",
     "page_name": "话务工作台",
     "group_name": "service_record_group",
     "conversation": "用户：我要投诉...",
     "template_keys": ["service_record_text"]  // 可选，指定需要的模板
   }
   ```

2. **后端处理**：
   - 查询字段组及字段列表。
   - 动态生成 Function Schema。
   - 调用 LLM，获得扁平 JSON 结果。
   - 根据 `template_keys` 渲染模板：遍历 `field_group.output_templates`，对该请求指定的 key 进行渲染（使用 LLM 返回的字段值）。
   - 返回：
     ```json
     {
       "fields": { "business_type": "售后投诉", "customer_name": "张三", ... },
       "rendered_templates": {
         "service_record_text": "车主张三...请求道路救援..."
       }
     }
     ```

3. **前端展示**：直接使用 `fields` 填充表单各控件，同时展示 `rendered_templates` 中的文本供客服确认。

---

## 六、维护与人工标注界面

- **字段管理界面**：列表展示所有字段，支持编辑 `fill_instruction`、`options.items` 中的 `base_annotation`，以及查看/追加 `corrections`。
- **同步操作**：提供一个“从接口同步”按钮，手动触发指定字段的同步任务。
- **批注弹窗**：客服在前端点击字段反馈时，直接调用后端接口追加 `corrections`（针对 text 字段）或某个选项的 `corrections`。

---

## 总结

这个方案实现了：
1. **多模板存储**：`output_templates` JSONB 字段，灵活支持任意数量输出。
2. **三方下拉选项管理**：`options` 结构存储接口源及合并数据，支持后台同步，人工标注永不丢失。
3. **运行时动态生成**：每次请求实时生成 Function Schema，人工反馈立即生效。
4. **简洁稳定**：只有两张核心表，无复杂自关联，所有扩展信息都放在 JSONB 中，既有关系型约束的严谨，又有 NoSQL 的灵活。

您可以基于这个设计直接开发，如果需要 Python 实现代码（同步任务、Function 生成器、模板渲染），我可以继续提供。