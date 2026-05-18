curl -X POST 'http://localhost:9999/api/autofill/dropdown/first_level' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR' \
  -d '{
    "app_name": "test_app",
    "class_name": "事件类型"
  }'

curl -X POST 'http://localhost:9999/api/autofill/dropdown/submenus_tree' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR' \
  -d '{
    "app_name": "test_app",
    "class_name": "事件类型",
    "first_level_value": "EVT001"
  }'



那么现在需要把这两个 CURL 的请求直接使用浏览器新建一个父字段。取合适的名字，然后需要记住是它的选项是从 CURL 里面进行导入的，然后进行同步的。那么成功之后查询数据，用浏览器查询，是不是他的选项已经全部同步了？然后第二步创建他的级联的字段。也是直接在浏览器上操作它的页面，然后也是从 CURL 里面进行导入。中医需要在配置的时候配置好它的各个参数，保证父字段和级联字段都能够创建。你可以分析整个字段管理里面的。创建字段的功能去完成这个事情
先分析整个字段创建包括级联字段创建的流程，包括展平的


从 curl 命令导入 OpenAPI Schema
中 展平配置 (可选) 不需要显示，需要删掉。
标签字段 JSONPath
值字段 JSONPath 也不需要展示，要删掉。
从 curl 命令导入 OpenAPI Schema
只做把curl转为yaml的工作。
点击确定后，才在页面上展示 
标签字段 JSONPath  $.data[*].label  
值字段 JSONPath  $.data[*].value  
然后开关 启用展平
则配置
标签分隔符  -
标签路径2 JSONPath $.data[*].children[*].label
值路径2 JSONPath $.data[*].children[*].value
标签路径3 JSONPath $.data[*].children[*].children[*].label
值路径3 JSONPath $.data[*].children[*].children[*].value


然后对于 级联子字段配置

它不是根据curl解析出来了yaml了吗
，这个yaml不需要改

yaml里面有一个路径 
x-api-params:
    first_level_value: EVT001
这个很关键。我们可以设计一个输入框可以修改这个
比如设置为 x-api-params.first_level_value =parent.$.data[*].label
那么这个就代表了后端要解析这个配置。需要请求级联下拉接口时，需要修改这个参数。
x-api-params.first_level_value
并且让它的值等于父字段的值[*].label，这个值就是遍历父字段的选项得到的

同时 级联子字段配置 页面也是一样。从 curl 命令导入 OpenAPI Schema页面只展示curl 命令 输入框，其他不需要，点击确定后，得到yaml，然后展示
标签字段 JSONPath  $.data[*].label  
值字段 JSONPath  $.data[*].value  
然后开关 启用展平
则配置
标签分隔符  -
标签路径2 JSONPath $.data[*].children[*].label
值路径2 JSONPath $.data[*].children[*].value
标签路径3 JSONPath $.data[*].children[*].children[*].label
值路径3 JSONPath $.data[*].children[*].children[*].value

然后再点击确定，则把这整个配置的级联配置保存到这个字段中，需要针对单个字段进行保存它的级联配置。

API 返回的数据结构是：
{
  "data": [
    {
      "summary": "道路救援",
      "option_value": "EVT001",
      "children": [
        {
          "summary": "拖车服务",
          "option_value": "EVT001001",
          "children": [
            {"summary": "标准拖车", "option_value": "EVT001001001"},
            {"summary": "紧急拖车", "option_value": "EVT001001002"}
          ]
        }
      ]
    }
  ]
}
配置的 flatten_config 是：
label_path_level1: $.data[*].summary
label_path_level2: $.data[*].children[*].summary
label_path_level3: $.data[*].children[*].children[*].summary
现在 ## -现场维修-电池更换
现在也只有两层丢失了第一层的

展平后的三级数据（如 道路救援-拖车服务-标准拖车 ）。

问题出在 /Users/lu/code/code/py/autofill/app/services/autofill/field_flatten_service.py 文件中的 _flatten_with_absolute_paths 方法

智能填单/
字段管理 搜索 测试展平下拉同步 这个字段标签。然后编辑、同步



智能填单/
字段管理
 导入导出功能重构

 