设计详细的需求文档，

数据表设计约束：
varchar 设置默认为空字符串
主键等采用bigint类型
字段设计尽量大一点，因为大多数都是中文的总结或者一大段文本

新增走Authorization: Bearer认证的接口(不需要在接口管理里面维护)
以下是dify调用的
/autofill/summary_template/list
/autofill/summary_template
/autofill/dropdown_options/list
/autofill/dropdown_options
/autofill/record_fill_data 用于记录dify 在填单过程中填写的数据
以下是给三方应用调用的接口
/autofill/get_ai_fill_data 

接口全部是post json 格式


设计应用管理功能
- id: 主键，自增
- app_name: 应用名称，英文格式
- tenant_id: 租户ID，用于关联不同的租户
- api_key: api秘钥，用于调用api时验证身份 唯一索引，生成需要符合业内规范
- create_time: 创建时间
- update_time: 更新时间
唯一索引约束：
- (tenant_id, app_name) 唯一索引，用于防止重复创建

设计总结类填单模板功能  
- id: 主键，自增
- name: 填单模板名称
- app_name: 应用名称，英文格式，和应用管理功能中的app_name保持一致
- tenant_id: 租户ID，用于关联不同的租户
- class_name: 模板分类名称 ，用于关联不同的模板分类
- summary: 填单模板摘要
- template_content: 填单模板内容
- create_time: 创建时间
- update_time: 更新时间
唯一索引约束：
- (tenant_id, app_name, class_name, name) 唯一索引，用于防止重复创建
1. 后端需要实现服务内容类填单模板的基础的curd接口
2. 需要提供给dify调用的接口:dify仅传参header中的api_key,然后middleware根据api_key查询出对应的tenant_id,app_name
- 根据tenant_id,app_name和class_name查所有模板的summary和name，返回一个列表: /autofill/summary_template/list
- 根据tenant_id,app_name和class_name/name查询模板内容: /autofill/summary_template name在post body中
页面设计：
过滤条件：
- 应用名称(下拉选择)
- 模板名称
- 以及其他必要的过滤条件



设计下拉选项类填单模板功能  
- id: 主键，自增
- field_name: 下拉选项字段名称
- domain: 应用域名，和应用管理功能中的domain保持一致
- summary: 下拉选项字段摘要
- description: 下拉选项的详细说明
- class_name: 模板分类名称 ，用于关联不同的模板分类
- tenant_id: 租户ID，用于关联不同的租户
- app_name: 应用名称，英文格式，用于关联不同的服务内容
- parent_field_name: 父字段名称，用于递归下拉选项的场景
- create_time: 创建时间
- update_time: 更新时间
- (tenant_id, app_name, field_name) 唯一索引，用于防止重复创建
1. 后端需要实现下拉选项类填单模板的基础的curd接口
2. 需要提供给dify调用的接口:dify仅传参header中的api_key,然后middleware根据api_key查询出对应的tenant_id,app_name,domain
- 根据app_name/domain和class_name/parent_field_name查询查询所有下拉选项的summary和field_name,返回一个列表: /autofill/dropdown_options/list 
parent_field_name在post body中默认为空，即查询第一级的下拉选项
- 根据app_name/domain和class_name/field_name查询下拉选项内容: /autofill/dropdown_options 
页面设计：
过滤条件：
- 应用名称(下拉选择)
- field_name: 下拉选项字段名称
- parent_field_name: 父字段名称
- 以及其他必要的过滤条件

设计填单数据记录功能  
- id: 主键，自增
- session_id: 会话ID
- phone: 手机号
- user_unique_id: 用户唯一标识varchar类型
- user_name: 用户名称
- app_name: 应用名称，英文格式，和应用管理功能中的app_name保持一致
- tenant_id: 租户ID，用于关联不同的租户
- create_time: 创建时间
- data: 填单数据，json格式
- create_time: 创建时间
- update_time: 更新时间
页面设计：
过滤条件：
- 应用名称(下拉选择)
- phone: 手机号
- user_unique_id: 用户标识
- user_name: 用户名称
- session_id: 会话ID
- create_time: 创建时间
- update_time: 更新时间
- 以及其他必要的过滤条件
1. 后端需要实现填单数据记录的基础的curd接口,data需要用json组件展示，用户可以在页面上查看和编辑
2. 需要提供给dify调用的接口:dify仅传参header中的api_key,然后middleware根据api_key查询出对应的tenant_id,app_name
- 根据session_id/tenant_id/app_name设置填单数据: /autofill/record_fill_data 
- 每次传参data都需要将数据库中的data查询出来，然后和传参的data进行合并，最后将合并后的data更新到数据库中，data是一个map结构







调用链路
1. 三方应用请求/autofill/get_ai_fill_data传参是:
json body格式
- session_id: 会话ID
- data: 其他关键数据
- data.chat_message: 用户/客服的聊天消息
- data.phone
header:
- Authorization: Bearer api_key
- api_key: api秘钥，用于调用api时验证身份
然后需要根据api_key查询出对应的tenant_id,app_name,domain

2. 后端header中的api_key并查询出对应的tenant_id,app_name
验证通过则调用/autofill/record_fill_data接口的service层方法，将数据data直接设置到表的data字段,需要注意加上original_data作为key
{
    "original_data": {},
}
然后根据api_key查询出对应的dify url、key等配置项，
然后将请求原封不动转发到dify
3. dify中实现自动化流程的编排：例如：
- 1. 调用三方的车辆信息和用户信息接口然后和用户输入的聊天消息
- 2. 调用/autofill/summary_template/list接口查询所有模板的summary和name
- 3. 根据1/2接口的结果内容进行组装自动填单提示词，让大模型去得到当前符合哪个模板；等等
- dify的编排仅作为提示整个链路，不在本系统中实现具体的业务逻辑

