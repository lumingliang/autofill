#!/usr/bin/env python3
"""
测试接口服务 - 端口6666
提供3个测试接口用于验证统一CURL导入引擎
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from typing import Dict, Any, List, Optional

app = FastAPI(title="CURL Import Test API", version="1.0.0")


# ==================== 测试数据 ====================

# 树形结构数据 - 用于单请求测试
TREE_DATA = [
    {
        "id": 1,
        "option_value": "EVT001",
        "summary": "道路救援",
        "code": "ROAD",
        "children": [
            {
                "id": 4,
                "option_value": "EVT001001",
                "summary": "拖车服务",
                "children": [
                    {"id": 10, "option_value": "EVT001001001", "summary": "标准拖车"},
                    {"id": 11, "option_value": "EVT001001002", "summary": "紧急拖车"}
                ]
            },
            {
                "id": 5,
                "option_value": "EVT001002",
                "summary": "现场维修",
                "children": [
                    {"id": 12, "option_value": "EVT001002001", "summary": "电池更换"},
                    {"id": 13, "option_value": "EVT001002002", "summary": "更换轮胎"},
                    {"id": 14, "option_value": "EVT001002003", "summary": "送油服务"}
                ]
            }
        ]
    },
    {
        "id": 2,
        "option_value": "EVT002",
        "summary": "保养预约",
        "code": "MAINT",
        "children": [
            {
                "id": 6,
                "option_value": "EVT002001",
                "summary": "常规保养",
                "children": [
                    {"id": 15, "option_value": "EVT002001001", "summary": "小保养"},
                    {"id": 16, "option_value": "EVT002001002", "summary": "大保养"}
                ]
            },
            {
                "id": 7,
                "option_value": "EVT002002",
                "summary": "专项维修",
                "children": [
                    {"id": 17, "option_value": "EVT002002001", "summary": "刹车系统"},
                    {"id": 18, "option_value": "EVT002002002", "summary": "空调系统"}
                ]
            }
        ]
    },
    {
        "id": 3,
        "option_value": "EVT003",
        "summary": "质量问题",
        "code": "QUALITY",
        "children": [
            {
                "id": 8,
                "option_value": "EVT003001",
                "summary": "车身问题",
                "children": [
                    {"id": 19, "option_value": "EVT003001001", "summary": "漆面问题"},
                    {"id": 20, "option_value": "EVT003001002", "summary": "钣金问题"}
                ]
            },
            {
                "id": 9,
                "option_value": "EVT003002",
                "summary": "动力系统",
                "children": [
                    {"id": 21, "option_value": "EVT003002001", "summary": "发动机故障"},
                    {"id": 22, "option_value": "EVT003002002", "summary": "电池问题"}
                ]
            }
        ]
    }
]

# 一级菜单数据 - 用于级联测试
FIRST_LEVEL_DATA = [
    {"id": 1, "option_value": "EVT001", "summary": "道路救援", "class_name": "事件类型"},
    {"id": 2, "option_value": "EVT002", "summary": "保养预约", "class_name": "事件类型"},
    {"id": 3, "option_value": "EVT003", "summary": "质量问题", "class_name": "事件类型"}
]

# 子菜单映射 - 用于级联测试
SUBMENUS_MAP = {
    "EVT001": [
        {
            "id": 4,
            "option_value": "EVT001001",
            "summary": "拖车服务",
            "children": [
                {"id": 10, "option_value": "EVT001001001", "summary": "标准拖车"},
                {"id": 11, "option_value": "EVT001001002", "summary": "紧急拖车"}
            ]
        },
        {
            "id": 5,
            "option_value": "EVT001002",
            "summary": "现场维修",
            "children": [
                {"id": 12, "option_value": "EVT001002001", "summary": "电池更换"},
                {"id": 13, "option_value": "EVT001002002", "summary": "更换轮胎"},
                {"id": 14, "option_value": "EVT001002003", "summary": "送油服务"}
            ]
        }
    ],
    "EVT002": [
        {
            "id": 6,
            "option_value": "EVT002001",
            "summary": "常规保养",
            "children": [
                {"id": 15, "option_value": "EVT002001001", "summary": "小保养"},
                {"id": 16, "option_value": "EVT002001002", "summary": "大保养"}
            ]
        },
        {
            "id": 7,
            "option_value": "EVT002002",
            "summary": "专项维修",
            "children": [
                {"id": 17, "option_value": "EVT002002001", "summary": "刹车系统"},
                {"id": 18, "option_value": "EVT002002002", "summary": "空调系统"}
            ]
        }
    ],
    "EVT003": [
        {
            "id": 8,
            "option_value": "EVT003001",
            "summary": "车身问题",
            "children": [
                {"id": 19, "option_value": "EVT003001001", "summary": "漆面问题"},
                {"id": 20, "option_value": "EVT003001002", "summary": "钣金问题"}
            ]
        },
        {
            "id": 9,
            "option_value": "EVT003002",
            "summary": "动力系统",
            "children": [
                {"id": 21, "option_value": "EVT003002001", "summary": "发动机故障"},
                {"id": 22, "option_value": "EVT003002002", "summary": "电池问题"}
            ]
        }
    ]
}


# ==================== 接口1: 单请求树形结构 ====================

@app.post("/api/test/tree")
async def get_tree_data(request: Request):
    """
    单请求树形结构接口
    返回完整的三级树形数据
    """
    body = await request.json()
    print(f"[TREE] 收到请求: {body}")
    
    return {
        "code": 200,
        "msg": "OK",
        "data": TREE_DATA
    }


# ==================== 接口2: 级联请求 - 一级菜单 ====================

@app.post("/api/test/first_level")
async def get_first_level(request: Request):
    """
    级联请求第一级接口
    返回一级菜单列表
    """
    body = await request.json()
    print(f"[FIRST_LEVEL] 收到请求: {body}")
    
    return {
        "code": 200,
        "msg": "OK",
        "data": FIRST_LEVEL_DATA
    }


# ==================== 接口3: 级联请求 - 子菜单树 ====================

@app.post("/api/test/submenus")
async def get_submenus(request: Request):
    """
    级联请求第二级接口
    根据 first_level_value 返回子菜单树
    """
    body = await request.json()
    print(f"[SUBMENUS] 收到请求: {body}")
    
    first_level_value = body.get("first_level_value", "")
    
    if not first_level_value:
        return {
            "code": 400,
            "msg": "first_level_value is required",
            "data": None
        }
    
    children = SUBMENUS_MAP.get(first_level_value, [])
    
    # 找到对应的一级菜单信息
    first_level_info = next(
        (item for item in FIRST_LEVEL_DATA if item["option_value"] == first_level_value),
        None
    )
    
    return {
        "code": 200,
        "msg": "OK",
        "data": {
            "first_level": first_level_info,
            "children": children
        }
    }


# ==================== 健康检查 ====================

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "curl-import-test-api"}


if __name__ == "__main__":
    print("=" * 60)
    print("启动测试接口服务")
    print("端口: 6666")
    print("接口:")
    print("  POST /api/test/tree         - 单请求树形结构")
    print("  POST /api/test/first_level  - 级联请求第一级")
    print("  POST /api/test/submenus     - 级联请求第二级")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=6666)
