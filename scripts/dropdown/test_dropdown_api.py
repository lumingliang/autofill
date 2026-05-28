#!/usr/bin/env python3
"""
测试下拉选项API接口脚本
使用提供的API Key请求一级菜单和二三级菜单树形结构
并将数据展平保存到CSV文件
"""

import requests
import json
import csv

# API配置
BASE_URL = "http://localhost:9999"
API_KEY = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

# 请求头
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def get_first_level_menus(class_name: str = "") -> dict:
    """
    A1. 获取所有一级菜单
    """
    url = f"{BASE_URL}/api/autofill/dropdown/first_level"
    
    payload = {}
    if class_name:
        payload["class_name"] = class_name
    
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        print(f"📝 响应状态码: {response.status_code}")
        print(f"📝 响应内容: {response.text[:500]}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求一级菜单失败: {e}")
        return {"code": -1, "msg": str(e), "data": []}


def get_submenus_tree(first_level_value: str, class_name: str = "") -> dict:
    """
    A2. 根据一级菜单名称获取二三级菜单树形结构
    """
    url = f"{BASE_URL}/api/autofill/dropdown/submenus_tree"
    
    payload = {
        "first_level_value": first_level_value
    }
    if class_name:
        payload["class_name"] = class_name
    
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求二三级菜单失败: {e}")
        return {"code": -1, "msg": str(e), "data": {}}


def print_tree(data: list, indent: int = 0):
    """
    递归打印树形结构
    """
    prefix = "  " * indent
    for item in data:
        print(f"{prefix}├─ {item['option_value']} ({item['summary']})")
        if "children" in item and item["children"]:
            print_tree(item["children"], indent + 1)


def flatten_tree(first_level_value: str, second_level_data: list, third_level_data: list = None) -> list:
    """
    递归展平树形结构，返回展平后的记录列表
    每条记录包含: level1, level1_summary, level2, level2_summary, level3, level3_summary
    """
    flattened = []
    
    for second_item in second_level_data:
        level2_value = second_item.get("option_value", "")
        level2_summary = second_item.get("summary", "")
        
        # 获取三级菜单
        third_level_items = second_item.get("children", [])
        
        if third_level_items:
            for third_item in third_level_items:
                level3_value = third_item.get("option_value", "")
                level3_summary = third_item.get("summary", "")
                flattened.append({
                    "level1": first_level_value,
                    "level1_summary": "",  # 一级菜单的summary需要单独记录
                    "level2": level2_value,
                    "level2_summary": level2_summary,
                    "level3": level3_value,
                    "level3_summary": level3_summary
                })
        else:
            # 如果没有三级菜单，level3为空
            flattened.append({
                "level1": first_level_value,
                "level1_summary": "",
                "level2": level2_value,
                "level2_summary": level2_summary,
                "level3": "",
                "level3_summary": ""
            })
    
    return flattened


def save_to_csv(data: list, filename: str = "dropdown_data.csv"):
    """
    将展平的数据保存到CSV文件
    """
    if not data:
        print("⚠️ 没有数据可保存")
        return
    
    # 按照level1, level2, level3排序
    sorted_data = sorted(data, key=lambda x: (x["level1"], x["level2"], x["level3"]))
    
    # 获取一级菜单的summary并更新
    level1_summary_map = {}
    for row in sorted_data:
        if row["level1"] and not level1_summary_map.get(row["level1"]):
            # 找到第一个包含该level1的行，获取其level1_summary
            for r in sorted_data:
                if r["level1"] == row["level1"] and r.get("level1_summary"):
                    level1_summary_map[row["level1"]] = r["level1_summary"]
                    break
    
    # 更新所有行的level1_summary
    for row in sorted_data:
        if row["level1"] in level1_summary_map:
            row["level1_summary"] = level1_summary_map[row["level1"]]
    
    # 写入CSV文件
    fieldnames = ["level1", "level1_summary", "level2", "level2_summary", "level3", "level3_summary"]
    
    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sorted_data)
        
        print(f"✅ 数据已成功保存到文件: {filename}")
        print(f"📊 共写入 {len(sorted_data)} 条记录")
    except Exception as e:
        print(f"❌ 保存文件失败: {e}")


def main():
    print("=" * 60)
    print("         下拉选项API测试脚本")
    print("=" * 60)
    
    # 存储所有展平后的数据
    all_flattened_data = []
    
    # 1. 获取一级菜单
    print("\n📋 步骤1: 获取一级菜单")
    print("-" * 40)
    
    # 传入分类参数"事件类型"
    result = get_first_level_menus(class_name="事件类型")
    
    if result.get("code") == 200:
        first_level_menus = result.get("data", [])
        print(f"✅ 成功获取 {len(first_level_menus)} 个一级菜单")
        
        if first_level_menus:
            print("\n一级菜单列表:")
            for idx, menu in enumerate(first_level_menus, 1):
                print(f"{idx}. {menu['option_value']} - {menu['summary']}")
                print(f"   ID: {menu['id']}")
                if 'class_name' in menu:
                    print(f"   分类: {menu['class_name']}")
        else:
            print("⚠️ 没有找到一级菜单")
    else:
        print(f"❌ 获取失败: {result.get('msg')}")
        return
    
    # 2. 遍历所有一级菜单，获取每个的二三级菜单
    if first_level_menus:
        print("\n📋 步骤2: 获取所有一级菜单的二三级菜单")
        print("-" * 40)
        
        for idx, first_menu in enumerate(first_level_menus, 1):
            first_menu_value = first_menu["option_value"]
            first_menu_summary = first_menu.get("summary", "")
            
            print(f"\n[{idx}/{len(first_level_menus)}] 获取一级菜单 '{first_menu_value}' 的二三级菜单...")
            
            submenus_result = get_submenus_tree(first_menu_value)
            
            if submenus_result.get("code") == 200:
                data = submenus_result.get("data", {})
                children = data.get("children", [])
                
                print(f"✅ 成功获取二三级菜单")
                print("树形结构:")
                print_tree(children)
                
                # 展平数据
                flattened = flatten_tree(first_menu_value, children)
                
                # 更新level1_summary
                for item in flattened:
                    item["level1_summary"] = first_menu_summary
                
                # 添加到总数据
                all_flattened_data.extend(flattened)
            else:
                print(f"❌ 获取失败: {submenus_result.get('msg')}")
    
    # 3. 保存到CSV文件
    print("\n📋 步骤3: 保存数据到CSV文件")
    print("-" * 40)
    save_to_csv(all_flattened_data)


if __name__ == "__main__":
    main()
