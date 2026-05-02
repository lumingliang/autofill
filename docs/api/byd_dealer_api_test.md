# 比亚迪经销商门店 API 测试文档

## 公开搜索接口

### 接口信息

- **URL**: `POST /api/byd-dealers/search`
- **认证方式**: API Key (Header: `Authorization: Bearer {api_key}`)
- **Content-Type**: `application/json`

### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| app_key | string | 是 | 应用密钥 |
| name | string | 否 | 门店名称模糊查询 |
| city | string | 否 | 城市模糊查询 |
| address | string | 否 | 地址模糊查询 |
| limit | integer | 否 | 返回数量限制，默认 10，最大 50 |

> **注意**: `name`、`city`、`address` 三个参数至少传一个，支持组合查询

### 测试用例

#### 1. 按门店名称查询

```bash
curl -X POST "http://localhost:9999/api/byd-dealers/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -d '{
    "app_key": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
    "name": "重庆",
    "limit": 5
  }'
```

**预期结果**: 返回名称中包含"重庆"的门店

---

#### 2. 按城市查询

```bash
curl -X POST "http://localhost:9999/api/byd-dealers/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -d '{
    "app_key": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
    "city": "重庆",
    "limit": 5
  }'
```

**预期结果**: 返回城市为"重庆"的所有门店

---

#### 3. 按地址查询

```bash
curl -X POST "http://localhost:9999/api/byd-dealers/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -d '{
    "app_key": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
    "address": "中山",
    "limit": 5
  }'
```

**预期结果**: 返回地址中包含"中山"的门店

---

#### 4. 组合查询（名称 + 城市）

```bash
curl -X POST "http://localhost:9999/api/byd-dealers/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -d '{
    "app_key": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
    "name": "海洋网",
    "city": "重庆",
    "limit": 5
  }'
```

**预期结果**: 返回重庆地区名称中包含"海洋网"的门店

---

#### 5. 组合查询（城市 + 地址）

```bash
curl -X POST "http://localhost:9999/api/byd-dealers/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -d '{
    "app_key": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
    "city": "广州",
    "address": "海珠",
    "limit": 5
  }'
```

**预期结果**: 返回广州地区地址中包含"海珠"的门店

---

#### 6. 三参数组合查询

```bash
curl -X POST "http://localhost:9999/api/byd-dealers/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR" \
  -d '{
    "app_key": "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR",
    "name": "比亚迪",
    "city": "重庆",
    "address": "沙坪坝",
    "limit": 5
  }'
```

**预期结果**: 返回重庆沙坪坝地区名称中包含"比亚迪"的门店

---

### 响应示例

#### 成功响应

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "比亚迪重庆海洋网2号店",
      "code": "BYD_CQ_002",
      "province": "重庆市",
      "city": "重庆",
      "district": "沙坪坝区",
      "address": "重庆市重庆沙坪坝区新华路689号",
      "phone": "023-12345678",
      "contact_person": "张经理",
      "longitude": 106.4598,
      "latitude": 29.5234,
      "dealer_type": "旗舰店",
      "status": "营业中",
      "service_types": ["销售", "售后", "维修"],
      "business_hours": "09:00-18:00",
      "brands": ["比亚迪"],
      "remark": null,
      "created_at": "2024-01-15T08:30:00",
      "updated_at": "2024-01-15T08:30:00"
    }
  ],
  "total": 1,
  "query": "名称:比亚迪; 城市:重庆; 地址:沙坪坝",
  "matched_keywords": ["比亚迪", "重庆", "沙坪坝"],
  "message": "找到 1 家门店"
}
```

#### 失败响应

```json
{
  "success": false,
  "data": [],
  "total": 0,
  "query": "名称:比亚迪; 城市:重庆; 地址:沙坪坝",
  "matched_keywords": [],
  "message": "无效的 AppKey"
}
```

---

## 内部管理接口 (JWT 认证)

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/byd-dealers/dealers` | 创建门店 |
| GET | `/api/v1/byd-dealers/dealers` | 门店列表 |
| GET | `/api/v1/byd-dealers/dealers/{id}` | 获取门店详情 |
| PUT | `/api/v1/byd-dealers/dealers/{id}` | 更新门店 |
| DELETE | `/api/v1/byd-dealers/dealers/{id}` | 删除门店 |
| GET | `/api/v1/byd-dealers/dealers/cities/all` | 获取所有城市 |
| GET | `/api/v1/byd-dealers/dealers/statistics/overview` | 获取统计信息 |

---

## 数据库中的测试数据

| 门店名称 | 城市 | 地址 | 类型 |
|---------|------|------|------|
| 比亚迪重庆服务中心 | 重庆 | 重庆市重庆渝北区中山大道252号 | 专营店 |
| 比亚迪重庆海洋网2号店 | 重庆 | 重庆市重庆沙坪坝区新华路689号 | 旗舰店 |
| 比亚迪广州王朝网 | 广州 | 广东省广州海珠区人民街365号 | 专营店 |
| 比亚迪青岛服务中心 | 青岛 | 山东省青岛崂山区新华路71号 | 体验中心 |
| 比亚迪厦门4S店 | 厦门 | 福建省厦门同安区解放中路645号 | 城市展厅 |

---

## 更新记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-05-02 | v1.0 | 初始版本，支持三个独立参数模糊查询 |
