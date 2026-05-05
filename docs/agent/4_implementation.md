# 400电话事件类型数据同步脚本实施文档

## 1. 需求概述

### 1.1 业务背景
需要将400电话的事件类型数据从下拉选项系统同步到字段组配置中，实现多级联动下拉菜单的自动化配置。

### 1.2 核心需求
1. **一级事件类型同步**: 查询分类为"400电话"、parent_id=0的下拉选项，创建一级事件类型字段
2. **二三级事件类型同步**: 为每个一级事件类型查询其二三级子选项，展平后创建对应的二三级字段

### 1.3 数据流向
```
DropdownOption (下拉选项表)
    ↓ 查询
Public API (/api/public/autofill/dropdown_options/list)
    ↓ 处理/展平
FieldGroupConfig + FieldSpec (字段组配置 + 字段明细)
    ↓ 调用
Public API (/api/public/autofill/field_group/upsert)
```

---

## 2. 现有架构分析

### 2.1 核心数据模型

#### 2.1.1 DropdownOption (下拉选项表)
- **位置**: `app/models/autofill.py`
- **核心字段**:
  - `option_value`: 选项值
  - `parent_id`: 父选项ID (0表示顶级)
  - `class_name`: 分类名称 (如"400电话")
  - `tenant_id` / `app_name`: 多租户隔离

#### 2.1.2 FieldGroupConfig (字段组配置表)
- **位置**: `app/models/autofill.py`
- **核心字段**:
  - `group_name`: 字段组名称
  - `group_code`: 唯一编码
  - `page_id`: 关联页面ID
  - `prompt_template_base`: Prompt基础模板
  - `output_templates`: 输出模板配置

#### 2.1.3 FieldSpec (字段明细表)
- **位置**: `app/models/autofill.py`
- **核心字段**:
  - `field_name`: 字段英文名
  - `field_label`: 字段显示名称
  - `field_type`: 字段类型 (select/text)
  - `fill_instruction`: 填写指引
  - `options`: 选项配置 (JSON格式)

#### 2.1.4 FieldGroupFieldSpec (关联中间表)
- **多对多关系**: 字段组与字段的关联

### 2.2 公开接口 (Public API)

#### 2.2.1 查询下拉选项列表
```
GET/POST /api/public/autofill/dropdown_options/list
参数:
  - class_name: 分类名称 (如"400电话")
  - parent_id: 父选项ID (0表示顶级)
  - tree: 是否返回树形结构 (默认false)

返回 (tree=false, 默认):
  - id, option_value, summary, has_children

返回 (tree=true):
  - id, option_value, summary, children: [...]

说明:
  - tree=false: 返回扁平列表，只包含直接子项，带has_children标记
  - tree=true: 返回树形结构，递归包含所有子级
  - 通过tree参数灵活切换返回格式

示例:
  # 扁平结构（默认）
  GET /autofill/dropdown_options/list?class_name=400电话&parent_id=0
  # 返回: [{id, option_value, summary, has_children}, ...]

  # 树形结构
  GET /autofill/dropdown_options/list?class_name=400电话&parent_id=0&tree=true
  # 返回: [{id, option_value, summary, children: [{...}, ...]}, ...]
```

#### 2.2.2 字段组批量创建/更新 (核心接口)
```
POST /api/public/autofill/field_group/upsert
参数:
  - page_name: 页面名称 (如"用户信息页")
  - group_name: 字段组名称 (如"default")
  - fields: 字段列表
    - field_name: 字段名
    - field_label: 字段标签
    - field_type: 字段类型 (select/text)
    - fill_instruction: 填写指引
    - options: 选项配置
      - source: "static"
      - items: 选项列表 [{value, label, fill_instruction}]
```

### 2.3 认证方式
- **API Key认证**: 使用 `X-API-Key` Header
- **自动解析**: API Key关联tenant_id和app_name

---

## 3. 脚本设计方案

### 3.1 脚本位置
```
scripts/sync_400_event_types.py
```

### 3.2 核心类设计

```python
class EventTypeSyncer:
    """400电话事件类型同步器"""

    def __init__(self, api_key: str, base_url: str = "http://localhost:9999"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}

    async def get_dropdown_options(self, class_name: str, parent_id: int = 0) -> List[Dict]:
        """查询下拉选项"""

    async def create_field_group_with_fields(
        self,
        page_name: str,
        group_name: str,
        fields: List[Dict]
    ) -> Dict:
        """调用upsert接口创建字段组"""

    async def sync_first_level(self, class_name: str = "400电话"):
        """同步一级事件类型"""

    async def sync_second_third_level(
        self,
        first_level_id: int,
        first_level_value: str,
        class_name: str = "400电话"
    ):
        """同步二三级事件类型"""

    async def get_all_descendants(
        self,
        class_name: str,
        parent_id: int
    ) -> List[Dict]:
        """递归获取所有后代选项"""
```

### 3.3 执行流程

```
┌─────────────────────────────────────────────────────────────┐
│                    同步脚本执行流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 查询一级事件类型                                         │
│     ├─ 调用 /api/public/autofill/dropdown_options/list      │
│     ├─ 参数: class_name="400电话", parent_id=0              │
│     └─ 获取: [{id, option_value, summary}, ...]             │
│                                                             │
│  2. 创建一级事件类型字段                                     │
│     ├─ 构建字段配置                                         │
│     │   field_name: "一级事件类型"                           │
│     │   field_label: "一级事件类型"                          │
│     │   field_type: "select"                                │
│     │   options.items: [{value, label, fill_instruction}]   │
│     └─ 调用 /api/public/autofill/field_group/upsert         │
│                                                             │
│  3. 遍历每个一级事件类型                                     │
│     ├─ 查询其二三级选项                                     │
│     │   调用 /api/public/autofill/dropdown_options/list     │
│     │   参数: parent_id={一级事件类型id}                     │
│     │                                                       │
│     ├─ 展平二三级选项                                       │
│     │   格式: "二级值 - 三级值"                              │
│     │   值: "{二级id}-{三级id}"                              │
│     │                                                       │
│     └─ 创建二三级字段                                       │
│         field_name: "{一级值}-二三级"                        │
│         调用 /api/public/autofill/field_group/upsert        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 数据结构定义

### 4.1 一级事件类型字段配置

```json
{
  "page_name": "用户信息页",
  "group_name": "default",
  "fields": [
    {
      "field_name": "一级事件类型",
      "field_label": "一级事件类型",
      "field_type": "select",
      "fill_instruction": "请选择一级事件类型",
      "options": {
        "source": "static",
        "items": [
          {
            "value": "{一级选项id}",
            "label": "{一级选项值}",
            "fill_instruction": "请填写{一级选项值}"
          }
        ]
      }
    }
  ]
}
```

### 4.2 二三级事件类型字段配置

```json
{
  "page_name": "用户信息页",
  "group_name": "default",
  "fields": [
    {
      "field_name": "{一级事件类型值}-二三级",
      "field_label": "{一级事件类型值}-二三级",
      "field_type": "select",
      "fill_instruction": "请选择二三级事件类型",
      "options": {
        "source": "static",
        "items": [
          {
            "value": "{二级id}-{三级id}",
            "label": "{二级选项值}-{三级选项值}",
            "fill_instruction": "请填写{二级选项值}-{三级选项值}"
          }
        ]
      }
    }
  ]
}
```

---

## 5. 实现代码

```python
#!/usr/bin/env python3
"""
400电话事件类型数据同步脚本

功能:
1. 查询分类为"400电话"的一级下拉选项
2. 创建一级事件类型字段
3. 为每个一级选项查询二三级子选项
4. 展平二三级选项并创建对应字段

使用方法:
    python scripts/sync_400_event_types.py --api-key "af_xxx" [--dry-run]

参数:
    --api-key: API Key (必需)
    --base-url: API基础地址 (默认: http://localhost:9999)
    --class-name: 分类名称 (默认: 400电话)
    --page-name: 页面名称 (默认: 用户信息页)
    --group-name: 字段组名称 (默认: default)
    --dry-run: 只打印日志，不实际创建
"""

import argparse
import asyncio
import re
from typing import Any, Dict, List, Optional

import httpx


class EventTypeSyncer:
    """400电话事件类型同步器"""

    def __init__(self, api_key: str, base_url: str = "http://localhost:9999"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=json_data,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_dropdown_options(
        self,
        class_name: str,
        parent_id: int = 0,
        tree: bool = False,
    ) -> List[Dict]:
        """
        查询下拉选项列表

        Args:
            class_name: 分类名称 (如"400电话")
            parent_id: 父选项ID (0表示顶级)
            tree: 是否返回树形结构 (默认False)

        Returns:
            tree=False: [{id, option_value, summary, has_children}, ...]
            tree=True:  [{id, option_value, summary, children: [...]}, ...]
        """
        params = {
            "class_name": class_name,
            "parent_id": parent_id,
            "tree": tree,
        }

        result = await self._request(
            "GET",
            "/api/public/autofill/dropdown_options/list",
            params=params,
        )

        if result.get("code") != 200:
            raise Exception(f"查询下拉选项失败: {result.get('msg')}")

        return result.get("data", [])

    async def upsert_field_group(
        self,
        page_name: str,
        group_name: str,
        fields: List[Dict],
    ) -> Dict:
        """
        创建或更新字段组

        Args:
            page_name: 页面名称
            group_name: 字段组名称
            fields: 字段列表

        Returns:
            操作结果
        """
        json_data = {
            "page_name": page_name,
            "group_name": group_name,
            "fields": fields,
        }

        result = await self._request(
            "POST",
            "/api/public/autofill/field_group/upsert",
            json_data=json_data,
        )

        if result.get("code") != 200:
            raise Exception(f"创建字段组失败: {result.get('msg')}")

        return result.get("data", {})

    async def get_all_descendants(
        self, class_name: str, parent_id: int
    ) -> List[Dict]:
        """
        递归获取所有后代选项

        Args:
            class_name: 分类名称
            parent_id: 父选项ID

        Returns:
            所有后代选项的展平列表
        """
        result = []

        # 获取直接子选项
        children = await self.get_dropdown_options(class_name, parent_id)

        for child in children:
            child_id = child.get("id")
            child_value = child.get("option_value", "")

            # 获取孙选项
            grandchildren = await self.get_dropdown_options(class_name, child_id)

            if grandchildren:
                # 有三级选项，展平
                for grandchild in grandchildren:
                    grandchild_id = grandchild.get("id")
                    grandchild_value = grandchild.get("option_value", "")

                    result.append({
                        "value": f"{child_id}-{grandchild_id}",
                        "label": f"{child_value} - {grandchild_value}",
                        "fill_instruction": f"请填写{child_value} - {grandchild_value}",
                    })
            else:
                # 只有二级选项
                result.append({
                    "value": str(child_id),
                    "label": child_value,
                    "fill_instruction": f"请填写{child_value}",
                })

        return result

    async def sync_first_level(
        self,
        page_name: str,
        group_name: str,
        class_name: str = "400电话",
        dry_run: bool = False,
    ):
        """
        同步一级事件类型

        Args:
            page_name: 页面名称
            group_name: 字段组名称
            class_name: 分类名称
            dry_run: 是否只打印日志
        """
        print(f"\n[步骤1] 查询一级事件类型...")
        print(f"  分类: {class_name}, parent_id: 0")

        first_level_options = await self.get_dropdown_options(class_name, parent_id=0)

        if not first_level_options:
            print("  ⚠️ 没有一级事件类型数据")
            return []

        print(f"  ✅ 获取到 {len(first_level_options)} 个一级事件类型")
        for opt in first_level_options:
            print(f"     - {opt.get('option_value')} (ID: {opt.get('id')})")

        # 构建字段配置
        field_options = [
            {
                "value": str(opt.get("id")),
                "label": opt.get("option_value", ""),
                "fill_instruction": f"请填写{opt.get('option_value', '')}",
            }
            for opt in first_level_options
        ]

        fields = [
            {
                "field_name": "一级事件类型",
                "field_label": "一级事件类型",
                "field_type": "select",
                "fill_instruction": "请选择一级事件类型",
                "options": {
                    "source": "static",
                    "items": field_options,
                },
            }
        ]

        print(f"\n[步骤2] 创建一级事件类型字段...")
        print(f"  页面: {page_name}")
        print(f"  字段组: {group_name}")
        print(f"  字段名: 一级事件类型")
        print(f"  选项数量: {len(field_options)}")

        if dry_run:
            print("  [Dry Run] 跳过实际创建")
            return first_level_options

        try:
            result = await self.upsert_field_group(
                page_name=page_name,
                group_name=group_name,
                fields=fields,
            )
            print(f"  ✅ 创建成功")
            return first_level_options
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  ⚠️ 字段已存在，跳过")
                return first_level_options
            raise

    async def sync_second_third_level(
        self,
        page_name: str,
        group_name: str,
        first_level_options: List[Dict],
        class_name: str = "400电话",
        dry_run: bool = False,
    ):
        """
        同步二三级事件类型

        Args:
            page_name: 页面名称
            group_name: 字段组名称
            first_level_options: 一级事件类型列表
            class_name: 分类名称
            dry_run: 是否只打印日志
        """
        print(f"\n[步骤3] 同步二三级事件类型...")
        print(f"  共 {len(first_level_options)} 个一级事件类型需要处理\n")

        for first_level in first_level_options:
            first_id = first_level.get("id")
            first_value = first_level.get("option_value", "")

            print(f"  处理: {first_value} (ID: {first_id})")

            # 获取二三级选项
            try:
                flat_options = await self.get_all_descendants(class_name, first_id)
            except Exception as e:
                print(f"    ❌ 获取子选项失败: {e}")
                continue

            if not flat_options:
                print(f"    ⚠️ 没有二三级选项，跳过")
                continue

            print(f"    ✅ 获取到 {len(flat_options)} 个选项")

            # 构建字段名（使用原始值，保持中文）
            field_name = f"{first_value}-二三级"
            field_label = f"{first_value}-二三级"

            fields = [
                {
                    "field_name": field_name,
                    "field_label": field_label,
                    "field_type": "select",
                    "fill_instruction": "请选择二三级事件类型",
                    "options": {
                        "source": "static",
                        "items": flat_options,
                    },
                }
            ]

            print(f"    字段名: {field_name}")
            print(f"    选项示例:")
            for opt in flat_options[:3]:
                print(f"      - {opt['label']}")
            if len(flat_options) > 3:
                print(f"      ... 还有 {len(flat_options) - 3} 个选项")

            if dry_run:
                print(f"    [Dry Run] 跳过实际创建\n")
                continue

            try:
                result = await self.upsert_field_group(
                    page_name=page_name,
                    group_name=group_name,
                    fields=fields,
                )
                print(f"    ✅ 创建成功\n")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"    ⚠️ 字段已存在，跳过\n")
                else:
                    print(f"    ❌ 创建失败: {e}\n")

    async def sync(
        self,
        page_name: str = "用户信息页",
        group_name: str = "default",
        class_name: str = "400电话",
        dry_run: bool = False,
    ):
        """
        执行完整同步

        Args:
            page_name: 页面名称
            group_name: 字段组名称
            class_name: 分类名称
            dry_run: 是否只打印日志
        """
        print("=" * 60)
        print("400电话事件类型数据同步")
        print("=" * 60)
        print(f"API地址: {self.base_url}")
        print(f"分类: {class_name}")
        print(f"页面: {page_name}")
        print(f"字段组: {group_name}")
        print(f"Dry Run: {dry_run}")
        print("=" * 60)

        # 1. 同步一级事件类型
        first_level_options = await self.sync_first_level(
            page_name=page_name,
            group_name=group_name,
            class_name=class_name,
            dry_run=dry_run,
        )

        if not first_level_options:
            print("\n⚠️ 没有一级事件类型，同步结束")
            return

        # 2. 同步二三级事件类型
        await self.sync_second_third_level(
            page_name=page_name,
            group_name=group_name,
            first_level_options=first_level_options,
            class_name=class_name,
            dry_run=dry_run,
        )

        print("=" * 60)
        print("同步完成!")
        print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(
        description="400电话事件类型数据同步脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本用法
    python scripts/sync_400_event_types.py --api-key "af_xxx"

    # 指定页面和字段组
    python scripts/sync_400_event_types.py --api-key "af_xxx" --page-name "用户信息页" --group-name "default"

    # 只打印日志，不实际创建
    python scripts/sync_400_event_types.py --api-key "af_xxx" --dry-run
        """,
    )

    parser.add_argument(
        "--api-key",
        required=True,
        help="API Key (格式: af_xxx)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:9999",
        help="API基础地址 (默认: http://localhost:9999)",
    )
    parser.add_argument(
        "--class-name",
        default="400电话",
        help="分类名称 (默认: 400电话)",
    )
    parser.add_argument(
        "--page-name",
        default="用户信息页",
        help="页面名称 (默认: 用户信息页)",
    )
    parser.add_argument(
        "--group-name",
        default="default",
        help="字段组名称 (默认: default)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印日志，不实际创建字段",
    )

    args = parser.parse_args()

    syncer = EventTypeSyncer(
        api_key=args.api_key,
        base_url=args.base_url,
    )

    await syncer.sync(
        page_name=args.page_name,
        group_name=args.group_name,
        class_name=args.class_name,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. 使用方法

### 6.1 安装依赖
确保已安装 `httpx`:
```bash
pip install httpx
```

### 6.2 获取API Key
从系统管理后台获取API Key (格式: `af_xxxxxxxx...`)

### 6.3 执行同步

#### 基本用法
```bash
python scripts/sync_400_event_types.py --api-key "af_your_api_key"
```

#### 指定页面和字段组
```bash
python scripts/sync_400_event_types.py \
    --api-key "af_your_api_key" \
    --page-name "用户信息页" \
    --group-name "default"
```

#### 预览模式 (不实际创建)
```bash
python scripts/sync_400_event_types.py \
    --api-key "af_your_api_key" \
    --dry-run
```

#### 指定分类
```bash
python scripts/sync_400_event_types.py \
    --api-key "af_your_api_key" \
    --class-name "其他分类"
```

---

## 7. 注意事项

### 7.1 幂等性
- 脚本支持重复执行
- 已存在的字段会自动跳过
- 不会删除或修改已有字段

### 7.2 字段命名
- 字段名会自动清理特殊字符
- 只保留字母、数字和下划线
- 以数字开头的字段名会自动添加下划线前缀

### 7.3 错误处理
- 网络错误会抛出异常
- 字段已存在会跳过并继续
- 单个子选项查询失败不会影响其他选项

### 7.4 性能考虑
- 每个一级事件类型会发起一次查询
- 大量数据时建议分批处理
- 可考虑添加延迟避免请求过快

---

## 8. 扩展建议

### 8.1 增量同步
可记录最后同步时间，只同步变更数据:
```python
# 记录同步状态
sync_state = {
    "last_sync_at": "2024-01-01T00:00:00",
    "synced_count": 100
}
```

### 8.2 字段更新
支持更新已有字段的选项:
```python
# 比较现有选项和新选项
diff = compare_options(existing_options, new_options)
if diff.has_changes:
    await update_field_options(field_id, new_options)
```

### 8.3 批量优化
大量数据时采用批量处理:
```python
# 批量查询子选项
async with asyncio.TaskGroup() as tg:
    tasks = [
        tg.create_task(get_descendants(opt))
        for opt in first_level_options
    ]
```

---

## 9. 相关文件

| 文件路径 | 说明 |
|---------|------|
| `app/models/autofill.py` | 数据模型定义 |
| `app/api/public/autofill.py` | 公开接口实现 |
| `app/schemas/fill_page.py` | 字段相关Schema |
| `app/controllers/autofill.py` | 控制器逻辑 |
| `scripts/sync_dropdown_to_fields.py` | 参考实现 |
| `scripts/sync_template_fields.py` | 参考实现 |

---

## 10. 测试验证

### 10.1 验证下拉选项数据
```bash
# 查询一级选项
curl -X GET "http://localhost:9999/api/public/autofill/dropdown_options/list?class_name=400电话&parent_id=0" \
  -H "X-API-Key: af_your_api_key"

# 查询子选项
curl -X GET "http://localhost:9999/api/public/autofill/dropdown_options/list?class_name=400电话&parent_id=1" \
  -H "X-API-Key: af_your_api_key"
```

### 10.2 验证字段组创建
```bash
# 查询字段组
curl -X GET "http://localhost:9999/api/public/autofill/field_group?page_name=用户信息页&group_name=default" \
  -H "X-API-Key: af_your_api_key"
```

### 10.3 验证字段明细
```bash
# 查询字段列表
curl -X GET "http://localhost:9999/api/public/autofill/field_spec/list?page_name=用户信息页&group_name=default" \
  -H "X-API-Key: af_your_api_key"
```
