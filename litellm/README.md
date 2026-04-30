# LiteLLM 网关服务

## 简介

LiteLLM 作为独立的大模型网关服务，统一适配多种模型提供商，为后端服务提供标准化的模型调用接口。

## 目录结构

```
litellm/
├── config.yaml          # LiteLLM 配置文件
├── docker-compose.yml   # Docker Compose 配置
└── README.md           # 说明文档
```

## 配置说明

### 数据库

使用项目现有的 MySQL 数据库：
- 主机: `host.docker.internal:3306`
- 数据库: `autofill`
- 用户名: `root`
- 密码: `root123456`

### 缓存

使用项目现有的 Redis：
- 主机: `host.docker.internal:6379`
- 密码: `redis123456`

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LITELLM_MASTER_KEY` | LiteLLM 管理接口密钥 | `sk-litellm-master-key` |
| `DATABASE_URL` | MySQL 连接 URL | 从 config.toml 读取 |
| `REDIS_HOST` | Redis 主机 | `host.docker.internal` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `REDIS_PASSWORD` | Redis 密码 | 从 config.toml 读取 |

## 启动服务

```bash
cd /Users/lu/code/code/py/autofill/litellm
docker-compose up -d
```

## 查看日志

```bash
docker-compose logs -f litellm
```

## 停止服务

```bash
docker-compose down
```

## 管理接口

LiteLLM 提供以下管理接口：

- `POST /model/new` - 添加新模型
- `POST /model/update` - 更新模型配置
- `DELETE /model/delete` - 删除模型
- `GET /model/info` - 获取模型信息
- `GET /health` - 健康检查

所有管理接口需要在请求头中携带 Master Key：
```
Authorization: Bearer sk-litellm-master-key
```

## 与后端服务集成

后端服务通过以下方式调用 LiteLLM：

1. **代理接口**: 使用 API Key 认证，调用结构化提取接口
2. **管理接口**: 使用 JWT 认证，管理模型配置并同步到 LiteLLM

详见项目文档：`/docs/llm_proxy_api.md`
