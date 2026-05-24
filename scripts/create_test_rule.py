#!/usr/bin/env python3
"""
创建测试规则数据 - 根据需求文档示例
"""

import asyncio
import sys
import json
import base64
import gzip

sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from tortoise import Tortoise
from app.settings.config import settings
from app.models.rule_management import RuleInfo, RuleVersion


async def init_db():
    """初始化数据库连接"""
    await Tortoise.init(
        db_url=f"mysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}",
        modules={'models': ['app.models.rule_management', 'app.models.admin', 'app.models.autofill']}
    )


async def create_test_rule():
    """创建测试规则"""
    await init_db()
    
    tenant_id = 1
    app_name = "test_app"
    
    # 1. 事件类型分类库 (选择题专用) - 根据需求文档示例
    csv_content_event = """一级事件类型,二级事件类型,三级事件类型,一级事件类型id,二级事件类型id,三级事件类型id,二级事件类型填写规则,三级事件类型填写规则
投诉,商品投诉,质量问题,1,101,10101,用户反馈商品本身存在问题,商品有破损、瑕疵、功能异常
投诉,商品投诉,破损问题,1,101,10102,用户反馈商品本身存在问题,商品收到时已损坏、漏液、变形
投诉,商品投诉,外观问题,1,101,10103,用户反馈商品本身存在问题,商品颜色不符、有划痕、做工粗糙
投诉,物流投诉,配送延迟,1,102,10201,用户反馈物流配送问题,快递超过预计时间未送达
投诉,物流投诉,包裹丢失,1,102,10202,用户反馈物流配送问题,快递显示签收但未收到
投诉,服务投诉,客服态度,1,103,10301,用户反馈服务相关问题,客服态度恶劣、不耐烦、不专业
投诉,服务投诉,处理不及时,1,103,10302,用户反馈服务相关问题,问题提交后长时间未得到处理
咨询,商品咨询,规格参数,2,201,20101,用户咨询商品相关信息,询问商品尺寸、重量、材质等
咨询,商品咨询,使用方法,2,201,20102,用户咨询商品相关信息,询问商品如何使用、操作步骤
咨询,物流咨询,物流进度,2,202,20201,用户咨询物流相关信息,询问快递当前位置、预计送达时间
售后,退换货申请,退货申请,3,301,30101,用户申请售后退换货,用户要求退货退款
售后,退换货申请,换货申请,3,301,30102,用户申请售后退换货,用户要求更换商品
售后,维修申请,上门维修,3,302,30201,用户申请维修服务,要求工作人员上门维修
售后,维修申请,寄回维修,3,302,30202,用户申请维修服务,要求将商品寄回厂家维修"""
    
    await create_or_update_rule(
        tenant_id=tenant_id,
        app_name=app_name,
        rule_code="event_type",
        rule_name="事件类型分类库",
        desc="用于分类用户事件类型，支持投诉、咨询、售后等分类",
        csv_content=csv_content_event
    )
    
    # 2. 常用语模板 (选择题)
    csv_content_common = """模板名称,模板id,模板填写规则,模板内容
投诉安抚,1001,用户表达不满、愤怒情绪时使用，需包含道歉和处理时限,非常抱歉给您带来了不好的体验！关于您反馈的问题，我们已经收到，会立即安排专人处理，预计24小时内给您回复。
咨询解答,1002,用户咨询业务问题时使用，需清晰准确回答,您好，关于您咨询的问题，答案如下：{answer}。如果还有其他疑问，欢迎随时联系我们。
售后指引,1003,用户申请售后时使用，需告知处理流程,您好，您的售后申请已提交成功。我们会在1-3个工作日内审核您的申请，审核通过后会安排后续处理，请您耐心等待。"""
    
    await create_or_update_rule(
        tenant_id=tenant_id,
        app_name=app_name,
        rule_code="common_template",
        rule_name="常用语模板",
        desc="客服常用回复模板，用于快速回复用户",
        csv_content=csv_content_common
    )
    
    # 3. 客服回复模板 (填空题专用) - 根据需求文档示例
    csv_content_reply = """模板名称,模板id,模板填写规则,模板内容,适用场景
手机屏幕破损回复,3001,用户反馈手机屏幕破损时使用，需包含：1. 真诚道歉 2. 要求提供订单号和照片 3. 说明处理方案 4. 告知联系方式,非常抱歉给您带来了不便！关于您反馈的手机屏幕破损问题，为了更好地为您处理，请您提供一下订单号和手机破损的照片。我们收到后会立即为您安排退换货或维修服务，您也可以拨打我们的客服热线400-123-4567咨询进度。,手机类售后
物流延迟回复,3002,用户反馈物流延迟时使用，需包含：1. 道歉 2. 说明可能原因 3. 催促措施 4. 补偿方案,非常抱歉让您久等了！由于近期快递量较大，您的包裹可能会延迟1-2天送达。我们已经联系快递公司加急派送，给您带来的不便我们深表歉意，将为您赠送一张10元无门槛优惠券作为补偿。,物流类投诉
商品质量问题回复,3003,用户反馈商品质量问题时使用，需包含：1. 道歉 2. 核实要求 3. 退换货政策 4. 处理时限,非常抱歉您收到的商品存在质量问题！请您提供一下订单号和商品问题的照片，我们核实后会为您办理免费退换货，来回运费由我们承担。整个处理过程预计需要3-5个工作日。,通用商品投诉"""
    
    await create_or_update_rule(
        tenant_id=tenant_id,
        app_name=app_name,
        rule_code="reply_template",
        rule_name="客服回复模板",
        desc="根据用户问题生成个性化回复内容",
        csv_content=csv_content_reply
    )
    
    print("\n✅ 所有测试规则数据创建完成！")
    print("\n已创建的规则：")
    print("  1. event_type - 事件类型分类库 (选择题)")
    print("  2. common_template - 常用语模板 (选择题)")
    print("  3. reply_template - 客服回复模板 (填空题)")
    
    await Tortoise.close_connections()


async def create_or_update_rule(tenant_id, app_name, rule_code, rule_name, desc, csv_content):
    """创建或更新规则"""
    import csv
    import io
    import hashlib
    
    # 创建规则信息
    rule_info, created = await RuleInfo.get_or_create(
        tenant_id=tenant_id,
        app_name=app_name,
        rule_code=rule_code,
        defaults={
            "rule_name": rule_name,
            "desc": desc,
            "status": 1
        }
    )
    
    if created:
        print(f"✅ 创建规则信息: {rule_code} - {rule_name}")
    else:
        print(f"ℹ️ 规则已存在: {rule_code} - {rule_name}")
    
    # 将CSV转换为JSON格式 (headers + data)
    csv_file = io.StringIO(csv_content)
    reader = csv.reader(csv_file)
    headers = next(reader)
    data = list(reader)
    
    content_dict = {
        "headers": headers,
        "data": data
    }
    
    # 压缩并编码内容
    json_str = json.dumps(content_dict, ensure_ascii=False)
    compressed = gzip.compress(json_str.encode('utf-8'))
    content_encoded = base64.b64encode(compressed).decode('utf-8')
    
    # 创建规则版本
    content_md5 = hashlib.md5(content_encoded.encode()).hexdigest()
    
    # 检查是否已存在相同内容的版本
    existing_version = await RuleVersion.filter(
        tenant_id=tenant_id,
        app_name=app_name,
        rule_id=rule_info.id,
        content_md5=content_md5
    ).first()
    
    if existing_version:
        print(f"   ℹ️ 规则版本已存在: v{existing_version.version_no}")
        rule_info.latest_version_id = existing_version.id
        await rule_info.save()
    else:
        # 获取最新版本号
        latest_version = await RuleVersion.filter(
            tenant_id=tenant_id,
            app_name=app_name,
            rule_id=rule_info.id
        ).order_by("-version_no").first()
        
        version_no = 1 if not latest_version else latest_version.version_no + 1
        
        rule_version = await RuleVersion.create(
            tenant_id=tenant_id,
            app_name=app_name,
            rule_id=rule_info.id,
            version_no=version_no,
            content_md5=content_md5,
            storage_type=1,
            content_json=content_encoded,
            file_size=len(content_encoded.encode()),
            remark="初始版本",
            status=1
        )
        
        print(f"   ✅ 创建规则版本: v{rule_version.version_no}")
        
        # 更新规则信息的最新版本ID
        rule_info.latest_version_id = rule_version.id
        await rule_info.save()


if __name__ == "__main__":
    asyncio.run(create_test_rule())
