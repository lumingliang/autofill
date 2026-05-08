http://localhost:3200/autofill/field_spec 这个页面中下拉单选和下拉多选是有输入 API 接口的选项的，现在里面关于api接口的配置和功能不对，
那么需要 把选项来源字段去掉。 api接口 功能去掉(包括所有和他相关的内容全部删除

。是一直可以填的（之前是需要选择api接口才能填）。选项列表也是一直可以填的。


http://localhost:3200/autofill/field_spec 这个页面
新建和编辑

增加一个header字段：可以配置header的键和值(可以配置多个)
增加字段 schema 输入框
可以配置

openapi: 3.0.3
info:
  title: 下拉选择列表接口文档
  description: 通用下拉列表接口 - 事件类型示例（带固定鉴权Header）
  version: 1.0.0
servers:
  - url: http://localhost:8080/api
    description: 本地开发环境

paths:
  /common/dict/event-type:
    get:
      summary: 获取事件类型下拉列表
      description: 返回用于前端下拉选择框的事件类型枚举列表，必须携带固定鉴权Header
      tags:
        - 公共字典接口
      operationId: getEventTypeList
      responses:
        '200':
          description: 获取成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DropDownListResponse'
              examples:
                success:
                  summary: 成功响应示例
                  value:
                    code: 200
                    message: "操作成功"
                    data:
                      - label: "会议事件"
                        value: "MEETING"
                      - label: "培训事件"
                        value: "TRAINING"
                      - label: "团建事件"
                        value: "TEAM_BUILDING"
                      - label: "其他事件"
                        value: "OTHER"

components:
  schemas:
    # 下拉列表统一响应实体
    DropDownListResponse:
      type: object
      description: 下拉列表通用返回结果
      required:
        - code
        - message
        - data
      properties:
        code:
          type: integer
          description: 响应状态码，200=成功
          example: 200
        message:
          type: string
          description: 响应描述信息
          example: "操作成功"
        data:
          type: array
          description: 下拉列表数据集合
          items:
            $ref: '#/components/schemas/DropDownItem'

    # 下拉列表单项实体（标准前端下拉格式）
    DropDownItem:
      type: object
      description: 下拉选择项
      required:
        - label
        - value
      properties:
        label:
          type: string
          description: 下拉显示文本（前端展示名称）
          example: "会议事件"
        value:
          type: string
          description: 下拉选项值（后端存储/传递值）
          example: "MEETING" 

这种openai swagger格式，然后，里面使用组件prance 解析出来，后端就知道如何去拿到这个配置的下拉接口的数据，以及拿到数据如何解析出来 下拉选项的列表数据，包括 每一个的label 和value。都能拿到，然后需要有一个同步按钮，然后点击同步就会请求这个接口拿到数据(需要携带配置的header).然后解析后得到一个数组,这个数组需要直接更新到下拉选项列表options.items中(根据label字段直接替换label一样的那个item的value即可。如果这个label不存在则插入一个新的item。如果存在则更新这个item的value(根据label进行查询)
需要开发好前后端保证一切功能正常

最后，你需要