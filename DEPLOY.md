# Docker 部署指南

## 快速开始

### 1. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，根据需要修改配置
vim .env
```

### 2. 启动服务

```bash
# 启动所有服务
docker compose up -d

# 或者只启动特定服务
docker compose up -d seekdb
docker compose up -d postgres
docker compose up -d litellm
docker compose up -d app
```

### 3. 查看服务状态

```bash
# 查看所有服务状态
docker compose ps

# 查看服务日志
docker compose logs -f seekdb
docker compose logs -f app

# 查看所有服务日志
docker compose logs -f
```

### 4. 停止服务

```bash
# 停止所有服务
docker compose down

# 停止并删除数据卷（谨慎使用）
docker compose down -v
```

## 配置说明

### 环境变量配置 (.env)

所有配置都通过 `.env` 文件管理，主要配置项包括：

#### 数据库配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `POSTGRES_USER` | PostgreSQL 用户名 | litellm |
| `POSTGRES_PASSWORD` | PostgreSQL 密码 | litellm123456 |
| `POSTGRES_DB` | PostgreSQL 数据库名 | litellm |
| `POSTGRES_PORT` | PostgreSQL 映射端口 | 5332 |
| `SEEKDB_ROOT_PASSWORD` | SeekDB root 密码 | seekdb123456 |
| `SEEKDB_PORT` | SeekDB 映射端口 | 2881 |

#### 应用配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `APP_PORT` | 应用服务端口 | 9999 |
| `APP_DEBUG` | 调试模式 | false |
| `APP_SECRET_KEY` | JWT 密钥 | (请修改) |
| `MYSQL_HOST` | MySQL 主机地址 | host.docker.internal |
| `MYSQL_PASSWORD` | MySQL 密码 | root123456 |
| `REDIS_HOST` | Redis 主机地址 | host.docker.internal |
| `REDIS_PASSWORD` | Redis 密码 | redis123456 |

#### 存储路径配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `POSTGRES_DATA_PATH` | PostgreSQL 数据存储路径 | postgres_data (命名卷) |
| `SEEKDB_DATA_PATH` | SeekDB 数据存储路径 | seekdb_data (命名卷) |
| `UPLOADS_HOST_PATH` | 上传文件存储路径 | ./uploads |
| `LOGS_HOST_PATH` | 日志存储路径 | ./logs |
| `DATA_HOST_PATH` | 数据目录路径 | ./data |

## 数据持久化

### 使用 Docker 命名卷（默认）

数据存储在 Docker 管理的卷中，适合开发环境：

```env
POSTGRES_DATA_PATH=postgres_data
SEEKDB_DATA_PATH=seekdb_data
```

### 使用本地目录映射（推荐生产环境）

数据存储在宿主机指定目录，便于备份和管理：

```env
POSTGRES_DATA_PATH=./data/postgres
SEEKDB_DATA_PATH=./data/seekdb
UPLOADS_HOST_PATH=./data/uploads
LOGS_HOST_PATH=./data/logs
```

创建数据目录：

```bash
mkdir -p data/postgres data/seekdb data/uploads data/logs
```

## 初始化脚本

### PostgreSQL 初始化

将 SQL 脚本放入 `init/postgres/` 目录，容器首次启动时会自动执行：

```bash
cp init/postgres/01-init.sql.example init/postgres/01-init.sql
# 编辑 init/postgres/01-init.sql
```

### SeekDB 初始化

将 SQL 脚本放入 `init/seekdb/init.d/` 目录：

```bash
cp init/seekdb/init.d/01-init-database.sql.example init/seekdb/init.d/01-init-database.sql
# 编辑 init/seekdb/init.d/01-init-database.sql
```

### SeekDB 配置文件

如需自定义 SeekDB 配置：

```bash
cp init/seekdb/seekdb.cnf.example init/seekdb/seekdb.cnf
# 编辑 init/seekdb/seekdb.cnf
```

然后在 `.env` 中启用：

```env
SEEKDB_CONFIG_PATH=./init/seekdb
```

## 服务访问

| 服务 | 地址 | 说明 |
|------|------|------|
| 主应用 | http://localhost:9999 | Web 应用 |
| LiteLLM | http://localhost:4000 | LLM 网关 |
| SeekDB | localhost:2881 | 向量数据库 (MySQL 协议) |
| PostgreSQL | localhost:5332 | 关系数据库 |

## 常用命令

```bash
# 进入容器
docker compose exec app bash
docker compose exec seekdb bash

# 查看容器日志
docker compose logs -f --tail=100 app

# 重启服务
docker compose restart app

# 重建并启动
docker compose up -d --build app

# 查看资源使用
docker stats

# 清理未使用的数据卷
docker volume prune
```

## 故障排查

### 1. 容器无法启动

```bash
# 查看详细日志
docker compose logs seekdb

# 检查配置
docker compose config
```

### 2. 连接数据库失败

```bash
# 测试 SeekDB 连接
mysql -uroot -pseekdb123456 -h127.0.0.1 -P2881 -e "SELECT 1"

# 测试 PostgreSQL 连接
docker compose exec postgres psql -U litellm -d litellm -c "SELECT 1"
```

### 3. 权限问题

确保数据目录有正确的权限：

```bash
# 设置目录权限
chmod -R 755 data/
chown -R 1000:1000 data/  # 根据容器用户调整
```

## 生产环境建议

1. **修改默认密码**：务必修改所有默认密码
2. **使用 HTTPS**：配置反向代理（Nginx/Traefik）启用 HTTPS
3. **定期备份**：配置数据备份策略
4. **资源限制**：为容器设置 CPU 和内存限制
5. **日志收集**：配置集中式日志收集（如 ELK）
6. **监控告警**：配置服务监控和告警

## 网络配置

服务间通过 `autofill-network` 网络通信：

- `app` 服务可以通过服务名访问其他服务：
  - `seekdb:2881` - SeekDB
  - `postgres:5432` - PostgreSQL
  - `litellm:4000` - LiteLLM

- 宿主机服务（MySQL、Redis）通过 `host.docker.internal` 访问
