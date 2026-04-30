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
