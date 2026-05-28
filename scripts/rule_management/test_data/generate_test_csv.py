#!/usr/bin/env python3
"""
生成 CSV 导入测试数据 - 包含唯一主键
"""
import csv
import random
import os

# 确保目录存在
os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)

# 定义测试数据模板
event_types = ['投诉', '咨询', '建议', '表扬']
level2_map = {
    '投诉': ['产品质量问题', '服务态度问题', '物流问题', '价格问题', '售后服务问题'],
    '咨询': ['产品信息', '订单信息', '物流信息', '售后政策'],
    '建议': ['产品建议', '服务建议'],
    '表扬': ['产品质量', '服务态度', '物流速度']
}
level3_map = {
    '产品质量问题': ['商品破损', '商品变质', '商品过期', '商品不符'],
    '服务态度问题': ['客服态度差', '配送员态度差', '商家态度差', '售后态度差'],
    '物流问题': ['配送延迟', '商品丢失', '配送地址错误', '物流不更新'],
    '价格问题': ['价格欺诈', '虚假宣传', '乱收费', '价格变动'],
    '售后服务问题': ['退款难', '换货难', '维修难', '投诉无门'],
    '产品信息': ['商品规格', '商品价格', '商品库存', '商品产地'],
    '订单信息': ['订单状态', '订单修改', '订单取消', '订单查询'],
    '物流信息': ['配送进度', '配送时间', '自提点地址', '快递查询'],
    '售后政策': ['退货政策', '换货政策', '保修政策', '退款时效'],
    '产品建议': ['功能改进', '新品需求', '包装改进', '价格调整'],
    '服务建议': ['流程优化', '服务改进', '响应速度', '专业度'],
    '产品质量': ['质量优秀', '品质保证', '用料考究', '做工精细'],
    '服务态度': ['服务周到', '热情耐心', '专业解答', '主动服务'],
    '物流速度': ['配送快速', '准时送达', '包装完好', '送货上门']
}

def generate_v1_unique():
    """生成 V1 版本（3列，2000行，每行主键唯一）
    
    通过添加序号确保每行的主键组合都是唯一的
    """
    rows = []
    used_keys = set()
    
    for i in range(2000):
        # 生成基础数据
        level1 = random.choice(event_types)
        level2 = random.choice(level2_map[level1])
        level3 = random.choice(level3_map[level2])
        
        # 添加序号后缀确保唯一性
        # 格式: 原值_序号，这样每行的主键都是唯一的
        unique_suffix = f"_{i+1:04d}"
        level3_unique = level3 + unique_suffix
        
        # 检查是否重复（理论上不会重复，因为有序号）
        key = (level1, level2, level3_unique)
        if key not in used_keys:
            used_keys.add(key)
            rows.append([level1, level2, level3_unique])
    
    with open('test_data/csv_import_test_v1.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['一级事件类型', '二级事件类型', '三级事件类型'])
        writer.writerows(rows)
    
    print(f"✓ 生成 V1 版本: {len(rows)} 行, 3 列（每行主键唯一）")
    print(f"  唯一主键数: {len(used_keys)}")
    return rows

def generate_v2_unique(base_rows):
    """生成 V2 版本（4列，基于V1修改部分数据）"""
    levels = ['紧急', '高', '中', '低']
    rows_v2 = []
    
    # 修改前 100 行的三级事件类型（模拟数据更新）
    for i, row in enumerate(base_rows):
        if i < 100:
            # 修改三级事件类型
            level1, level2, _ = row
            level3_new = level3_map.get(level2, ['其他'])[0] + f'_V2_{i+1:04d}'
            rows_v2.append([level1, level2, level3_new])
        else:
            rows_v2.append(row)
    
    with open('test_data/csv_import_test_v2.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['一级事件类型', '二级事件类型', '三级事件类型'])
        writer.writerows(rows_v2)
    
    print(f"✓ 生成 V2 版本: {len(rows_v2)} 行（修改100行数据）")
    return rows_v2

def generate_v3_unique():
    """生成 V3 版本（全新的2000行唯一数据）"""
    rows = []
    used_keys = set()
    
    for i in range(2000):
        level1 = random.choice(event_types)
        level2 = random.choice(level2_map[level1])
        level3 = random.choice(level3_map[level2])
        
        # 使用不同的序号范围确保与V1不重复
        unique_suffix = f"_V3_{i+1:04d}"
        level3_unique = level3 + unique_suffix
        
        key = (level1, level2, level3_unique)
        if key not in used_keys:
            used_keys.add(key)
            rows.append([level1, level2, level3_unique])
    
    with open('test_data/csv_import_test_v3.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['一级事件类型', '二级事件类型', '三级事件类型'])
        writer.writerows(rows)
    
    print(f"✓ 生成 V3 版本: {len(rows)} 行, 3 列（全新数据，主键唯一）")
    print(f"  唯一主键数: {len(used_keys)}")
    return rows

def main():
    print("=== 生成 CSV 测试文件（唯一主键版本）===\n")
    
    # 生成 V1 - 2000行唯一数据
    base_rows = generate_v1_unique()
    
    # 生成 V2 - 基于V1修改100行
    generate_v2_unique(base_rows)
    
    # 生成 V3 - 全新2000行唯一数据
    generate_v3_unique()
    
    print("\n=== 测试文件生成完成 ===")
    print("文件列表:")
    print("  1. test_data/csv_import_test_v1.csv - 基础版本（3列，2000行，主键唯一）")
    print("  2. test_data/csv_import_test_v2.csv - 更新版本（3列，2000行，修改100行）")
    print("  3. test_data/csv_import_test_v3.csv - 全新版本（3列，2000行，主键唯一）")
    print("\n说明:")
    print("  - V1和V3的主键完全不重复")
    print("  - V2基于V1修改了前100行，用于测试增量更新")

if __name__ == "__main__":
    main()
