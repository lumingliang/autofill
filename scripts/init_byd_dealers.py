"""
初始化比亚迪经销商门店数据
生成100个全国经销商数据并绑定到指定应用
"""
import asyncio
import random
import string
from typing import List, Dict, Any

from tortoise import Tortoise

from app.models.byd_dealer import BYDDealer
from app.models.autofill import AppManagement
from app.services.dealer.byd_dealer_service import BYDDealerService
from app.settings.config import settings


# 比亚迪经销商数据模板
DEALER_NAMES = [
    "比亚迪汽车{}4S店", "比亚迪{}王朝网", "比亚迪{}海洋网", "比亚迪{}城市展厅",
    "比亚迪{}体验中心", "比亚迪{}旗舰店", "比亚迪{}专营店", "比亚迪{}服务中心"
]

# 全国主要城市
CITIES = [
    ("北京", "北京市", ["朝阳区", "海淀区", "丰台区", "东城区", "西城区", "昌平区", "大兴区"]),
    ("上海", "上海市", ["浦东新区", "黄浦区", "徐汇区", "长宁区", "静安区", "普陀区", "闵行区"]),
    ("广州", "广东省", ["天河区", "越秀区", "海珠区", "白云区", "番禺区", "黄埔区"]),
    ("深圳", "广东省", ["福田区", "罗湖区", "南山区", "宝安区", "龙岗区", "龙华区"]),
    ("成都", "四川省", ["锦江区", "青羊区", "金牛区", "武侯区", "成华区", "高新区"]),
    ("杭州", "浙江省", ["上城区", "下城区", "江干区", "拱墅区", "西湖区", "滨江区"]),
    ("武汉", "湖北省", ["江岸区", "江汉区", "硚口区", "汉阳区", "武昌区", "洪山区"]),
    ("西安", "陕西省", ["新城区", "碑林区", "莲湖区", "雁塔区", "未央区", "灞桥区"]),
    ("重庆", "重庆市", ["渝中区", "江北区", "南岸区", "九龙坡区", "沙坪坝区", "渝北区"]),
    ("南京", "江苏省", ["玄武区", "秦淮区", "建邺区", "鼓楼区", "浦口区", "栖霞区"]),
    ("天津", "天津市", ["和平区", "河东区", "河西区", "南开区", "河北区", "红桥区"]),
    ("苏州", "江苏省", ["姑苏区", "虎丘区", "吴中区", "相城区", "工业园区"]),
    ("长沙", "湖南省", ["芙蓉区", "天心区", "岳麓区", "开福区", "雨花区"]),
    ("郑州", "河南省", ["中原区", "二七区", "管城回族区", "金水区", "上街区"]),
    ("东莞", "广东省", ["莞城街道", "南城街道", "东城街道", "万江街道"]),
    ("青岛", "山东省", ["市南区", "市北区", "黄岛区", "崂山区", "李沧区"]),
    ("沈阳", "辽宁省", ["和平区", "沈河区", "大东区", "皇姑区", "铁西区"]),
    ("宁波", "浙江省", ["海曙区", "江北区", "北仑区", "镇海区", "鄞州区"]),
    ("昆明", "云南省", ["五华区", "盘龙区", "官渡区", "西山区", "呈贡区"]),
    ("厦门", "福建省", ["思明区", "海沧区", "湖里区", "集美区", "同安区"]),
    ("合肥", "安徽省", ["瑶海区", "庐阳区", "蜀山区", "包河区"]),
    ("佛山", "广东省", ["禅城区", "南海区", "顺德区", "三水区", "高明区"]),
    ("福州", "福建省", ["鼓楼区", "台江区", "仓山区", "马尾区", "晋安区"]),
    ("哈尔滨", "黑龙江省", ["道里区", "南岗区", "道外区", "平房区", "松北区"]),
    ("济南", "山东省", ["历下区", "市中区", "槐荫区", "天桥区", "历城区"]),
]

# 街道地址模板
STREET_TEMPLATES = [
    "{}大道{}号", "{}路{}号", "{}街{}号", "{}中路{}号",
    "{}北路{}号", "{}南路{}号", "{}东路{}号", "{}西路{}号"
]

# 服务类型
SERVICE_TYPES = [
    ["销售", "售后", "维修"],
    ["销售", "售后", "维修", "充电"],
    ["销售", "售后"],
    ["销售"],
    ["销售", "售后", "维修", "充电", "保养"]
]

# 门店类型
DEALER_TYPES = ["4S店", "城市展厅", "体验中心", "旗舰店", "专营店"]

# 经营状态
STATUSES = ["营业中", "营业中", "营业中", "营业中", "装修中"]  # 80%营业中


def generate_phone():
    """生成随机电话号码"""
    prefixes = ["138", "139", "135", "136", "137", "150", "151", "152", "157", "158", "159", "182", "183", "187", "188"]
    prefix = random.choice(prefixes)
    suffix = ''.join(random.choices(string.digits, k=8))
    return f"{prefix}{suffix}"


def generate_dealer_code(city: str, index: int) -> str:
    """生成门店编码"""
    city_code = city[:2]
    return f"BYD{city_code}{index:03d}"


def generate_address(province: str, city: str, district: str) -> str:
    """生成详细地址"""
    street_template = random.choice(STREET_TEMPLATES)
    street_name = random.choice(["人民", "解放", "建设", "中山", "新华", "和平", "光明", "胜利"])
    street_number = random.randint(1, 999)
    street = street_template.format(street_name, street_number)
    return f"{province}{city}{district}{street}"


def generate_dealer_data(city_info: tuple, index: int) -> Dict[str, Any]:
    """生成单个门店数据"""
    city, province, districts = city_info
    district = random.choice(districts)

    dealer_type = random.choice(DEALER_TYPES)
    name_template = random.choice(DEALER_NAMES)
    name = name_template.format(city)

    # 如果有多个同城市门店，添加序号
    if index > 1:
        name = f"{name}{index}号店"

    return {
        "name": name,
        "code": generate_dealer_code(city, index),
        "province": province,
        "city": city,
        "district": district,
        "address": generate_address(province, city, district),
        "phone": generate_phone(),
        "contact_person": f"张{random.choice(['伟', '芳', '娜', '敏', '静', '强', '磊', '洋', '勇', '军'])}",
        "longitude": random.uniform(100.0, 130.0),
        "latitude": random.uniform(20.0, 45.0),
        "dealer_type": dealer_type,
        "status": random.choice(STATUSES),
        "service_types": random.choice(SERVICE_TYPES),
        "business_hours": "09:00-18:00" if random.random() > 0.3 else "08:30-17:30",
        "brands": ["比亚迪"],
        "remark": None
    }


def generate_100_dealers() -> List[Dict[str, Any]]:
    """生成100个经销商数据"""
    dealers = []

    # 为每个城市生成1-4个门店
    city_indices = {}
    for _ in range(100):
        city_info = random.choice(CITIES)
        city = city_info[0]

        if city not in city_indices:
            city_indices[city] = 1
        else:
            city_indices[city] += 1

        dealer = generate_dealer_data(city_info, city_indices[city])
        dealers.append(dealer)

    return dealers


async def init_database():
    """初始化数据库连接"""
    await Tortoise.init(
        config=settings.TORTOISE_ORM
    )


async def get_first_app() -> AppManagement:
    """获取第一个可用的应用"""
    app = await AppManagement.filter(is_active=True).first()
    if not app:
        raise Exception("没有找到可用的应用，请先创建一个应用")
    return app


async def init_byd_dealers():
    """初始化比亚迪经销商数据"""
    print("=" * 60)
    print("初始化比亚迪经销商门店数据")
    print("=" * 60)

    # 初始化数据库
    await init_database()
    print("✓ 数据库连接成功")

    # 获取应用信息
    try:
        app = await get_first_app()
        print(f"✓ 找到应用: {app.app_name}")
        print(f"  - App ID: {app.id}")
        print(f"  - Tenant ID: {app.tenant_id}")
        print(f"  - API Key: {app.api_key}")
    except Exception as e:
        print(f"✗ 获取应用失败: {e}")
        return

    # 生成100个经销商数据
    dealers_data = generate_100_dealers()
    print(f"\n✓ 生成了 {len(dealers_data)} 个经销商数据")

    # 批量创建门店
    count = await BYDDealerService.batch_create_dealers(
        dealers_data,
        tenant_id=app.tenant_id,
        app_id=app.id
    )

    print(f"✓ 成功创建 {count} 个门店")

    # 显示统计信息
    stats = await BYDDealerService.get_statistics(
        tenant_id=app.tenant_id,
        app_id=app.id
    )

    print(f"\n统计信息:")
    print(f"  - 总门店数: {stats['total']}")
    print(f"  - 营业中: {stats['active']}")
    print(f"  - 覆盖城市: {stats['city_count']}")

    # 显示前5个门店
    print(f"\n前5个门店示例:")
    dealers = await BYDDealer.filter(tenant_id=app.tenant_id, app_id=app.id).limit(5).all()
    for i, dealer in enumerate(dealers, 1):
        print(f"  {i}. {dealer.name} ({dealer.city} - {dealer.district})")
        print(f"     地址: {dealer.address}")
        print(f"     电话: {dealer.phone}")

    print("\n" + "=" * 60)
    print("初始化完成！")
    print(f"可以使用 API Key ({app.api_key}) 访问公开接口")
    print("=" * 60)

    # 关闭数据库连接
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(init_byd_dealers())
