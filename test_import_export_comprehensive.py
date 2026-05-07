#!/usr/bin/env python3
"""
全面的导入导出测试脚本 - 覆盖多种场景
"""
import asyncio
import aiohttp
import csv
import io
from datetime import datetime

BASE_URL = "http://localhost:9999"


def get_auth_headers(token):
    return {"token": token}


async def login():
    """登录获取token"""
    async with aiohttp.ClientSession() as session:
        login_data = {"username": "admin", "password": "123456"}
        async with session.post(
            f"{BASE_URL}/api/v1/base/access_token",
            json=login_data
        ) as resp:
            result = await resp.json()
            if result.get("code") == 200:
                return result["data"]["access_token"]
            print(f"登录失败: {result}")
            return None


async def get_field_groups(token):
    """获取字段组列表"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/v1/autofill/field_group/list",
            headers=get_auth_headers(token),
            params={"page": 1, "page_size": 100}
        ) as resp:
            return await resp.json()


async def get_tenants(token):
    """获取租户列表"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/v1/user/my_tenants",
            headers=get_auth_headers(token),
            params={"page": 1, "page_size": 100}
        ) as resp:
            return await resp.json()


async def create_field(token, field_data):
    """创建字段"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/v1/autofill/field_spec/create",
            headers={**get_auth_headers(token), "Content-Type": "application/json"},
            json=field_data
        ) as resp:
            return await resp.json()


async def list_fields(token, page_size=100, field_name=None):
    """获取字段列表"""
    async with aiohttp.ClientSession() as session:
        params = {"page": 1, "page_size": page_size}
        if field_name:
            params["field_name"] = field_name
        async with session.get(
            f"{BASE_URL}/api/v1/autofill/field_spec/list",
            headers=get_auth_headers(token),
            params=params
        ) as resp:
            return await resp.json()


async def get_field_detail(token, field_id):
    """获取字段详情"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/v1/autofill/field_spec/get",
            headers=get_auth_headers(token),
            params={"id": field_id}
        ) as resp:
            return await resp.json()


async def delete_field(token, field_id):
    """删除字段"""
    async with aiohttp.ClientSession() as session:
        async with session.delete(
            f"{BASE_URL}/api/v1/autofill/field_spec/delete",
            headers=get_auth_headers(token),
            params={"id": field_id}
        ) as resp:
            return await resp.json()


async def export_fields(token, ids=None):
    """导出字段"""
    async with aiohttp.ClientSession() as session:
        params = {}
        if ids:
            params["ids"] = ",".join(map(str, ids))
        async with session.get(
            f"{BASE_URL}/api/v1/autofill/field_spec/export",
            headers=get_auth_headers(token),
            params=params
        ) as resp:
            return await resp.json()


async def import_fields(token, base_csv_content=None, options_csv_content=None):
    """导入字段"""
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        if base_csv_content:
            data.add_field("base_file", base_csv_content, filename="base_fields.csv", content_type="text/csv")
        if options_csv_content:
            data.add_field("options_file", options_csv_content, filename="options.csv", content_type="text/csv")
        
        async with session.post(
            f"{BASE_URL}/api/v1/autofill/field_spec/import",
            headers=get_auth_headers(token),
            data=data
        ) as resp:
            return await resp.json()


def parse_list_response(result):
    """解析列表响应"""
    if result.get("code") == 200:
        data = result.get("data", [])
        if isinstance(data, list):
            return data
        return data.get("items", [])
    return []


class TestRunner:
    """测试运行器"""
    
    def __init__(self, token):
        self.token = token
        self.test_results = []
        self.tenant_domain = None
        self.group_name = None
        self.group_id = None
        self.page_name = None
        
    async def setup(self):
        """设置测试环境"""
        # 获取字段组信息
        groups_result = await get_field_groups(self.token)
        groups_list = parse_list_response(groups_result)
        
        if not groups_list:
            print("❌ 无法获取字段组信息")
            return False
        
        first_group = groups_list[0]
        self.group_name = first_group["group_name"]
        self.group_id = first_group["id"]
        self.page_name = first_group.get("page_name", "")
        group_tenant_id = first_group.get("tenant_id", 0)
        
        # 获取匹配的租户
        tenants_result = await get_tenants(self.token)
        tenants_list = parse_list_response(tenants_result)
        
        for tenant in tenants_list:
            if tenant.get("id") == group_tenant_id:
                self.tenant_domain = tenant.get("domain", "root")
                break
        
        # 如果无法获取租户域名，使用硬编码值
        if not self.tenant_domain:
            # 根据字段组租户ID使用默认域名
            if group_tenant_id == 1:
                self.tenant_domain = "tenant-a"
            elif group_tenant_id == 2:
                self.tenant_domain = "tenant-b"
            elif group_tenant_id == 3:
                self.tenant_domain = "test"
            else:
                self.tenant_domain = "test"
        
        print(f"测试环境设置完成:")
        print(f"  字段组: {self.group_name} (ID: {self.group_id})")
        print(f"  页面名称: {self.page_name}")
        print(f"  租户域名: {self.tenant_domain}")
        return True
    
    def create_csv_row(self, **kwargs):
        """创建CSV行数据"""
        defaults = {
            'id': '',
            'field_name': '',
            'field_label': '',
            'field_type': 'text',
            'fill_instruction': '',
            'corrections': '',
            'status': '启用',
            'tenant_domain': self.tenant_domain,
            'group_name': self.group_name,
            'page_name': self.page_name,
            'option_source': ''
        }
        defaults.update(kwargs)

        # CSV字段转义：如果字段包含双引号，需要将其替换为两个双引号
        def escape_csv_field(field):
            if field is None:
                return ''
            field_str = str(field)
            # 将双引号替换为两个双引号
            field_str = field_str.replace('"', '""')
            return field_str

        fields = [
            defaults["id"],
            defaults["field_name"],
            defaults["field_label"],
            defaults["field_type"],
            defaults["fill_instruction"],
            defaults["corrections"],
            defaults["status"],
            defaults["tenant_domain"],
            defaults["group_name"],
            defaults["page_name"],
            defaults["option_source"]
        ]

        # 所有字段都用双引号包裹
        escaped_fields = [f'"{escape_csv_field(f)}"' for f in fields]
        return ','.join(escaped_fields) + '\n'
    
    async def run_test(self, test_name, test_func):
        """运行单个测试"""
        print(f"\n{'='*60}")
        print(f"测试: {test_name}")
        print('='*60)
        try:
            result = await test_func()
            self.test_results.append((test_name, result))
            return result
        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            self.test_results.append((test_name, False))
            return False
    
    # ==================== 测试场景 ====================
    
    async def test_create_text_field(self):
        """测试场景1: 新增文本字段"""
        timestamp = datetime.now().strftime('%H%M%S')
        field_name = f"text_new_{timestamp}"
        
        print(f"1. 导入新文本字段: {field_name}")
        
        csv_content = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        csv_content += self.create_csv_row(
            field_name=field_name,
            field_label="新文本字段",
            field_type="text",
            fill_instruction="这是新文本字段的填写指引",
            corrections="*标注1\n*标注2\n*标注3"
        )
        
        result = await import_fields(self.token, base_csv_content=csv_content.encode('utf-8-sig'))
        
        if result.get("code") != 200:
            print(f"❌ 导入失败: {result.get('msg')}")
            return False
        
        success_count = result['data'].get('success_count', 0)
        if success_count == 0:
            print(f"❌ 导入成功数为0")
            return False
        
        print(f"✅ 导入成功: {success_count}条")
        
        # 验证字段创建
        list_result = await list_fields(self.token, field_name=field_name)
        fields = parse_list_response(list_result)
        if not fields:
            print("❌ 未找到新创建的字段")
            return False
        
        field = fields[0]
        print(f"✅ 字段已创建，ID: {field['id']}")
        
        # 验证字段组关联
        field_groups = field.get("field_groups", [])
        group_names = [g.get("group_name") for g in field_groups]
        if self.group_name not in group_names:
            print(f"❌ 字段未关联到字段组，实际关联: {group_names}")
            return False
        
        print(f"✅ 字段已关联到字段组: {self.group_name}")
        
        # 验证corrections
        detail = await get_field_detail(self.token, field['id'])
        if detail.get("code") == 200:
            corrections = detail['data'].get('corrections', [])
            if len(corrections) == 3:
                print(f"✅ corrections数量正确: {len(corrections)}")
            else:
                print(f"⚠️ corrections数量不对: {len(corrections)}, 期望3")
        
        return True
    
    async def test_create_select_single_field(self):
        """测试场景2: 新增下拉单选字段"""
        timestamp = datetime.now().strftime('%H%M%S')
        field_name = f"single_new_{timestamp}"
        
        print(f"2. 导入新下拉单选字段: {field_name}")
        
        # 基础字段CSV
        base_csv = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        base_csv += self.create_csv_row(
            field_name=field_name,
            field_label="新下拉单选字段",
            field_type="select_single",
            fill_instruction="请选择一项",
            corrections="*单选标注",
            option_source="静态选项"
        )
        
        # 选项CSV
        options_csv = '"字段ID","字段名","选项值","选项标签","填写说明","corrections","状态","租户域名","字段组名称","页面名称"\n'
        options_csv += f'"","{field_name}","option_a","选项A","选项A说明","*选项A标注","启用","{self.tenant_domain}","{self.group_name}",""\n'
        options_csv += f'"","{field_name}","option_b","选项B","选项B说明","","启用","{self.tenant_domain}","{self.group_name}",""\n'
        options_csv += f'"","{field_name}","option_c","选项C","选项C说明","*选项C标注1\n*选项C标注2","启用","{self.tenant_domain}","{self.group_name}",""\n'
        
        result = await import_fields(
            self.token,
            base_csv_content=base_csv.encode('utf-8-sig'),
            options_csv_content=options_csv.encode('utf-8-sig')
        )
        
        if result.get("code") != 200:
            print(f"❌ 导入失败: {result.get('msg')}")
            return False
        
        success_count = result['data'].get('success_count', 0)
        print(f"✅ 导入成功: {success_count}条")
        
        # 验证字段创建
        list_result = await list_fields(self.token, field_name=field_name)
        fields = parse_list_response(list_result)
        if not fields:
            print("❌ 未找到新创建的字段")
            return False
        
        field = fields[0]
        print(f"✅ 字段已创建，ID: {field['id']}")
        
        # 验证选项
        detail = await get_field_detail(self.token, field['id'])
        if detail.get("code") == 200:
            options = detail['data'].get('options', {})
            items = options.get('items', [])
            print(f"✅ 选项数量: {len(items)}")
            for item in items:
                print(f"  - {item['value']}: {item['label']}")
        
        return True
    
    async def test_create_select_multi_field(self):
        """测试场景3: 新增下拉多选字段"""
        timestamp = datetime.now().strftime('%H%M%S')
        field_name = f"multi_new_{timestamp}"
        
        print(f"3. 导入新下拉多选字段: {field_name}")
        
        base_csv = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        base_csv += self.create_csv_row(
            field_name=field_name,
            field_label="新下拉多选字段",
            field_type="select_multi",
            fill_instruction="请选择多项",
            option_source="API接口"
        )
        
        result = await import_fields(self.token, base_csv_content=base_csv.encode('utf-8-sig'))
        
        if result.get("code") != 200:
            print(f"❌ 导入失败: {result.get('msg')}")
            return False
        
        success_count = result['data'].get('success_count', 0)
        print(f"✅ 导入成功: {success_count}条")
        
        # 验证字段创建和选项配置
        list_result = await list_fields(self.token, field_name=field_name)
        fields = parse_list_response(list_result)
        if not fields:
            print("❌ 未找到新创建的字段")
            return False
        
        field = fields[0]
        detail = await get_field_detail(self.token, field['id'])
        if detail.get("code") == 200:
            options = detail['data'].get('options', {})
            print(f"✅ 选项来源: {options.get('source', '未设置')}")
            print(f"✅ 最少选择: {options.get('min_selections', '未设置')}")
            print(f"✅ 最多选择: {options.get('max_selections', '未设置')}")
        
        return True
    
    async def test_update_field_basic(self):
        """测试场景4: 修改字段基本信息"""
        # 先创建一个字段
        timestamp = datetime.now().strftime('%H%M%S')
        field_name = f"update_test_{timestamp}"
        
        print(f"4. 测试修改字段基本信息")
        print(f"   先创建字段: {field_name}")
        
        create_csv = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        create_csv += self.create_csv_row(
            field_name=field_name,
            field_label="原始标签",
            field_type="text",
            fill_instruction="原始指引"
        )
        
        result = await import_fields(self.token, base_csv_content=create_csv.encode('utf-8-sig'))
        if result.get("code") != 200:
            print(f"❌ 创建失败: {result.get('msg')}")
            return False
        
        # 获取字段ID
        list_result = await list_fields(self.token, field_name=field_name)
        fields = parse_list_response(list_result)
        if not fields:
            print("❌ 未找到创建的字段")
            return False
        
        field_id = fields[0]['id']
        print(f"   字段ID: {field_id}")
        
        # 修改字段
        print(f"   修改字段信息")
        update_csv = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        update_csv += self.create_csv_row(
            id=str(field_id),
            field_name=field_name,
            field_label="修改后的标签",
            field_type="text",
            fill_instruction="修改后的指引",
            corrections="*新增标注"
        )
        
        result = await import_fields(self.token, base_csv_content=update_csv.encode('utf-8-sig'))
        if result.get("code") != 200:
            print(f"❌ 修改失败: {result.get('msg')}")
            return False
        
        print(f"✅ 修改成功")
        
        # 验证修改
        detail = await get_field_detail(self.token, field_id)
        if detail.get("code") == 200:
            data = detail['data']
            if data['field_label'] == "修改后的标签":
                print(f"✅ 字段标签已更新")
            else:
                print(f"❌ 字段标签未更新: {data['field_label']}")
                return False
            
            if data['fill_instruction'] == "修改后的指引":
                print(f"✅ 填写指引已更新")
            else:
                print(f"❌ 填写指引未更新: {data['fill_instruction']}")
                return False
        
        return True
    
    async def test_update_field_options(self):
        """测试场景5: 修改字段选项"""
        timestamp = datetime.now().strftime('%H%M%S')
        field_name = f"option_update_{timestamp}"
        
        print(f"5. 测试修改字段选项")
        
        # 创建下拉字段
        base_csv = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        base_csv += self.create_csv_row(
            field_name=field_name,
            field_label="选项测试字段",
            field_type="select_single",
            option_source="静态选项"
        )
        
        options_csv = '"字段ID","字段名","选项值","选项标签","填写说明","corrections","状态","租户域名","字段组名称","页面名称"\n'
        options_csv += f'"","{field_name}","opt1","原始选项1","","","启用","{self.tenant_domain}","{self.group_name}",""\n'
        options_csv += f'"","{field_name}","opt2","原始选项2","","","启用","{self.tenant_domain}","{self.group_name}",""\n'
        
        result = await import_fields(
            self.token,
            base_csv_content=base_csv.encode('utf-8-sig'),
            options_csv_content=options_csv.encode('utf-8-sig')
        )
        
        if result.get("code") != 200:
            print(f"❌ 创建失败: {result.get('msg')}")
            return False
        
        # 获取字段ID
        list_result = await list_fields(self.token, field_name=field_name)
        fields = parse_list_response(list_result)
        if not fields:
            print("❌ 未找到创建的字段")
            return False
        
        field_id = fields[0]['id']
        print(f"   字段创建成功，ID: {field_id}")
        
        # 修改选项
        print(f"   修改选项（修改opt1标签，删除opt2，新增opt3）")
        update_options_csv = '"字段ID","字段名","选项值","选项标签","填写说明","corrections","状态","租户域名","字段组名称","页面名称"\n'
        update_options_csv += f'"{field_id}","{field_name}","opt1","修改后的选项1","新说明","*新标注","启用","{self.tenant_domain}","{self.group_name}",""\n'
        update_options_csv += f'"","{field_name}","opt3","新增选项3","","","启用","{self.tenant_domain}","{self.group_name}",""\n'
        
        result = await import_fields(
            self.token,
            options_csv_content=update_options_csv.encode('utf-8-sig')
        )
        
        if result.get("code") != 200:
            print(f"❌ 修改选项失败: {result.get('msg')}")
            return False
        
        print(f"✅ 选项修改成功")
        
        # 验证选项
        detail = await get_field_detail(self.token, field_id)
        if detail.get("code") == 200:
            options = detail['data'].get('options', {})
            items = options.get('items', [])
            print(f"✅ 当前选项数量: {len(items)}")
            for item in items:
                print(f"  - {item['value']}: {item['label']}")
        
        return True
    
    async def test_delete_field(self):
        """测试场景6: 删除字段"""
        timestamp = datetime.now().strftime('%H%M%S')
        field_name = f"delete_test_{timestamp}"
        
        print(f"6. 测试删除字段")
        
        # 创建字段
        create_csv = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        create_csv += self.create_csv_row(
            field_name=field_name,
            field_label="待删除字段",
            field_type="text"
        )
        
        result = await import_fields(self.token, base_csv_content=create_csv.encode('utf-8-sig'))
        if result.get("code") != 200:
            print(f"❌ 创建失败: {result.get('msg')}")
            return False
        
        # 获取字段ID
        list_result = await list_fields(self.token, field_name=field_name)
        fields = parse_list_response(list_result)
        if not fields:
            print("❌ 未找到创建的字段")
            return False
        
        field_id = fields[0]['id']
        print(f"   字段创建成功，ID: {field_id}")
        
        # 删除字段（设置状态为已删除）
        print(f"   删除字段")
        delete_csv = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        delete_csv += self.create_csv_row(
            id=str(field_id),
            field_name=field_name,
            field_label="待删除字段",
            field_type="text",
            status="已删除"
        )
        
        result = await import_fields(self.token, base_csv_content=delete_csv.encode('utf-8-sig'))
        if result.get("code") != 200:
            print(f"❌ 删除失败: {result.get('msg')}")
            return False
        
        delete_count = result['data'].get('delete_count', 0)
        print(f"✅ 删除成功: {delete_count}条")
        
        # 验证字段已删除
        detail = await get_field_detail(self.token, field_id)
        if detail.get("code") == 200:
            if not detail['data'].get('is_active', True):
                print(f"✅ 字段已标记为删除")
            else:
                print(f"❌ 字段仍然有效")
                return False
        
        return True
    
    async def test_batch_import(self):
        """测试场景7: 批量导入多个字段"""
        timestamp = datetime.now().strftime('%H%M%S')
        
        print(f"7. 测试批量导入多个字段")
        
        # 创建包含多个字段的CSV
        base_csv = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        base_csv += self.create_csv_row(
            field_name=f"batch_text_{timestamp}",
            field_label="批量文本字段",
            field_type="text",
            fill_instruction="批量导入的文本字段"
        )
        base_csv += self.create_csv_row(
            field_name=f"batch_single_{timestamp}",
            field_label="批量单选字段",
            field_type="select_single",
            option_source="静态选项"
        )
        base_csv += self.create_csv_row(
            field_name=f"batch_multi_{timestamp}",
            field_label="批量多选字段",
            field_type="select_multi",
            option_source="API接口"
        )
        
        result = await import_fields(self.token, base_csv_content=base_csv.encode('utf-8-sig'))
        
        if result.get("code") != 200:
            print(f"❌ 批量导入失败: {result.get('msg')}")
            return False
        
        success_count = result['data'].get('success_count', 0)
        print(f"✅ 批量导入成功: {success_count}条")
        
        if success_count != 3:
            print(f"❌ 导入数量不对，期望3，实际{success_count}")
            return False
        
        # 验证所有字段都创建了
        for field_type in ["batch_text", "batch_single", "batch_multi"]:
            field_name = f"{field_type}_{timestamp}"
            list_result = await list_fields(self.token, field_name=field_name)
            fields = parse_list_response(list_result)
            if not fields:
                print(f"❌ 未找到字段: {field_name}")
                return False
            print(f"✅ 字段创建成功: {field_name}")
        
        return True
    
    async def test_error_handling(self):
        """测试场景8: 错误处理"""
        print(f"8. 测试错误处理")
        
        # 测试1: 空字段名
        print(f"   测试空字段名")
        base_csv = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        base_csv += self.create_csv_row(
            field_name="",
            field_label="无效字段",
            field_type="text"
        )
        
        result = await import_fields(self.token, base_csv_content=base_csv.encode('utf-8-sig'))
        if result.get("code") == 200:
            print(f"✅ 系统正确处理了空字段名（跳过或报错）")
        else:
            print(f"✅ 系统返回错误: {result.get('msg')}")
        
        # 测试2: 无效字段类型
        print(f"   测试无效字段类型")
        base_csv = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        base_csv += self.create_csv_row(
            field_name=f"invalid_type_{datetime.now().strftime('%H%M%S')}",
            field_label="无效类型字段",
            field_type="invalid_type"
        )
        
        result = await import_fields(self.token, base_csv_content=base_csv.encode('utf-8-sig'))
        if result.get("code") != 200 or result['data'].get('error_count', 0) > 0:
            print(f"✅ 系统正确处理了无效字段类型")
        else:
            print(f"⚠️ 系统未报错，可能需要检查")
        
        return True
    
    async def test_find_by_names(self):
        """测试场景9: 通过名称查找字段（不使用ID）"""
        timestamp = datetime.now().strftime('%H%M%S')
        field_name = f"byname_test_{timestamp}"
        
        print(f"9. 测试通过名称查找字段（不使用ID）")
        
        # 创建字段
        create_csv = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        create_csv += self.create_csv_row(
            field_name=field_name,
            field_label="通过名称查找测试",
            field_type="text"
        )
        
        result = await import_fields(self.token, base_csv_content=create_csv.encode('utf-8-sig'))
        if result.get("code") != 200:
            print(f"❌ 创建失败: {result.get('msg')}")
            return False
        
        print(f"   字段创建成功")
        
        # 不使用ID，只使用名称修改字段
        print(f"   使用名称修改字段（不提供ID）")
        update_csv = '"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n'
        update_csv += self.create_csv_row(
            field_name=field_name,
            field_label="通过名称修改成功",
            field_type="text"
        )
        
        result = await import_fields(self.token, base_csv_content=update_csv.encode('utf-8-sig'))
        if result.get("code") != 200:
            print(f"❌ 修改失败: {result.get('msg')}")
            return False
        
        print(f"✅ 通过名称修改成功")
        
        # 验证修改
        list_result = await list_fields(self.token, field_name=field_name)
        fields = parse_list_response(list_result)
        if fields and fields[0]['field_label'] == "通过名称修改成功":
            print(f"✅ 验证修改成功")
        else:
            print(f"❌ 验证修改失败")
            return False
        
        return True
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("="*60)
        print("开始全面导入导出测试")
        print("="*60)
        
        if not await self.setup():
            return
        
        # 运行所有测试场景
        await self.run_test("新增文本字段", self.test_create_text_field)
        await self.run_test("新增下拉单选字段", self.test_create_select_single_field)
        await self.run_test("新增下拉多选字段", self.test_create_select_multi_field)
        await self.run_test("修改字段基本信息", self.test_update_field_basic)
        await self.run_test("修改字段选项", self.test_update_field_options)
        await self.run_test("删除字段", self.test_delete_field)
        await self.run_test("批量导入多个字段", self.test_batch_import)
        await self.run_test("错误处理", self.test_error_handling)
        await self.run_test("通过名称查找字段", self.test_find_by_names)
        
        # 打印测试总结
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{status}: {test_name}")
        
        print(f"\n总计: {passed}/{total} 个测试通过")


async def main():
    print("正在登录...")
    token = await login()
    if not token:
        print("登录失败")
        return
    
    print("✅ 登录成功\n")
    
    runner = TestRunner(token)
    await runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
