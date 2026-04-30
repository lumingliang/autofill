1. 集成litellm
2. 增加llm.toml文件，里面可以配置litellm支持的各种模型
3. 引入langchain，新加一个llm模块,前端也要新加一个父级菜单，可以输入prompt，然后下拉选择模型，然后选择是否json格式输出，然后点击运行，就可以得到模型的回复，前端需要判断是否为json格式，如果是，就解析为json展示，否则，就直接显示回复
4. llm模块除了提供给前端使用的api接口，还需要增加提供给三方调用的代理接口：主要是让三方输入一个prompt，和模型名称，以及需要的json格式的样例，重试次数。超时时间.然后api接口利用langchain的结构化输出能力，代理转发到llm，得到最终的json格式数据



LLM-Research/c4ai-command-r-plus-08-2024

https://api-inference.modelscope.cn/v1/

ms-919b1188-52f3-4654-b3bd-c46ab3bcf738