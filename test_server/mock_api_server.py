#!/usr/bin/env python3
"""
测试接口服务 - 端口 6666
提供自动填单相关的最小化测试接口：字段列表、级联选项、模板、提交。
"""
import csv
import os
import re
import uuid
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Autofill Test API", version="2.0.0")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts", "data")


def _load_csv(filename: str) -> List[Dict[str, str]]:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


EVENT_TYPES_DATA = _load_csv("event_types.csv")
TEMPLATES_DATA = _load_csv("templates_export.csv")

FORM_FIELDS = [
    {"field_id": "event_type_level1", "field_name": "一级事件类型", "field_type": "dropdown", "required": True},
    {"field_id": "event_type_level2", "field_name": "二级事件类型", "field_type": "dropdown", "required": True},
    {"field_id": "event_type_level3", "field_name": "三级事件类型", "field_type": "dropdown", "required": True},
    {"field_id": "service_summary", "field_name": "服务记录总结", "field_type": "textarea", "required": True},
]


def _dedup_options(rows: List[Dict[str, str]], label_key: str, value_key: str) -> List[Dict[str, str]]:
    seen = set()
    result = []
    for row in rows:
        value = row.get(value_key, "")
        if value and value not in seen:
            seen.add(value)
            result.append({"label": row.get(label_key, ""), "value": value})
    return result


def _get_level1_options() -> List[Dict[str, str]]:
    return _dedup_options(EVENT_TYPES_DATA, "一级事件类型", "一级事件类型ID")


def _get_level2_options(level1_id: str) -> List[Dict[str, str]]:
    return _dedup_options(
        [r for r in EVENT_TYPES_DATA if r.get("一级事件类型ID") == level1_id],
        "二级事件类型",
        "二级事件类型ID",
    )


def _get_level3_options(level2_id: str) -> List[Dict[str, str]]:
    return _dedup_options(
        [r for r in EVENT_TYPES_DATA if r.get("二级事件类型ID") == level2_id],
        "三级事件类型",
        "三级事件类型ID",
    )


def _get_template_by_level3(level3_id: str) -> Optional[Dict[str, str]]:
    mapping = {
        "EVT001001001": "1",
        "EVT001001002": "1",
        "EVT001002001": "5",
        "EVT001002002": "5",
        "EVT001002003": "5",
        "EVT002001001": "2",
        "EVT002001002": "2",
        "EVT002002001": "2",
        "EVT002002002": "2",
        "EVT003001001": "3",
        "EVT003001002": "3",
        "EVT003002001": "4",
        "EVT003002002": "4",
    }
    template_id = mapping.get(level3_id)
    if not template_id:
        return None
    for t in TEMPLATES_DATA:
        if t.get("id") == template_id:
            return t
    return None


def _extract_variables(template_content: str) -> List[Dict[str, Any]]:
    names = re.findall(r"\$\{(\w+)}", template_content)
    return [
        {"name": name, "required": True}
        for name in dict.fromkeys(names)
    ]


@app.get("/api/form/fields")
async def get_form_fields():
    """获取表单字段列表"""
    return {"code": 200, "msg": "OK", "data": FORM_FIELDS}


@app.get("/api/form/fields/{field_id}/options")
async def get_field_options(field_id: str, parent_id: Optional[str] = None):
    """获取下拉字段选项，级联字段需传入 parent_id"""
    if field_id == "event_type_level1":
        options = _get_level1_options()
    elif field_id == "event_type_level2":
        if not parent_id:
            return JSONResponse({"code": 400, "msg": "parent_id required", "data": None}, status_code=400)
        options = _get_level2_options(parent_id)
    elif field_id == "event_type_level3":
        if not parent_id:
            return JSONResponse({"code": 400, "msg": "parent_id required", "data": None}, status_code=400)
        options = _get_level3_options(parent_id)
    else:
        return JSONResponse({"code": 400, "msg": f"field {field_id} has no options", "data": None}, status_code=400)

    return {"code": 200, "msg": "OK", "data": {"field_id": field_id, "parent_id": parent_id, "options": options}}


@app.get("/api/templates/{level3_event_type_id}")
async def get_template(level3_event_type_id: str):
    """根据三级事件类型 ID 获取服务记录模板"""
    template = _get_template_by_level3(level3_event_type_id)
    if not template:
        return JSONResponse({"code": 404, "msg": "template not found", "data": None}, status_code=404)

    content = template.get("template_content", "")
    return {
        "code": 200,
        "msg": "OK",
        "data": {
            "event_type_id": level3_event_type_id,
            "template_id": template.get("id"),
            "template_name": template.get("name"),
            "template_content": content,
            "variables": _extract_variables(content),
        },
    }


@app.post("/api/form/submit")
async def submit_form(request: Request):
    """提交表单"""
    body = await request.json()
    data = body.get("data", {})

    missing = [f["field_name"] for f in FORM_FIELDS if f["required"] and f["field_id"] not in data]
    if missing:
        return JSONResponse(
            {"code": 400, "msg": f"Missing required fields: {', '.join(missing)}", "data": {"missing": missing}},
            status_code=400,
        )

    return {
        "code": 200,
        "msg": "Form submitted successfully",
        "data": {
            "form_id": f"FORM_{uuid.uuid4().hex[:12].upper()}",
            "submitted_at": "2024-01-01T00:00:00Z",
            "summary": {
                "event_type": f"{data.get('event_type_level1')} > {data.get('event_type_level2')} > {data.get('event_type_level3')}",
            },
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "autofill-test-api", "version": "2.0.0"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6666)
