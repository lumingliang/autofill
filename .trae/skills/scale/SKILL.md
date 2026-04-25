---
name: "scale"
description: "启动、停止、重启前后端项目服务。Invoke when user asks to start, stop, restart, or check status of the development servers."
---

# Scale - 项目服务管理

这个 skill 用于管理项目的前后端服务，通过调用项目根目录下的 `start.sh` 脚本来实现。

## 功能

- **启动服务** (`./start.sh up` 或 `./start.sh start`): 启动前后端服务
- **停止服务** (`./start.sh down` 或 `./start.sh stop`): 停止前后端服务
- **重启服务** (`./start.sh restart`): 重启前后端服务
- **查看状态** (`./start.sh status`): 查看服务运行状态
- **查看日志** (`./start.sh logs [backend|frontend]`): 查看服务日志

## 项目结构

- **后端**: FastAPI 项目，使用 conda 环境，端口 9999
- **前端**: Vue3 + Vite 项目，使用 pnpm/npm，端口 3200
  - 优先使用 `frontend` 目录（新项目）
  - 回退使用 `web` 目录（旧项目）

## 使用方法

当用户想要：
1. 启动项目 → 执行 `./start.sh up`
2. 停止项目 → 执行 `./start.sh down`
3. 重启项目 → 执行 `./start.sh restart`
4. 查看状态 → 执行 `./start.sh status`
5. 查看日志 → 执行 `./start.sh logs backend` 或 `./start.sh logs frontend`

## 注意事项

- 脚本会自动检测并激活 conda 环境（默认环境名为 `autofill`）
- 如果端口被占用，脚本会自动终止占用进程
- 日志文件保存在 `/tmp/autofill_backend.log` 和 `/tmp/autofill_frontend.log`
