# LiteLLM 网关服务

## 简介

LiteLLM 作为独立的大模型网关服务，统一适配多种模型提供商，为后端服务提供标准化的模型调用接口。

官方文档：[https://docs.litellm.com.cn/docs/](https://docs.litellm.com.cn/docs/)

## 目录结构

```
litellm/
├── config.yaml          # LiteLLM 配置文件
├── docker-compose.yml   # Docker Compose 配置
└── README.md           # 说明文档
```

---

## 启动方式

### 方式一：Python 环境直接启动（推荐开发环境使用）

#### 1. 安装 LiteLLM

```bash
# 基础安装
pip install litellm

# 安装代理服务器（LLM 网关）完整功能
pip install 'litellm[proxy]'
```

#### 2. 配置环境变量

```bash
# LiteLLM 主密钥（用于管理接口）
export LITELLM_MASTER_KEY="sk-litellm-master-key"

# 数据库 URL（使用项目现有的 MySQL）
export DATABASE_URL="mysql://root:root123456@localhost:3306/autofill"

# Redis 配置（使用项目现有的 Redis）
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_PASSWORD="redis123456"

# 日志级别
export LOG_LEVEL="INFO"
```

#### 3. 启动服务

```bash
# 进入 litellm 目录
cd /Users/lu/code/code/py/autofill/litellm

# 启动 LiteLLM 代理服务器
litellm --config config.yaml --port 4000 --host 0.0.0.0
```

或者使用配置文件中的设置：

```bash
litellm --config config.yaml
```

#### 4. 后台运行（可选）

```bash
# 使用 nohup 后台运行
nohup litellm --config config.yaml --port 4000 --host 0.0.0.0 > /tmp/litellm.log 2>&1 &

# 查看进程
ps aux | grep litellm

# 停止服务
pkill -f "litellm"
```

---

### 方式二：Docker Compose 启动（推荐生产环境使用）

#### 1. 启动服务

```bash
cd /Users/lu/code/code/py/autofill/litellm
docker-compose up -d
```

#### 2. 查看日志

```bash
docker-compose logs -f litellm
```

#### 3. 停止服务

```bash
docker-compose down
```

---

## 配置说明

### 数据库

使用项目现有的 MySQL 数据库：
- 主机: `localhost:3306` (Python) / `host.docker.internal:3306` (Docker)
- 数据库: `autofill`
- 用户名: `root`
- 密码: `root123456`

### 缓存

使用项目现有的 Redis：
- 主机: `localhost:6379` (Python) / `host.docker.internal:6379` (Docker)
- 密码: `redis123456`

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LITELLM_MASTER_KEY` | LiteLLM 管理接口密钥 | `sk-litellm-master-key` |
| `DATABASE_URL` | MySQL 连接 URL | `mysql://root:root123456@localhost:3306/autofill` |
| `REDIS_HOST` | Redis 主机 | `localhost` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `REDIS_PASSWORD` | Redis 密码 | `redis123456` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

---

## 验证服务

### 健康检查

```bash
curl http://localhost:4000/health
```

### 查看模型列表

```bash
curl -H "Authorization: Bearer sk-litellm-master-key" \
  http://localhost:4000/model/info
```

---

## 管理接口

LiteLLM 提供以下管理接口：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/model/new` | POST | 添加新模型 |
| `/model/update` | POST | 更新模型配置 |
| `/model/delete` | DELETE | 删除模型 |
| `/model/info` | GET | 获取模型信息 |
| `/health` | GET | 健康检查 |

所有管理接口需要在请求头中携带 Master Key：
```
Authorization: Bearer sk-litellm-master-key
```

### 示例：添加模型

```bash
curl -X POST http://localhost:4000/model/new \
  -H "Authorization: Bearer sk-litellm-master-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "gpt-4",
    "litellm_params": {
      "model": "openai/gpt-4",
      "api_key": "your-openai-api-key"
    }
  }'
```

---

## 与后端服务集成

后端服务通过以下方式调用 LiteLLM：

1. **代理接口**: 使用 API Key 认证，调用结构化提取接口
2. **管理接口**: 使用 JWT 认证，管理模型配置并同步到 LiteLLM

详见项目文档：`/docs/llm_proxy_api.md`

---

## 常见问题

### 1. Python 启动时报数据库连接错误

确保 MySQL 服务已启动：
```bash
# 检查 MySQL 是否运行
mysql -h localhost -u root -p -e "SELECT 1"
```

### 2. Redis 连接失败

确保 Redis 服务已启动：
```bash
# 检查 Redis 是否运行
redis-cli -h localhost -a redis123456 ping
```

### 3. 端口被占用

如果 4000 端口被占用，可以更换端口：
```bash
litellm --config config.yaml --port 4001 --host 0.0.0.0
```

### 4. Docker 方式无法连接 host 的 MySQL/Redis

确保 `extra_hosts` 配置正确，并且在 Docker 中使用 `host.docker.internal` 作为主机名。

---

## 参考文档

- [LiteLLM 官方文档](https://docs.litellm.com.cn/docs/)
- [LiteLLM Proxy 文档](https://docs.litellm.com.cn/docs/simple_proxy)
- [LiteLLM 配置参考](https://docs.litellm.com.cn/docs/proxy/configs)
