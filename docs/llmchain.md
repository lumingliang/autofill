需要开发一个基于langchain + LiteLLM的代理接口，能够根据请求里面的query参数（即用户输入或者上下文）+ fc调用的参数 类似下面的内容
   

  {
  "type": "function",
  "function": {
    "name": "classify_scene",
    "description": "根据客服对话内容，识别当前工单所属的业务场景",
    "parameters": {
      "type": "object",
      "properties": {
        "scene_name": {
          "type": "string",
          "enum": [
            "投诉处理",
            "业务咨询",
            "预约进店",
            "道路救援",
            "配件查询"
          ],
          "description": "只能从上述选项中选择一个最匹配的场景名称"
        },
        "confidence": {
          "type": "string",
          "enum": ["高", "中", "低"],
          "description": "分类置信度，若对话信息模糊可标记为低"
        }
      },
      "required": ["scene_name"]
    }
  }
}

直接用利用langchain 的with_structured_output能力，可以动态的根据不同的输入要求+上下文，得到结构化的json输出，返回给请求方

LiteLLM主要是作为llm的适配层。然后langchain调用litellm然后litellm适配多个模型。

然后菜单增加一个菜单AI大模型。然后子菜单增加一个llm配置的curd功能（需要支持多租户）数据隔离。超管创建的llm配置tenant_id为空，然后其他租户可以查出来全局的llm配置和自己的llm配置。llm配置需要有llm配置的通用字段。

接口调用方（需传appkey)->代理接口->根据appkey查询llm配置->(注意增加redis缓存) => langchain结构化解析 -》 litellm自动根据配置适配调用不同的模型 ->返回json格式数据
 注意前后端的改造符合当前项目架构