---
name: "litellm-gateway"
description: "Manages LiteLLM gateway service lifecycle including start, stop, restart, and status checks. Invoke when user needs to start, stop, restart, or check status of the LiteLLM gateway service."
---

# LiteLLM Gateway Management Skill

## When to Invoke

**CRITICAL: Must invoke this skill when user asks to:**
- Start the LiteLLM gateway service
- Stop the LiteLLM gateway service
- Restart the LiteLLM gateway service
- Check LiteLLM gateway status
- View LiteLLM gateway logs
- Any LiteLLM gateway management operations

## Quick Commands

Use the management script for all operations:

```bash
# 启动服务
./scripts/litellm-gateway.sh start

# 停止服务
./scripts/litellm-gateway.sh stop

# 重启服务
./scripts/litellm-gateway.sh restart

# 查看状态
./scripts/litellm-gateway.sh status

# 查看日志
./scripts/litellm-gateway.sh logs
```

## Configuration

### Default Settings

| Config | Value | Location |
|--------|-------|----------|
| Conda Environment | `dev` | Auto-activated |
| Config File | `litellm/config.yaml` | Project root |
| Port | `4000` | Configurable |
| Host | `0.0.0.0` | Configurable |
| Log File | `logs/litellm-gateway.log` | Auto-created |

### Config File Location

The script uses: `/Users/lu/code/code/py/autofill/litellm/config.yaml`

## Features

### 1. Environment Management

- Automatically checks and activates conda `dev` environment
- Verifies litellm installation
- Validates configuration file exists

### 2. Service Management

**Start:**
- Checks if already running
- Activates conda environment
- Starts service with nohup
- Saves PID to file
- Verifies successful startup

**Stop:**
- Graceful shutdown (SIGTERM)
- Waits up to 10 seconds
- Force kill if needed (SIGKILL)
- Cleans up PID file
- Verifies port release

**Restart:**
- Stops service if running
- Starts service fresh

**Status:**
- Shows running status
- Displays PID and uptime
- Shows service URL
- Performs health check

**Logs:**
- Real-time log streaming
- Uses `tail -f`

## Usage Examples

### Start the Gateway

```bash
./scripts/litellm-gateway.sh start
```

Expected output:
```
=== 启动 LiteLLM 网关服务 ===
✓ 当前环境: dev
✓ 配置文件: /Users/lu/code/code/py/autofill/litellm/config.yaml
正在启动 LiteLLM 网关...
等待服务启动...
✓ LiteLLM 网关启动成功!
  PID: 12345
  地址: http://0.0.0.0:4000
  文档: http://0.0.0.0:4000/docs
```

### Check Status

```bash
./scripts/litellm-gateway.sh status
```

Expected output:
```
=== LiteLLM 网关状态 ===
状态: 运行中
PID: 12345
地址: http://0.0.0.0:4000
启动时间: Mon Jan 1 12:00:00 2024
✓ 健康检查通过

配置信息:
  配置文件: /Users/lu/code/code/py/autofill/litellm/config.yaml
  日志文件: /Users/lu/code/code/py/autofill/logs/litellm-gateway.log
  Conda 环境: dev
```

### View Logs

```bash
./scripts/litellm-gateway.sh logs
```

Press `Ctrl+C` to exit log view.

### Restart After Config Changes

```bash
./scripts/litellm-gateway.sh restart
```

## Troubleshooting

### Port Already in Use

```
错误: 端口 4000 仍被占用
```

**Solution:**
```bash
# Find and kill process using port 4000
lsof -ti:4000 | xargs kill -9

# Then start again
./scripts/litellm-gateway.sh start
```

### Conda Environment Not Found

```
错误: 无法激活 dev 环境
```

**Solution:**
```bash
# Check available environments
conda env list

# Create if missing
conda create -n dev python=3.12

# Install litellm
conda activate dev
pip install litellm
```

### Service Fails to Start

```
✗ 服务启动失败，请检查日志
```

**Solution:**
```bash
# Check logs
./scripts/litellm-gateway.sh logs

# Common issues:
# 1. Database connection failed - check MySQL/Redis
# 2. Config syntax error - validate YAML
# 3. Missing dependencies - pip install litellm
```

## Health Check

The gateway provides a health endpoint:

```bash
curl http://localhost:4000/health
```

Expected response:
```json
{
  "status": "healthy"
}
```

## API Documentation

Once running, access the API docs at:
- Swagger UI: http://localhost:4000/docs
- ReDoc: http://localhost:4000/redoc

## Script Location

`/Users/lu/code/code/py/autofill/scripts/litellm-gateway.sh`

## Important Notes

1. **Always use the script** - Don't start litellm manually to ensure proper environment setup
2. **Check conda environment** - Script automatically activates `dev` environment
3. **Monitor logs** - Use `./scripts/litellm-gateway.sh logs` for troubleshooting
4. **Health checks** - Script automatically verifies service health on start
5. **PID tracking** - Service PID is saved to `/tmp/litellm-gateway.pid`

## Related Files

- Config: `litellm/config.yaml`
- Script: `scripts/litellm-gateway.sh`
- Logs: `logs/litellm-gateway.log`
- Skill: `.trae/skills/litellm-gateway/SKILL.md`
