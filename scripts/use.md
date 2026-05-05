cd /Users/lu/code/code/py/autofill && python scripts/sync_400_event_types.py --api-key "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"


curl -s -X POST "http://localhost:9999/api/autofill/field_group/upsert" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -H "Content-Type: application/json" \
  -d '{
    "page_name": "用户信息页",
    "group_name": "default",
    "fields": [{
      "field_name": "一级事件类型",
      "field_label": "一级事件类型(已更新)",
      "field_type": "select",
      "fill_instruction": "请选择一级事件类型(已更新)",
      "options": {
        "source": "static",
        "items": [
          {"value": "1", "label": "智能网联(已更新)", "fill_instruction": "请填写智能网联"},
          {"value": "2", "label": "产品咨询(已更新)", "fill_instruction": "请填写产品咨询"}
        ]
      }
    }]
  }' | python -m json.tool



cd /Users/lu/code/code/py/autofill && python test_new_apis.py



cd /Users/lu/code/code/py/autofill && python test_refactored_api.py


python ./scripts/sync_template_fields.py --api-key "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"