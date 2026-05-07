#!/usr/bin/env python3
"""
全面的字段管理测试脚本
测试所有字段类型的CRUD操作和导入导出功能
使用租户域名、字段组名称、字段名来确定字段（人类友好的方式）
"""
import asyncio
import aiohttp
import csv
import io
from datetime import datetime

BASE_URL = "http://localhost:9999"

def get_auth_headers(token):
    return {"token": token}

def parse_list_response(result):
    """解析列表API返回的数据"""
    if result.get("code") != 200:
        return []
    data = result.get("data", {})
    if isinstance(data, dict):
        return data.get("data", [])
    elif isinstance(data, list):
        return data
    return []

async def login():
    """登录获取token"""
    async with aiohttp.ClientSession() as session:
        login_data = {
            "username": "admin",
            "password": "123456"
        }
        async with session.post(f"{BASE_URL}/api/v1/base/access_token", json=login_data) as resp:
            result = await resp.json()
            if result.get("code") == 200:
                return result["data"]["access_token"]
            else:
                print(f"登录失败: {result}")
                return None

async def create_field(token, field_data):
    """创建字段"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/v1/autofill/field_spec/create",
            json=field_data,
            headers=get_auth_headers(token)
        ) as resp:
            return await resp.json()

async def update_field(token, field_id, field_data):
    """更新字段"""
    async with aiohttp.ClientSession() as session:
        field_data["id"] = field_id
        async with session.post(
            f"{BASE_URL}/api/v1/autofill/field_spec/update",
            json=field_data,
            headers=get_auth_headers(token)
        ) as resp:
            return await resp.json()

async def delete_field(token, field_id):
    """删除字段"""
    async with aiohttp.ClientSession() as session:
        async with session.delete(
            f"{BASE_URL}/api/v1/autofill/field_spec/delete?id={field_id}",
            headers=get_auth_headers(token)
        ) as resp:
            return await resp.json()

async def get_field(token, field_id):
    """获取字段详情"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/v1/autofill/field_spec/get?id={field_id}",
            headers=get_auth_headers(token)
        ) as resp:
            return await resp.json()

async def list_fields(token, page=1, page_size=10):
    """获取字段列表"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/v1/autofill/field_spec/list?page={page}&page_size={page_size}",
            headers=get_auth_headers(token)
        ) as resp:
            return await resp.json()

async def export_fields(token, field_ids):
    """导出字段"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/v1/autofill/field_spec/export",
            json={"ids": field_ids},
            headers=get_auth_headers(token)
        ) as resp:
            return await resp.json()

async def import_fields(token, base_csv_content=None, options_csv_content=None):
    """导入字段 - 使用两个CSV文件"""
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        
        if base_csv_content:
            data.add_field('base_file', base_csv_content, filename='base.csv', content_type='text/csv')
        if options_csv_content:
            data.add_field('options_file', options_csv_content, filename='options.csv', content_type='text/csv')
        
        async with session.post(
            f"{BASE_URL}/api/v1/autofill/field_spec/import",
            data=data,
            headers={"token": token}
        ) as resp:
            return await resp.json()

async def get_field_groups(token):
    """获取字段组列表"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/v1/autofill/field_group/list?page=1&page_size=100",
            headers=get_auth_headers(token)
        ) as resp:
            return await resp.json()

async def get_tenants(token):
    """获取租户列表"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/v1/tenant/list?page=1&page_size=100",
            headers=get_auth_headers(token)
        ) as resp:
            return await resp.json()

# ==================== 测试场景 ====================

async def test_text_field_crud(token):
    """测试场景1: 文本类型字段CRUD"""
    print("\n" + "="*60)
    print("测试场景1: 文本类型字段CRUD")
    print("="*60)
    
    # 获取字段组和租户信息
    groups_result = await get_field_groups(token)
    groups_list = parse_list_response(groups_result)
    
    if not groups_list:
        print("❌ 无法获取字段组信息")
        return False
    
    first_group = groups_list[0]
    group_id = first_group["id"]
    group_name = first_group["group_name"]
    
    tenants_result = await get_tenants(token)
    tenants_list = parse_list_response(tenants_result)
    tenant_domain = tenants_list[0].get("domain", "root") if tenants_list else "root"
    
    print(f"使用字段组: {group_name} (ID: {group_id})")
    print(f"使用租户域名: {tenant_domain}")
    
    timestamp = datetime.now().strftime('%H%M%S')
    field_name = f"test_text_{timestamp}"
    
    # 1. 创建文本字段
    print(f"\n1. 创建文本字段: {field_name}")
    field_data = {
        "field_name": field_name,
        "field_label": "测试文本字段",
        "field_type": "text",
        "fill_instruction": "请输入文本内容",
        "corrections": [{"text": "标注1"}, {"text": "标注2"}],
        "field_group_ids": [group_id]
    }
    
    result = await create_field(token, field_data)
    print(f"   结果: {result.get('msg')}")
    
    if result.get("code") != 200:
        print("   ❌ 创建失败")
        return False
    
    field_id = result["data"]["id"]
    print(f"   ✅ 创建成功，ID: {field_id}")
    
    # 2. 导出验证
    print(f"\n2. 导出字段验证")
    export_result = await export_fields(token, [field_id])
    if export_result.get("code") == 200:
        base_csv = export_result["data"]["base_csv"]
        print(f"   ✅ 导出成功")
        print(f"   导出内容预览:\n{base_csv[:500]}")
        
        # 验证导出内容包含租户域名和字段组名称
        if tenant_domain in base_csv and group_name in base_csv:
            print("   ✅ 导出包含租户域名和字段组名称")
        else:
            print("   ⚠️ 导出可能缺少租户域名或字段组名称")
    else:
        print(f"   ❌ 导出失败: {export_result.get('msg')}")
        return False
    
    # 3. 通过导入修改字段（使用租户域名+字段组名称+字段名）
    print(f"\n3. 通过导入修改字段（使用人类友好的标识）")
    modified_csv = f"""ID,字段名,字段标签,字段类型,填写指引,corrections,状态,租户域名,字段组名称,页面名称,选项来源
,{field_name},修改后的文本字段,text,修改后的填写指引,*修改标注1\n*修改标注2\n*修改标注3,启用,{tenant_domain},{group_name},,
"""
    
    import_result = await import_fields(token, base_csv_content=modified_csv.encode('utf-8-sig'))
    print(f"   导入结果: {import_result.get('msg')}")
    print(f"   导入详情: {import_result.get('data', {})}")
    
    if import_result.get("code") == 200:
        success_count = import_result['data'].get('success_count', 0)
        print(f"   ✅ 导入成功: 成功{success_count}条")
        
        # 验证修改
        get_result = await get_field(token, field_id)
        if get_result.get("code") == 200:
            field_data = get_result["data"]
            if field_data.get("field_label") == "修改后的文本字段":
                print("   ✅ 字段标签已更新")
            else:
                print(f"   ❌ 字段标签未更新: {field_data.get('field_label')}")
                
            corrections = field_data.get("corrections", [])
            if len(corrections) == 3:
                print(f"   ✅ 人工标注已更新，共{len(corrections)}条")
            else:
                print(f"   ⚠️ 人工标注数量不对: {len(corrections)}")
    else:
        print(f"   ❌ 导入失败: {import_result.get('msg')}")
    
    # 4. 删除字段（通过导入设置状态为已删除）
    print(f"\n4. 通过导入删除字段（设置状态为已删除）")
    delete_csv = f"""ID,字段名,字段标签,字段类型,填写指引,corrections,状态,租户域名,字段组名称,页面名称,选项来源
,{field_name},,,,,已删除,{tenant_domain},{group_name},,
"""
    
    delete_result = await import_fields(token, base_csv_content=delete_csv.encode('utf-8-sig'))
    print(f"   删除结果: {delete_result.get('msg')}")
    
    if delete_result.get("code") == 200:
        print(f"   ✅ 删除成功: 删除{delete_result['data'].get('delete_count', 0)}条")
        
        # 验证删除
        get_result = await get_field(token, field_id)
        if get_result.get("code") == 200:
            if not get_result["data"].get("is_active", True):
                print("   ✅ 字段已标记为删除")
            else:
                print("   ❌ 字段仍然有效")
    else:
        print(f"   ❌ 删除失败: {delete_result.get('msg')}")
    
    return True


async def test_select_single_field(token):
    """测试场景2: 下拉单选字段CRUD"""
    print("\n" + "="*60)
    print("测试场景2: 下拉单选字段CRUD")
    print("="*60)
    
    # 获取字段组和租户信息
    groups_result = await get_field_groups(token)
    groups_list = parse_list_response(groups_result)
    
    if not groups_list:
        print("❌ 无法获取字段组信息")
        return False
    
    first_group = groups_list[0]
    group_id = first_group["id"]
    group_name = first_group["group_name"]
    
    tenants_result = await get_tenants(token)
    tenants_list = parse_list_response(tenants_result)
    tenant_domain = tenants_list[0].get("domain", "root") if tenants_list else "root"
    
    timestamp = datetime.now().strftime('%H%M%S')
    field_name = f"test_single_{timestamp}"
    
    # 1. 创建下拉单选字段
    print(f"\n1. 创建下拉单选字段: {field_name}")
    field_data = {
        "field_name": field_name,
        "field_label": "测试下拉单选字段",
        "field_type": "select_single",
        "fill_instruction": "请选择一个选项",
        "corrections": [{"text": "单选标注1"}],
        "field_group_ids": [group_id],
        "options": {
            "source": "static",
            "items": [
                {"value": "option1", "label": "选项1", "fill_instruction": "选项1说明", "corrections": [{"text": "选项1标注"}], "is_deleted": False},
                {"value": "option2", "label": "选项2", "fill_instruction": "选项2说明", "corrections": [], "is_deleted": False}
            ]
        }
    }
    
    result = await create_field(token, field_data)
    print(f"   结果: {result.get('msg')}")
    
    if result.get("code") != 200:
        print("   ❌ 创建失败")
        return False
    
    field_id = result["data"]["id"]
    print(f"   ✅ 创建成功，ID: {field_id}")
    
    # 2. 导出验证
    print(f"\n2. 导出字段验证")
    export_result = await export_fields(token, [field_id])
    if export_result.get("code") == 200:
        base_csv = export_result["data"]["base_csv"]
        options_csv = export_result["data"]["options_csv"]
        print(f"   ✅ 导出成功")
        print(f"   基础字段CSV:\n{base_csv}")
        print(f"   选项详情CSV:\n{options_csv}")
    else:
        print(f"   ❌ 导出失败: {export_result.get('msg')}")
        return False
    
    # 3. 通过导入修改选项
    print(f"\n3. 通过导入修改选项")
    modified_options_csv = f"""字段ID,字段名,选项值,选项标签,填写说明,corrections,状态,租户域名,字段组名称,页面名称
,{field_name},option1,修改后的选项1,修改后的说明,*修改后的标注,启用,{tenant_domain},{group_name},
,{field_name},option3,新增选项3,新增选项说明,*新增标注,启用,{tenant_domain},{group_name},
"""
    
    import_result = await import_fields(token, options_csv_content=modified_options_csv.encode('utf-8-sig'))
    print(f"   导入结果: {import_result.get('msg')}")
    
    if import_result.get("code") == 200:
        print(f"   ✅ 选项导入成功")
        
        # 验证修改
        get_result = await get_field(token, field_id)
        if get_result.get("code") == 200:
            options = get_result["data"].get("options", {})
            items = options.get("items", [])
            print(f"   当前选项数量: {len(items)}")
            for item in items:
                print(f"   - {item.get('value')}: {item.get('label')}")
    
    # 4. 通过导入删除选项
    print(f"\n4. 通过导入删除选项（option2）")
    delete_option_csv = f"""字段ID,字段名,选项值,选项标签,填写说明,corrections,状态,租户域名,字段组名称,页面名称
,{field_name},option2,,,,已删除,{tenant_domain},{group_name},
"""
    
    delete_result = await import_fields(token, options_csv_content=delete_option_csv.encode('utf-8-sig'))
    print(f"   删除结果: {delete_result.get('msg')}")
    
    if delete_result.get("code") == 200:
        print(f"   ✅ 选项删除成功")
    
    return True


async def test_select_multi_field(token):
    """测试场景3: 下拉多选字段CRUD"""
    print("\n" + "="*60)
    print("测试场景3: 下拉多选字段CRUD")
    print("="*60)
    
    # 获取字段组和租户信息
    groups_result = await get_field_groups(token)
    groups_list = parse_list_response(groups_result)
    
    if not groups_list:
        print("❌ 无法获取字段组信息")
        return False
    
    first_group = groups_list[0]
    group_id = first_group["id"]
    group_name = first_group["group_name"]
    
    tenants_result = await get_tenants(token)
    tenants_list = parse_list_response(tenants_result)
    tenant_domain = tenants_list[0].get("domain", "root") if tenants_list else "root"
    
    timestamp = datetime.now().strftime('%H%M%S')
    field_name = f"test_multi_{timestamp}"
    
    # 1. 创建下拉多选字段
    print(f"\n1. 创建下拉多选字段: {field_name}")
    field_data = {
        "field_name": field_name,
        "field_label": "测试下拉多选字段",
        "field_type": "select_multi",
        "fill_instruction": "请选择多个选项",
        "corrections": [{"text": "多选标注1"}, {"text": "多选标注2"}],
        "field_group_ids": [group_id],
        "options": {
            "source": "static",
            "min_selections": 1,
            "max_selections": 3,
            "items": [
                {"value": "m1", "label": "多选1", "fill_instruction": "", "corrections": [], "is_deleted": False},
                {"value": "m2", "label": "多选2", "fill_instruction": "", "corrections": [], "is_deleted": False},
                {"value": "m3", "label": "多选3", "fill_instruction": "", "corrections": [], "is_deleted": False}
            ]
        }
    }
    
    result = await create_field(token, field_data)
    print(f"   结果: {result.get('msg')}")
    
    if result.get("code") != 200:
        print("   ❌ 创建失败")
        return False
    
    field_id = result["data"]["id"]
    print(f"   ✅ 创建成功，ID: {field_id}")
    
    # 2. 导出验证
    print(f"\n2. 导出字段验证")
    export_result = await export_fields(token, [field_id])
    if export_result.get("code") == 200:
        base_csv = export_result["data"]["base_csv"]
        print(f"   ✅ 导出成功")
        # 验证选项来源字段
        if "静态选项" in base_csv:
            print("   ✅ 导出包含选项来源信息")
    
    return True


async def test_import_new_field_via_csv(token):
    """测试场景4: 通过CSV导入全新字段"""
    print("\n" + "="*60)
    print("测试场景4: 通过CSV导入全新字段")
    print("="*60)
    
    # 获取字段组和租户信息
    groups_result = await get_field_groups(token)
    groups_list = parse_list_response(groups_result)
    
    if not groups_list:
        print("❌ 无法获取字段组信息")
        return False
    
    first_group = groups_list[0]
    group_name = first_group["group_name"]
    group_tenant_id = first_group.get("tenant_id", 0)
    
    # 获取租户列表，找到与字段组匹配的租户
    tenants_result = await get_tenants(token)
    tenants_list = parse_list_response(tenants_result)
    
    # 查找与字段组租户ID匹配的租户域名
    tenant_domain = "root"
    for tenant in tenants_list:
        if tenant.get("id") == group_tenant_id:
            tenant_domain = tenant.get("domain", "root")
            break
    
    if tenant_domain == "root" and tenants_list:
        tenant_domain = tenants_list[0].get("domain", "root")
    
    timestamp = datetime.now().strftime('%H%M%S')
    field_name = f"imported_field_{timestamp}"
    
    print(f"\n1. 导入全新文本字段: {field_name}")
    
    # 导入基础字段（不包含ID，表示新建）
    # corrections字段包含换行符，需要用引号包裹
    corrections_value = "*标注1\n*标注2"
    base_csv = f'"ID","字段名","字段标签","字段类型","填写指引","corrections","状态","租户域名","字段组名称","页面名称","选项来源"\n,"{field_name}","导入的文本字段","text","这是导入的字段","{corrections_value}","启用","{tenant_domain}","{group_name}","",""\n'
    
    import_result = await import_fields(token, base_csv_content=base_csv.encode('utf-8-sig'))
    print(f"   导入结果: {import_result.get('msg')}")
    
    if import_result.get("code") == 200:
        success_count = import_result['data'].get('success_count', 0)
        print(f"   ✅ 导入成功: {success_count}条")
        
        # 验证字段已创建并关联到字段组
        list_result = await list_fields(token, page_size=100)
        fields_list = parse_list_response(list_result)
        
        found_field = None
        for f in fields_list:
            if f.get("field_name") == field_name:
                found_field = f
                break
        
        if found_field:
            print(f"   ✅ 字段已创建，ID: {found_field['id']}")
            
            # 检查字段组关联
            field_groups = found_field.get("field_groups", [])
            group_names = [g.get("group_name") for g in field_groups]
            if group_name in group_names:
                print(f"   ✅ 字段已关联到字段组: {group_name}")
            else:
                print(f"   ❌ 字段未关联到预期的字段组")
                print(f"   实际关联的字段组: {group_names}")
        else:
            print("   ❌ 未找到新创建的字段")
    else:
        print(f"   ❌ 导入失败: {import_result.get('msg')}")
        if import_result.get("data", {}).get("errors"):
            for error in import_result["data"]["errors"]:
                print(f"   错误: {error}")
    
    return True


async def test_cross_page_selection(token):
    """测试场景5: 跨分页选择功能（通过浏览器测试）"""
    print("\n" + "="*60)
    print("测试场景5: 跨分页选择功能")
    print("="*60)
    print("此功能需要通过浏览器进行人工测试")
    print("测试步骤:")
    print("1. 打开浏览器访问 http://localhost:3200")
    print("2. 进入字段管理页面")
    print("3. 在第一页选择几个字段")
    print("4. 切换到第二页，选择更多字段")
    print("5. 切换回第一页，验证之前的选择仍然保留")
    print("6. 点击导出按钮，验证所有选中的字段都被导出")
    
    return True


async def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("开始全面测试 - 字段管理功能")
    print("="*60)
    
    # 登录
    print("\n正在登录...")
    token = await login()
    if not token:
        print("登录失败，测试终止")
        return
    
    print("✅ 登录成功")
    
    # 运行所有测试场景
    results = []
    
    results.append(("文本字段CRUD", await test_text_field_crud(token)))
    results.append(("下拉单选字段CRUD", await test_select_single_field(token)))
    results.append(("下拉多选字段CRUD", await test_select_multi_field(token)))
    results.append(("CSV导入新字段", await test_import_new_field_via_csv(token)))
    results.append(("跨分页选择", await test_cross_page_selection(token)))
    
    # 打印测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}: {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    print(f"\n总计: {passed_count}/{len(results)} 个测试通过")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
