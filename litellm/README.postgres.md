# LiteLLM with PostgreSQL

使用 PostgreSQL 作为 LiteLLM 的数据库后端的 Docker Compose 配置。

## 配置说明

### 数据库凭据

| 配置项 | 值 |
|--------|-----|
| 数据库类型 | PostgreSQL 16 |
| 用户名 | litellm |
| 密码 | litellm123456 |
| 数据库名 | litellm |
| 端口 | 5432 |
| 主机 | postgres (Docker 网络内) |

## 使用步骤

### 1. 停止旧服务

如果之前使用过 MySQL 版本的 LiteLLM，请先停止：

```bash
cd /Users/lu/code/code/py/autofill/litellm
./litellm-gateway.sh stop
```

### 2. 启动 PostgreSQL 版本

使用 PostgreSQL 的 Docker Compose 文件：

```bash
cd /Users/lu/code/code/py/autofill/litellm
docker compose -f docker-compose.postgres.yml up -d
```

或者创建一个简化的启动脚本：

```bash
# 创建启动脚本
cat > /Users/lu/code/code/py/autofill/litellm/start-postgres.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "=== 启动 LiteLLM + PostgreSQL ==="
docker compose -f docker-compose.postgres.yml up -d
echo "等待服务启动..."
sleep 5
docker compose -f docker-compose.postgres.yml ps
echo ""
echo "=== 查看日志 ==="
echo "docker compose -f docker-compose.postgres.yml logs -f"
EOF
chmod +x start-postgres.sh

# 运行启动脚本
./start-postgres.sh
```

### 3. 查看服务状态

```bash
# 查看服务状态
docker compose -f docker-compose.postgres.yml ps

# 查看日志
docker compose -f docker-compose.postgres.yml logs -f

# 单独查看 PostgreSQL 日志
docker compose -f docker-compose.postgres.yml logs -f postgres

# 单独查看 LiteLLM 日志
docker compose -f docker-compose.postgres.yml logs -f litellm
```

### 4. 验证服务

```bash
# 测试 PostgreSQL 连接
docker compose -f docker-compose.postgres.yml exec postgres psql -U litellm -d litellm -c "SELECT version();"

# 测试 LiteLLM 健康检查
curl http://localhost:4000/health

# 访问 API 文档
open http://localhost:4000/docs
```

### 5. 停止服务

```bash
# 停止服务（保留数据）
docker compose -f docker-compose.postgres.yml stop

# 完全停止并删除容器（保留数据卷）
docker compose -f docker-compose.postgres.yml down

# 完全清理（删除数据卷）
docker compose -f docker-compose.postgres.yml down -v
```

## 数据管理

### 备份数据库

```bash
# 创建备份目录
mkdir -p /Users/lu/code/code/py/autofill/litellm/backups

# 备份数据库
docker compose -f docker-compose.postgres.yml exec -T postgres pg_dump -U litellm litellm > /Users/lu/code/code/py/autofill/litellm/backups/litellm-$(date +%Y%m%d_%H%M%S).sql
```

### 恢复数据库

```bash
# 从备份恢复
docker compose -f docker-compose.postgres.yml exec -T postgres psql -U litellm -d litellm < /path/to/backup.sql
```

### 查看数据

```bash
# 连接到 PostgreSQL
docker compose -f docker-compose.postgres.yml exec postgres psql -U litellm -d litellm

# 查看所有表
docker compose -f docker-compose.postgres.yml exec postgres psql -U litellm -d litellm -c "\\dt"
```

## 架构说明

### 服务组件

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| postgres | postgres:16-alpine | 5432 | PostgreSQL 数据库 |
| litellm | ghcr.io/berriai/litellm:main-latest | 4000 | LiteLLM 网关 |

### 网络配置

- Docker 网络：`litellm-network`
- 服务间通信通过 Docker 网络：`postgres:5432`
- 宿主机访问 PostgreSQL：`localhost:5432`
- 宿主机访问 LiteLLM：`localhost:4000`

### 数据持久化

- PostgreSQL 数据：`postgres-data` volume
- 数据卷由 Docker 自动管理
- 即使容器被删除，数据仍保留

## 常见问题

### 端口被占用

如果 5432 端口被占用，修改 `docker-compose.postgres.yml`：

```yaml
ports:
  - "5433:5432"  # 改为 5433
```

### 密码修改

修改 `docker-compose.postgres.yml` 中的环境变量：

```yaml
environment:
  - POSTGRES_USER=litellm
  - POSTGRES_PASSWORD=your-new-password
  - DATABASE_URL=postgresql://litellm:your-new-password@postgres:5432/litellm
```

### 连接到现有 PostgreSQL

如果你已经有 PostgreSQL 实例，修改连接字符串：

```yaml
environment:
  - DATABASE_URL=postgresql://user:password@your-postgres-host:5432/dbname
```

## 快速开始

```bash
# 1. 进入目录
cd /Users/lu/code/code/py/autofill/litellm

# 2. 启动服务
docker compose -f docker-compose.postgres.yml up -d

# 3. 等待启动完成（约 10 秒）
sleep 10

# 4. 查看状态
docker compose -f docker-compose.postgres.yml ps

# 5. 测试访问
curl http://localhost:4000/health
```
