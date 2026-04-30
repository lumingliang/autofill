话务前端 -> 传递session_id/domain/app_name/通话记录/phone信息  -> 调用ai_agent平台 autofill接口 -> 调用dify平台

# Dify
负责填单流程的编排
1. 查询三方用户信息接口, llm根据聊天记录从用户列表中选出用户信息
2. 获取字段组: xxx,没有则 根据聊天记录提取到经销商和服务店、查询三方列表接口 llm从列表中选出经销商、服务店信息
3. 获取字段组: 一级事件类型, 如果没有, 则 根据反馈途径（队列）查询一级事件类型列表， 写入对应的字段组。llm选出一级事件类型(即填单场景), 
4. 获取字段组: xxx 如果没有， 则据一级事件类型(填单场景)，查询三方二三级列表。  写入对应的字段组。 llm选出二三级
5. 获取字段组: xxx,如果没有事，则据一级事件类型(填单场景), 查询服务记录模板，查询处理类型、业务类型列表,组装提示词, 写入对应的字段组。lm选出最匹配的处理类型、业务类型、服务记录总结

# 三方
提供接口


# ai_agent平台(当前项目的前后端)

## 应用管理app_name（现有
## 填单页面管理 需要新增
page_name 表 需要绑定app_name /app_id curd中的筛选框可以下拉应用列表
curd
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

字段：appname/ page_name /page_id / field_group_name / prompt_template
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



## autofill接口
调用单dify后记录llm填单结果

## 填单优化
llm-填单agent接口（用于后期增强dify无法文档输出结构化数据的能力，前期在dify实现）

## store接口
记录人工填单结果

## 队列服务
异步填单模式，填单结束实时推送结果到调用方  
# 话务前端
请求ai_agent平台autofill接口,获取填单结果,展示给客服
提交人工填单结果到话务后端，话务后端调用ai_agent平台  store 接口 保存人工填单结果

字段组 表 的结构不需要那么复杂，只要有 app_name/ page_name/ field_group_name  / prompt_template 即可， dify中直接编排不同职能字段组的名称 查询出来 prompt_template  ，如果prompt_template  为空说明需要初始化，那么dify编排需要调用哪些三方接口，组装成prompt_template 给到aiagent平台去保存起来。最后llm直接根据prompt_template  一次性得到该字段组的json输出。 

需要给出一份清晰的技术架构文档，包括架构图、各个组件的交互时序图，，图需要美观展示