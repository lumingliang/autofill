#!/usr/bin/env python3
"""
字段创建脚本 V2 - 适配新架构（无页面管理，直接关联应用）

特性：
- 从YAML配置文件读取所有配置
- 支持灵活的主字段组合（level1/level2/level3 或组合如 level1-level2）
- 支持灵活的次字段组合
- 自动ID生成
- 可配置的字段映射

使用方法:
    python create_fields_v2.py [config.yaml]

示例:
    # 使用默认配置文件 create_fields_config.yaml
    python create_fields_v2.py
    
    # 指定配置文件
    python create_fields_v2.py my_config.yaml
"""

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests
import yaml


# 默认配置文件名
DEFAULT_CONFIG_FILE = "create_fields_config.yaml"
SCRIPT_DIR = Path(__file__).parent.resolve()


def get_default_config_path() -> str:
    """获取默认配置文件的完整路径"""
    script_config = SCRIPT_DIR / DEFAULT_CONFIG_FILE
    if script_config.exists():
        return str(script_config)
    return DEFAULT_CONFIG_FILE


class IDGenerator:
    """ID生成器"""
    
    def __init__(self, prefix: str = "EVT", digit_length: int = 3, use_hierarchical: bool = True):
        self.prefix = prefix
        self.digit_length = digit_length
        self.use_hierarchical = use_hierarchical
        self.counters = {"level1": 0, "level2": 0, "level3": 0}
        self.parent_ids = {}
    
    def generate(self, level: str, parent_id: str = "") -> str:
        """生成ID"""
        self.counters[level] += 1
        counter = self.counters[level]
        
        if level == "level1":
            return f"{self.prefix}{counter:0{self.digit_length}d}"
        elif self.use_hierarchical and parent_id:
            return f"{parent_id}{counter:0{self.digit_length}d}"
        else:
            return f"{self.prefix}{level[-1].upper()}{counter:0{self.digit_length}d}"


class ConfigLoader:
    """配置加载器"""
    
    @staticmethod
    def load(config_path: str) -> Dict:
        """加载YAML配置文件"""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return ConfigLoader._set_defaults(config)
    
    @staticmethod
    def _set_defaults(config: Dict) -> Dict:
        """设置默认配置值"""
        defaults = {
            "api": {
                "base_url": "http://localhost:9999",
                "api_key": ""
            },
            "app": {
                "app_name": "autofill",
                "field_group_name": "default"
            },
            "csv": {
                "file_path": "event_types.csv",
                "field_mapping": {
                    "level1": {"name": "一级事件类型", "id": "", "instruction": ""},
                    "level2": {"name": "二级事件类型", "id": "", "instruction": ""},
                    "level3": {"name": "三级事件类型", "id": "", "instruction": ""}
                }
            },
            "main_field": {
                "name": "事件类型",
                "label": "事件类型",
                "combine_levels": "level1",
                "separator": "-",
                "instruction": "",
                "instruction_template": ""
            },
            "secondary_field": {
                "enabled": True,
                "suffix": "详细分类",
                "combine_levels": "level2-level3",
                "separator": "-",
                "instruction": "",
                "instruction_template": ""
            },
            "id_generation": {
                "level1_prefix": "EVT",
                "digit_length": 3,
                "use_hierarchical_id": True
            },
            "options": {
                "sort_by": "id",
                "deduplicate": True,
                "skip_empty": True
            },
            "advanced": {
                "timeout": 30,
                "verify_creation": True,
                "batch_interval": 0.5,
                "verbose": True
            }
        }
        
        def merge_dict(base: Dict, override: Dict) -> Dict:
            result = base.copy()
            if override:
                for key, value in override.items():
                    if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = merge_dict(result[key], value)
                    else:
                        result[key] = value
            return result
        
        return merge_dict(defaults, config)


class CSVDataLoader:
    """CSV数据加载器"""
    
    def __init__(self, field_mapping: Dict):
        self.field_mapping = field_mapping
    
    def load(self, csv_path: str) -> List[Dict[str, str]]:
        """加载CSV数据"""
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV文件不存在: {csv_path}")
        
        data = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    
    def get_value(self, row: Dict[str, str], level: str, field_type: str) -> str:
        """获取字段值"""
        level_config = self.field_mapping.get(level, {})
        csv_field = level_config.get(field_type, "")
        if not csv_field:
            return ""
        return row.get(csv_field, "")


class DataOrganizer:
    """数据组织器"""
    
    def __init__(self, id_generator: IDGenerator, csv_loader: CSVDataLoader, skip_empty: bool = True):
        self.id_generator = id_generator
        self.csv_loader = csv_loader
        self.skip_empty = skip_empty
        self.data = []
    
    def organize(self, csv_data: List[Dict[str, str]]) -> Dict:
        """组织数据为层级结构"""
        self.data = csv_data
        hierarchy = {}
        
        for row in csv_data:
            level1_name = self.csv_loader.get_value(row, "level1", "name")
            level1_id = self.csv_loader.get_value(row, "level1", "id")
            level1_instruction = self.csv_loader.get_value(row, "level1", "instruction")
            
            level2_name = self.csv_loader.get_value(row, "level2", "name")
            level2_id = self.csv_loader.get_value(row, "level2", "id")
            level2_instruction = self.csv_loader.get_value(row, "level2", "instruction")
            
            level3_name = self.csv_loader.get_value(row, "level3", "name")
            level3_id = self.csv_loader.get_value(row, "level3", "id")
            level3_instruction = self.csv_loader.get_value(row, "level3", "instruction")
            
            if self.skip_empty and not level1_name:
                continue
            
            # 初始化一级
            if level1_name not in hierarchy:
                if not level1_id:
                    level1_id = self.id_generator.generate("level1")
                hierarchy[level1_name] = {
                    "id": level1_id,
                    "instruction": level1_instruction,
                    "children": {}
                }
            
            # 初始化二级
            if level2_name:
                if level2_name not in hierarchy[level1_name]["children"]:
                    if not level2_id:
                        parent_id = hierarchy[level1_name]["id"]
                        level2_id = self.id_generator.generate("level2", parent_id)
                    hierarchy[level1_name]["children"][level2_name] = {
                        "id": level2_id,
                        "instruction": level2_instruction,
                        "children": {}
                    }
                
                # 初始化三级
                if level3_name:
                    if level3_name not in hierarchy[level1_name]["children"][level2_name]["children"]:
                        if not level3_id:
                            parent_id = hierarchy[level1_name]["children"][level2_name]["id"]
                            level3_id = self.id_generator.generate("level3", parent_id)
                        hierarchy[level1_name]["children"][level2_name]["children"][level3_name] = {
                            "id": level3_id,
                            "instruction": level3_instruction
                        }
        
        return hierarchy


class FieldBuilder:
    """字段构建器"""
    
    def __init__(self, hierarchy: Dict, separator: str = "-"):
        self.hierarchy = hierarchy
        self.separator = separator
    
    def parse_combine_levels(self, combine_levels: str) -> List[str]:
        """解析组合级别字符串"""
        return combine_levels.split("-")
    
    def build_combined_name(self, path: List[str]) -> str:
        """构建组合名称"""
        return self.separator.join(path)
    
    def build_combined_id(self, ids: List[str]) -> str:
        """构建组合ID"""
        return "_".join(ids)
    
    def build_main_field_options(self, combine_levels: str, 
                                  instruction_fields: str = "") -> List[Dict]:
        """构建主字段选项"""
        levels = self.parse_combine_levels(combine_levels)
        inst_levels = self.parse_combine_levels(instruction_fields) if instruction_fields else levels
        options = []
        seen = set()
        
        def traverse(current_path: List[str], current_ids: List[str], 
                     current_instructions: List[str], node: Dict, depth: int):
            """递归遍历层级"""
            if depth >= len(levels):
                name = self.build_combined_name(current_path)
                if name in seen:
                    return
                seen.add(name)
                
                option_id = self.build_combined_id(current_ids)
                
                instruction_parts = []
                for i, level in enumerate(inst_levels):
                    level_idx = levels.index(level) if level in levels else -1
                    if level_idx >= 0 and level_idx < len(current_instructions):
                        inst = current_instructions[level_idx]
                        if inst:
                            instruction_parts.append(inst)
                
                instruction = "\n".join(instruction_parts) if instruction_parts else ""
                
                options.append({
                    "label": name,
                    "value": option_id,
                    "fill_instruction": instruction,
                    "_path": current_path.copy(),
                    "_ids": current_ids.copy()
                })
                return
            
            level = levels[depth]
            if depth == 0:
                for name, data in self.hierarchy.items():
                    traverse(
                        current_path + [name],
                        current_ids + [data["id"]],
                        current_instructions + [data.get("instruction", "")],
                        data,
                        depth + 1
                    )
            else:
                children = node.get("children", {})
                for name, data in children.items():
                    traverse(
                        current_path + [name],
                        current_ids + [data["id"]],
                        current_instructions + [data.get("instruction", "")],
                        data,
                        depth + 1
                    )
        
        traverse([], [], [], {}, 0)
        return options
    
    def build_secondary_field_options(self, parent_option: Dict, combine_levels: str,
                                       instruction_fields: str = "") -> List[Dict]:
        """为特定主字段选项构建次字段选项"""
        levels = self.parse_combine_levels(combine_levels)
        inst_levels = self.parse_combine_levels(instruction_fields) if instruction_fields else levels
        options = []
        seen = set()
        
        path = parent_option.get("_path", [])
        if not path:
            return options
        
        node = self.hierarchy.get(path[0], {})
        for i in range(1, len(path)):
            node = node.get("children", {}).get(path[i], {})
        
        def traverse(current_path: List[str], current_ids: List[str],
                     current_instructions: List[str], current_node: Dict, depth: int):
            if depth >= len(levels):
                name = self.build_combined_name(current_path)
                if name in seen:
                    return
                seen.add(name)
                
                option_id = self.build_combined_id(current_ids)
                
                instruction_parts = []
                for i, level in enumerate(inst_levels):
                    level_idx = levels.index(level) if level in levels else -1
                    if level_idx >= 0 and level_idx < len(current_instructions):
                        inst = current_instructions[level_idx]
                        if inst:
                            instruction_parts.append(inst)
                
                instruction = "\n".join(instruction_parts) if instruction_parts else ""
                
                options.append({
                    "label": name,
                    "value": option_id,
                    "fill_instruction": instruction
                })
                return
            
            level = levels[depth]
            level_num = int(level.replace("level", ""))
            
            if level_num == 2:
                children = current_node.get("children", {})
            elif level_num == 3:
                children = current_node.get("children", {})
                if current_node.get("children"):
                    for child_name, child_data in current_node.get("children", {}).items():
                        traverse(
                            current_path + [child_name],
                            current_ids + [child_data["id"]],
                            current_instructions + [child_data.get("instruction", "")],
                            child_data,
                            depth + 1
                        )
                    return
            else:
                children = {}
            
            for child_name, child_data in children.items():
                traverse(
                    current_path + [child_name],
                    current_ids + [child_data["id"]],
                    current_instructions + [child_data.get("instruction", "")],
                    child_data,
                    depth + 1
                )
        
        traverse([], [], [], node, 0)
        return options


class APIClient:
    """API客户端 - 新架构（无page_name）"""
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    
    def create_field_group(self, app_name: str, group_name: str, 
                           fields: List[Dict], is_append: bool = False) -> Dict:
        """创建/更新字段组 - 新API格式（无page_name）"""
        url = f"{self.base_url}/api/autofill/field_group/upsert"
        
        # 新格式：使用app_name替代page_name
        payload = {
            "app_name": app_name,
            "group_name": group_name,
            "fields": fields
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, 
                                    timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"响应状态码: {e.response.status_code}")
                print(f"响应内容: {e.response.text[:500]}")
            raise
    
    def verify_field(self, app_name: str, field_name: str) -> bool:
        """验证字段是否创建成功 - 新API格式"""
        url = f"{self.base_url}/api/autofill/field_spec/list"
        
        # 新格式：使用app_name和group_names/field_names
        params = {
            "app_name": app_name,
            "field_names": [field_name]
        }
        
        try:
            response = requests.post(url, json=params, headers=self.headers, 
                                    timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                return data.get("data") and len(data["data"]) > 0
            return False
        except Exception as e:
            print(f"验证字段失败: {e}")
            return False


class SmartFieldCreator:
    """智能字段创建器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.api_client = APIClient(
            config["api"]["base_url"],
            config["api"]["api_key"],
            config["advanced"]["timeout"]
        )
        self.csv_loader = CSVDataLoader(config["csv"]["field_mapping"])
        self.id_generator = IDGenerator(
            config["id_generation"]["level1_prefix"],
            config["id_generation"]["digit_length"],
            config["id_generation"]["use_hierarchical_id"]
        )
    
    def create_select_field(self, field_name: str, field_label: str,
                           options: List[Dict], fill_instruction: str = "") -> Dict:
        """创建下拉单选字段"""
        clean_options = []
        for opt in options:
            clean_opt = {
                "label": opt["label"],
                "value": opt["value"],
                "fill_instruction": opt.get("fill_instruction", "")
            }
            clean_options.append(clean_opt)
        
        return {
            "field_name": field_name,
            "field_label": field_label,
            "field_type": "select_single",
            "fill_instruction": fill_instruction,
            "options": {
                "items": clean_options,
                "min_selections": 1,
                "max_selections": 1
            }
        }
    
    def run(self):
        """执行字段创建流程"""
        print("=" * 60)
        print("智能字段创建脚本 V2 - 新架构")
        print("=" * 60)
        
        # 1. 加载CSV数据
        csv_path = self.config["csv"]["file_path"]
        csv_path_obj = Path(csv_path)
        if not csv_path_obj.is_absolute() and not csv_path_obj.exists():
            script_dir_csv = SCRIPT_DIR / csv_path
            if script_dir_csv.exists():
                csv_path = str(script_dir_csv)
        print(f"\n[1/5] 加载CSV数据: {csv_path}")
        csv_data = self.csv_loader.load(csv_path)
        print(f"      读取了 {len(csv_data)} 行数据")
        
        # 2. 组织数据
        print("\n[2/5] 组织层级数据...")
        organizer = DataOrganizer(
            self.id_generator, 
            self.csv_loader,
            self.config["options"]["skip_empty"]
        )
        hierarchy = organizer.organize(csv_data)
        print(f"      组织了 {len(hierarchy)} 个一级分类")
        
        # 3. 构建字段
        print("\n[3/5] 构建字段...")
        field_builder = FieldBuilder(
            hierarchy, 
            self.config["main_field"]["separator"]
        )
        
        main_config = self.config["main_field"]
        main_options = field_builder.build_main_field_options(
            main_config["combine_levels"],
            main_config.get("instruction_fields", "")
        )
        print(f"      主字段选项数: {len(main_options)}")
        
        main_field = self.create_select_field(
            main_config["name"],
            main_config["label"],
            main_options,
            main_config.get("instruction", "")
        )
        
        fields = [main_field]
        secondary_fields = []
        
        secondary_config = self.config["secondary_field"]
        if secondary_config["enabled"]:
            print(f"\n      创建次字段（后缀: {secondary_config['suffix']}）...")
            
            for option in main_options:
                secondary_name = f"{option['label']}{secondary_config['suffix']}"
                secondary_label = f"{option['label']}{secondary_config['suffix']}"
                
                secondary_options = field_builder.build_secondary_field_options(
                    option,
                    secondary_config["combine_levels"],
                    secondary_config.get("instruction_fields", "")
                )
                
                if secondary_options:
                    secondary_field = self.create_select_field(
                        secondary_name,
                        secondary_label,
                        secondary_options,
                        secondary_config.get("instruction", "")
                    )
                    secondary_fields.append(secondary_field)
                    print(f"        - {secondary_name}: {len(secondary_options)} 个选项")
            
            fields.extend(secondary_fields)
            print(f"      次字段数量: {len(secondary_fields)}")
        
        # 4. 创建字段组（分批创建）
        print(f"\n[4/5] 创建字段组...")
        app_name = self.config["app"]["app_name"]
        group_name = self.config["app"]["field_group_name"]
        print(f"      应用: {app_name}")
        print(f"      字段组: {group_name}")
        print(f"      字段总数: {len(fields)}")
        
        try:
            # 分批创建所有字段
            print(f"\n      4.1 创建字段组（共{len(fields)}个字段）...")
            batch_size = 10
            for i in range(0, len(fields), batch_size):
                batch = fields[i:i+batch_size]
                print(f"          创建批次 {i//batch_size + 1}/{(len(fields)-1)//batch_size + 1} ({len(batch)}个字段)...")
                result = self.api_client.create_field_group(
                    app_name,
                    group_name,
                    batch,
                    is_append=(i > 0)  # 第一批不追加，后续追加
                )
                time.sleep(self.config["advanced"].get("batch_interval", 0.5))
            print(f"          所有字段创建成功!")
            
        except Exception as e:
            print(f"      创建失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 5. 验证
        if self.config["advanced"]["verify_creation"]:
            print(f"\n[5/5] 验证字段创建...")
            all_verified = True
            for field in fields[:5]:
                verified = self.api_client.verify_field(
                    app_name,
                    field["field_name"]
                )
                status = "✓" if verified else "✗"
                print(f"      {status} {field['field_name']}")
                if not verified:
                    all_verified = False
            
            if len(fields) > 5:
                print(f"      ... 还有 {len(fields) - 5} 个字段未显示")
        
        print("\n" + "=" * 60)
        print("字段创建完成!")
        print("=" * 60)
        return True


def main():
    parser = argparse.ArgumentParser(
        description="智能字段创建脚本 V2 - 新架构",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 使用默认配置文件 create_fields_config.yaml
    python create_fields_v2.py
    
    # 指定配置文件
    python create_fields_v2.py my_config.yaml
        """
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help=f"配置文件路径 (默认: 脚本目录下的 {DEFAULT_CONFIG_FILE})"
    )
    
    args = parser.parse_args()
    
    config_path = args.config if args.config else get_default_config_path()
    
    try:
        print(f"加载配置文件: {config_path}")
        config = ConfigLoader.load(config_path)
        
        creator = SmartFieldCreator(config)
        success = creator.run()
        
        sys.exit(0 if success else 1)
        
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
