"""
CURL 命令解析工具
用于将 curl 命令解析为结构化的请求参数
"""
import json
import re
import shlex
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs


def parse_curl_command(curl_command: str) -> Dict[str, Any]:
    """
    解析 curl 命令，提取请求参数
    
    支持:
    - -X, --request: HTTP 方法
    - -H, --header: 请求头
    - -d, --data: 请求体数据
    - --data-raw: 原始请求体数据
    - -u, --user: 用户认证
    - -b, --cookie: Cookie 数据
    - URL: 请求地址
    
    返回:
    {
        'method': 'POST',
        'url': 'http://localhost:9999/api/autofill/dropdown_options/list',
        'headers': {'Authorization': 'Bearer xxx', 'Content-Type': 'application/json', 'Cookie': 'locale=zh-Hans'},
        'body': {'parent_id': 0},
        'body_raw': '{"parent_id": 0}'
    }
    """
    result = {
        'method': 'GET',
        'url': '',
        'headers': {},
        'body': None,
        'body_raw': None,
        'query_params': {}
    }
    
    if not curl_command or not curl_command.strip().startswith('curl'):
        raise ValueError("无效的 curl 命令")
    
    # 使用 shlex 安全地分割命令
    try:
        tokens = shlex.split(curl_command.strip())
    except ValueError as e:
        raise ValueError(f"解析 curl 命令失败: {e}")
    
    # 移除 'curl'
    if tokens and tokens[0] == 'curl':
        tokens = tokens[1:]
    
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        # HTTP 方法
        if token in ('-X', '--request'):
            i += 1
            if i < len(tokens):
                result['method'] = tokens[i].upper()
        
        # Headers
        elif token in ('-H', '--header'):
            i += 1
            if i < len(tokens):
                header_line = tokens[i]
                if ':' in header_line:
                    key, value = header_line.split(':', 1)
                    result['headers'][key.strip()] = value.strip()
        
        # Data (application/x-www-form-urlencoded)
        elif token in ('-d', '--data'):
            i += 1
            if i < len(tokens):
                data_str = tokens[i]
                result['body_raw'] = data_str
                # 尝试解析为 JSON
                try:
                    result['body'] = json.loads(data_str)
                    if 'Content-Type' not in result['headers']:
                        result['headers']['Content-Type'] = 'application/json'
                except json.JSONDecodeError:
                    # 尝试解析为 form data
                    if '=' in data_str:
                        form_data = {}
                        for pair in data_str.split('&'):
                            if '=' in pair:
                                k, v = pair.split('=', 1)
                                form_data[k] = v
                        result['body'] = form_data
                        if 'Content-Type' not in result['headers']:
                            result['headers']['Content-Type'] = 'application/x-www-form-urlencoded'
        
        # Data raw
        elif token == '--data-raw':
            i += 1
            if i < len(tokens):
                data_str = tokens[i]
                result['body_raw'] = data_str
                try:
                    result['body'] = json.loads(data_str)
                    if 'Content-Type' not in result['headers']:
                        result['headers']['Content-Type'] = 'application/json'
                except json.JSONDecodeError:
                    result['body'] = data_str
        
        # User authentication
        elif token in ('-u', '--user'):
            i += 1
            if i < len(tokens):
                result['headers']['Authorization'] = f"Basic {tokens[i]}"
        
        # Cookie
        elif token in ('-b', '--cookie'):
            i += 1
            if i < len(tokens):
                result['headers']['Cookie'] = tokens[i]
        
        # URL (通常不以 - 开头)
        elif not token.startswith('-') and not result['url']:
            result['url'] = token
        
        i += 1
    
    # 解析 URL 中的 query 参数
    if result['url']:
        parsed = urlparse(result['url'])
        result['query_params'] = {k: v[0] if len(v) == 1 else v 
                                   for k, v in parse_qs(parsed.query).items()}
    
    return result


def infer_schema_from_response(response_data: Any) -> Dict[str, Any]:
    """
    从响应数据推断 JSON Schema 结构
    
    返回 OpenAPI 3.0 格式的 schema 对象
    """
    if response_data is None:
        return {'type': 'string', 'nullable': True}
    
    if isinstance(response_data, bool):
        return {'type': 'boolean'}
    
    if isinstance(response_data, int):
        return {'type': 'integer'}
    
    if isinstance(response_data, float):
        return {'type': 'number'}
    
    if isinstance(response_data, str):
        return {'type': 'string'}
    
    if isinstance(response_data, list):
        if not response_data:
            return {'type': 'array', 'items': {}}
        
        # 推断数组元素的 schema
        item_schemas = [infer_schema_from_response(item) for item in response_data]
        
        # 合并所有元素的 schema（取并集）
        if item_schemas:
            merged = merge_schemas(item_schemas)
            return {'type': 'array', 'items': merged}
        
        return {'type': 'array', 'items': {}}
    
    if isinstance(response_data, dict):
        properties = {}
        required = []
        
        for key, value in response_data.items():
            properties[key] = infer_schema_from_response(value)
            required.append(key)
        
        schema = {
            'type': 'object',
            'properties': properties
        }
        if required:
            schema['required'] = required
        
        return schema
    
    return {'type': 'string'}


def merge_schemas(schemas: list) -> Dict[str, Any]:
    """
    合并多个 schema，取并集
    """
    if not schemas:
        return {}
    
    if len(schemas) == 1:
        return schemas[0]
    
    # 获取所有类型
    types = set()
    for s in schemas:
        t = s.get('type', 'string')
        if isinstance(t, list):
            types.update(t)
        else:
            types.add(t)
    
    # 如果都是对象类型，合并 properties
    if all(s.get('type') == 'object' for s in schemas if s.get('type')):
        all_props = {}
        for s in schemas:
            props = s.get('properties', {})
            for key, prop_schema in props.items():
                if key in all_props:
                    # 递归合并
                    all_props[key] = merge_schemas([all_props[key], prop_schema])
                else:
                    all_props[key] = prop_schema
        
        result = {'type': 'object', 'properties': all_props}
        return result
    
    # 如果都是数组类型
    if all(s.get('type') == 'array' for s in schemas if s.get('type')):
        item_schemas = [s.get('items', {}) for s in schemas if s.get('items')]
        if item_schemas:
            return {'type': 'array', 'items': merge_schemas(item_schemas)}
        return {'type': 'array'}
    
    # 返回最通用的类型
    if len(types) == 1:
        return {'type': list(types)[0]}
    else:
        return {'type': list(types)}


def generate_openapi_schema_from_curl(
    curl_command: str,
    response_data: Any,
    label_path: str = '$.data[*].label',
    value_path: str = '$.data[*].value',
    enable_flatten: bool = False,
    flatten_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    从 curl 命令和响应数据生成 OpenAPI 3.0 Schema
    
    参数:
    - curl_command: curl 命令字符串
    - response_data: API 响应数据
    - label_path: 标签字段的 JSONPath
    - value_path: 值字段的 JSONPath
    
    返回:
    完整的 OpenAPI 3.0 Schema 字典
    """
    # 解析 curl 命令
    parsed = parse_curl_command(curl_command)
    
    # 解析 URL
    parsed_url = urlparse(parsed['url'])
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    path = parsed_url.path
    
    # 构建请求体 schema
    request_body = None
    if parsed['body'] and parsed['method'] in ('POST', 'PUT', 'PATCH'):
        body_schema = infer_schema_from_response(parsed['body'])
        request_body = {
            'content': {
                'application/json': {
                    'schema': body_schema
                }
            }
        }
    
    # 构建响应 schema
    response_schema = infer_schema_from_response(response_data)
    
    # 构建 x-api-params
    x_api_params = {}
    
    # 提取 headers（排除标准 headers）
    standard_headers = {'content-type', 'accept', 'user-agent', 'host', 'connection'}
    custom_headers = {}
    for key, value in parsed['headers'].items():
        if key.lower() not in standard_headers:
            custom_headers[key] = value
    
    if custom_headers:
        x_api_params['headers'] = custom_headers
    
    # 添加 body 中的参数
    if isinstance(parsed['body'], dict):
        for key, value in parsed['body'].items():
            x_api_params[key] = value
    
    # 添加 query 参数
    for key, value in parsed['query_params'].items():
        x_api_params[key] = value
    
    # 构建 x-field-mapping
    x_field_mapping = {
        'label_path': label_path,
        'value_path': value_path
    }
    
    # 如果启用了展平，添加展平配置
    if enable_flatten and flatten_config:
        x_field_mapping['enable_flatten'] = True
        x_field_mapping['flatten_config'] = flatten_config
    
    # 构建 operation
    operation = {
        'summary': f'Generated from curl',
        'x-api-params': x_api_params,
        'x-field-mapping': x_field_mapping,
        'responses': {
            '200': {
                'description': '成功响应',
                'content': {
                    'application/json': {
                        'schema': response_schema
                    }
                }
            }
        }
    }
    
    if request_body:
        operation['requestBody'] = request_body
    
    # 构建完整的 OpenAPI Schema
    openapi_schema = {
        'openapi': '3.0.3',
        'info': {
            'title': 'Generated API',
            'version': '1.0.0'
        },
        'servers': [
            {'url': base_url}
        ],
        'paths': {
            path: {
                parsed['method'].lower(): operation
            }
        }
    }

    return openapi_schema


def generate_template_schema_from_curl(
    curl_command: str,
    response_data: Any,
    template_name_path: str = '$.data[*].name',
    template_content_path: str = '$.data[*].template_content',
    group_name_pattern: str = '$.data[*].name + 的服务记录',
    parse_prompt: str = ''
) -> Dict[str, Any]:
    """
    从 curl 命令和响应数据生成模板类型的 OpenAPI 3.0 Schema

    参数:
    - curl_command: curl 命令字符串
    - response_data: API 响应数据
    - template_name_path: 模板名称字段的 JSONPath (默认: $.data[*].name)
    - template_content_path: 模板内容字段的 JSONPath (默认: $.data[*].template_content)
    - group_name_pattern: 字段组名称生成规则，格式: $.data[*].name + 的服务记录
    - parse_prompt: 模板解析Prompt

    返回:
    完整的 OpenAPI 3.0 Schema 字典，包含模板类型特有的 x-template-mapping 配置
    """
    # 解析 curl 命令
    parsed = parse_curl_command(curl_command)

    # 解析 URL
    parsed_url = urlparse(parsed['url'])
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    path = parsed_url.path

    # 构建请求体 schema
    request_body = None
    if parsed['body'] and parsed['method'] in ('POST', 'PUT', 'PATCH'):
        body_schema = infer_schema_from_response(parsed['body'])
        request_body = {
            'content': {
                'application/json': {
                    'schema': body_schema
                }
            }
        }

    # 构建响应 schema
    response_schema = infer_schema_from_response(response_data)

    # 构建 x-api-params
    x_api_params = {}

    # 提取 headers（排除标准 headers）
    standard_headers = {'content-type', 'accept', 'user-agent', 'host', 'connection'}
    custom_headers = {}
    for key, value in parsed['headers'].items():
        if key.lower() not in standard_headers:
            custom_headers[key] = value

    if custom_headers:
        x_api_params['headers'] = custom_headers

    # 添加 body 中的参数
    if isinstance(parsed['body'], dict):
        for key, value in parsed['body'].items():
            x_api_params[key] = value

    # 添加 query 参数
    for key, value in parsed['query_params'].items():
        x_api_params[key] = value

    # 构建 x-template-mapping（模板类型特有的配置）
    x_template_mapping = {
        'template_name_path': template_name_path,
        'template_content_path': template_content_path,
        'group_name_pattern': group_name_pattern
    }

    if parse_prompt:
        x_template_mapping['parse_prompt'] = parse_prompt

    # 构建 operation
    operation = {
        'summary': 'Template API generated from curl',
        'x-api-params': x_api_params,
        'x-template-mapping': x_template_mapping,
        'responses': {
            '200': {
                'description': '成功响应',
                'content': {
                    'application/json': {
                        'schema': response_schema
                    }
                }
            }
        }
    }

    if request_body:
        operation['requestBody'] = request_body

    # 构建完整的 OpenAPI Schema
    openapi_schema = {
        'openapi': '3.0.3',
        'info': {
            'title': 'Template API',
            'version': '1.0.0'
        },
        'servers': [
            {'url': base_url}
        ],
        'paths': {
            path: {
                parsed['method'].lower(): operation
            }
        }
    }

    return openapi_schema
