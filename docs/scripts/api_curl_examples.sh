#!/bin/bash
# 智能填单系统公开接口 Curl 示例
# 使用 API Key 认证

# ==================== 配置 ====================
BASE_URL="http://localhost:9999/api/v1"
API_KEY="af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

# ==================== 通用请求头 ====================
COMMON_HEADERS=(-H "Authorization: Bearer ${API_KEY}" -H "Content-Type: application/json")

# ==================== 1. 查询模板列表 ====================
echo "=== 1. 查询模板列表 ==="

# 方式1: Query 参数
curl -X POST "${BASE_URL}/autofill/summary_template/list?class_name=充电故障" \
  "${COMMON_HEADERS[@]}"

echo -e "\n\n---\n"

# 方式2: Form 数据
curl -X POST "${BASE_URL}/autofill/summary_template/list" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "class_name=充电故障"

echo -e "\n\n---\n"

# 方式3: JSON Body
curl -X POST "${BASE_URL}/autofill/summary_template/list" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "class_name": "充电故障"
  }'

echo -e "\n\n"

# ==================== 2. 查询模板详情 ====================
echo "=== 2. 查询模板详情 ==="

# 方式1: Query 参数
curl -X POST "${BASE_URL}/autofill/summary_template?id=1" \
  "${COMMON_HEADERS[@]}"

echo -e "\n\n---\n"

# 方式2: Form 数据
curl -X POST "${BASE_URL}/autofill/summary_template" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "id=1"

echo -e "\n\n---\n"

# 方式3: JSON Body
curl -X POST "${BASE_URL}/autofill/summary_template" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "id": 1
  }'

echo -e "\n\n"

# ==================== 3. 查询下拉选项列表 ====================
echo "=== 3. 查询下拉选项列表 ==="

# 方式1: Query 参数（查询顶级选项）
curl -X POST "${BASE_URL}/autofill/dropdown_options/list?class_name=业务类型&parent_id=0" \
  "${COMMON_HEADERS[@]}"

echo -e "\n\n---\n"

# 方式2: Form 数据
curl -X POST "${BASE_URL}/autofill/dropdown_options/list" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "class_name=业务类型" \
  -d "parent_id=0"

echo -e "\n\n---\n"

# 方式3: JSON Body
curl -X POST "${BASE_URL}/autofill/dropdown_options/list" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "class_name": "业务类型",
    "parent_id": 0
  }'

echo -e "\n\n"

# ==================== 4. 查询下拉选项详情 ====================
echo "=== 4. 查询下拉选项详情 ==="

# 方式1: Query 参数
curl -X POST "${BASE_URL}/autofill/dropdown_options?id=1" \
  "${COMMON_HEADERS[@]}"

echo -e "\n\n---\n"

# 方式2: Form 数据
curl -X POST "${BASE_URL}/autofill/dropdown_options" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "id=1"

echo -e "\n\n---\n"

# 方式3: JSON Body
curl -X POST "${BASE_URL}/autofill/dropdown_options" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "id": 1
  }'

echo -e "\n\n"

# ==================== 5. 记录填单数据 ====================
echo "=== 5. 记录填单数据 ==="

# 方式1: Query 参数（仅简单参数）
curl -X POST "${BASE_URL}/autofill/record_fill_data?session_id=session_001&phone=13800138000" \
  "${COMMON_HEADERS[@]}"

echo -e "\n\n---\n"

# 方式2: Form 数据
curl -X POST "${BASE_URL}/autofill/record_fill_data" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "session_id=session_001" \
  -d "phone=13800138000" \
  -d "user_name=张三" \
  -d "user_unique_id=user_001"

echo -e "\n\n---\n"

# 方式3: JSON Body（推荐，支持复杂数据结构）
curl -X POST "${BASE_URL}/autofill/record_fill_data" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "session_id": "session_001",
    "phone": "13800138000",
    "user_name": "张三",
    "user_unique_id": "user_001",
    "data": {
      "customer_name": "张三",
      "vehicle_system": "比亚迪汉EV",
      "vin_code": "LGX12345678901234",
      "issue_type": "预约充电故障",
      "description": "预约充电功能异常"
    }
  }'

echo -e "\n\n"

# ==================== 6. 获取AI填单数据 ====================
echo "=== 6. 获取AI填单数据 ==="

# 方式1: Query 参数（仅简单参数，data参数需要URL编码）
curl -X POST "${BASE_URL}/autofill/get_ai_fill_data?session_id=session_001" \
  "${COMMON_HEADERS[@]}"

echo -e "\n\n---\n"

# 方式2: Form 数据（data字段会被当作字符串）
curl -X POST "${BASE_URL}/autofill/get_ai_fill_data" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "session_id=session_001"

echo -e "\n\n---\n"

# 方式3: JSON Body（推荐，支持复杂数据结构）
curl -X POST "${BASE_URL}/autofill/get_ai_fill_data" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "session_id": "session_001",
    "data": {
      "customer_name": "张三",
      "contact_phone": "13800138000",
      "vehicle_system": "比亚迪汉EV",
      "vin_code": "LGX12345678901234",
      "issue_description": "车主反馈预约充电功能异常，设置晚上10点开始充电，但实际在插枪后立即开始充电",
      "appointment_time": "22:00",
      "plug_in_time": "18:30",
      "actual_charge_time": "18:35",
      "remaining_battery": "45%",
      "charging_pile_type": "家用充电桩"
    }
  }'

echo -e "\n\n"

# ==================== 使用说明 ====================
echo "=== 使用说明 ==="
echo "1. 修改脚本顶部的 BASE_URL 和 API_KEY 为实际值"
echo "2. 每个接口提供3种调用方式：Query参数 / Form数据 / JSON Body"
echo "3. 推荐使用 JSON Body 方式，支持复杂数据结构"
echo "4. 所有接口都需要在 Header 中携带 Authorization: Bearer {API_KEY}"
echo "5. 可以使用 chmod +x api_curl_examples.sh && ./api_curl_examples.sh 执行测试"
