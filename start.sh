#!/bin/bash
#
# start.sh - 启动/重启前后端项目脚本
# 用法: ./start.sh [up|down|restart|status]
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$PROJECT_DIR/web"
BACKEND_PID_FILE="/tmp/autofill_backend.pid"
FRONTEND_PID_FILE="/tmp/autofill_frontend.pid"
BACKEND_PORT=9999
FRONTEND_PORT=3000

# Conda 配置
CONDA_ENV="autofill"  # 默认 conda 环境名，可根据需要修改

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 conda 是否安装
check_conda() {
    if ! command -v conda &> /dev/null; then
        log_error "conda 未安装，请先安装 Anaconda 或 Miniconda"
        exit 1
    fi
}

# 获取 conda 的 shell 钩子
get_conda_hook() {
    # 尝试不同的 conda 初始化方式
    if [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        echo "$HOME/anaconda3/etc/profile.d/conda.sh"
    elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        echo "$HOME/miniconda3/etc/profile.d/conda.sh"
    elif [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
        echo "/opt/anaconda3/etc/profile.d/conda.sh"
    elif [ -f "/opt/miniconda3/etc/profile.d/conda.sh" ]; then
        echo "/opt/miniconda3/etc/profile.d/conda.sh"
    else
        echo ""
    fi
}

# 激活 conda 环境
activate_conda_env() {
    local conda_hook=$(get_conda_hook)
    if [ -n "$conda_hook" ]; then
        source "$conda_hook"
        conda activate "$CONDA_ENV"
    else
        # 尝试直接激活
        eval "$(conda shell.bash hook)"
        conda activate "$CONDA_ENV"
    fi
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 获取占用端口的进程 PID
get_pid_by_port() {
    local port=$1
    lsof -Pi :"$port" -sTCP:LISTEN -t 2>/dev/null | head -1
}

# 保存 PID 到文件
save_pid() {
    local pid=$1
    local pid_file=$2
    echo "$pid" > "$pid_file"
}

# 读取 PID 文件
read_pid() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        cat "$pid_file"
    else
        echo ""
    fi
}

# 检查进程是否存在
check_process() {
    local pid=$1
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# 启动后端
start_backend() {
    log_info "启动后端服务..."
    
    # 检查端口是否被占用
    if check_port "$BACKEND_PORT"; then
        local existing_pid=$(get_pid_by_port "$BACKEND_PORT")
        log_warn "端口 $BACKEND_PORT 已被占用 (PID: $existing_pid)"
        log_info "尝试停止现有进程..."
        kill -9 "$existing_pid" 2>/dev/null || true
        sleep 1
    fi
    
    # 激活 conda 环境并启动后端
    (
        cd "$PROJECT_DIR"
        check_conda
        activate_conda_env
        
        log_info "使用 conda 环境: $CONDA_ENV"
        log_info "启动 FastAPI 服务 (端口: $BACKEND_PORT)..."
        
        python run.py &
        local pid=$!
        save_pid "$pid" "$BACKEND_PID_FILE"

        # 等待服务启动
        local count=0
        while ! check_port "$BACKEND_PORT" && [ $count -lt 30 ]; do
            sleep 1
            count=$((count + 1))
        done

        if check_port "$BACKEND_PORT"; then
            log_success "后端服务已启动 (PID: $pid, 端口: $BACKEND_PORT)"
        else
            log_error "后端服务启动失败，请检查日志: ./logs/app.log"
            exit 1
        fi
    )
}

# 启动前端
start_frontend() {
    log_info "启动前端服务..."
    
    # 检查是否在正确的目录
    if [ ! -d "$WEB_DIR" ]; then
        log_error "前端目录不存在: $WEB_DIR"
        exit 1
    fi
    
    # 检查 node_modules 是否存在
    if [ ! -d "$WEB_DIR/node_modules" ]; then
        log_warn "node_modules 不存在，正在安装依赖..."
        (
            cd "$WEB_DIR"
            if command -v pnpm &> /dev/null; then
                pnpm install
            elif command -v npm &> /dev/null; then
                npm install
            else
                log_error "未找到 pnpm 或 npm，请先安装 Node.js 包管理器"
                exit 1
            fi
        )
    fi
    
    (
        cd "$WEB_DIR"
        
        log_info "启动 Vite 开发服务器..."
        
        if command -v pnpm &> /dev/null; then
            pnpm dev > /tmp/autofill_frontend.log 2>&1 &
        elif command -v npm &> /dev/null; then
            npm run dev > /tmp/autofill_frontend.log 2>&1 &
        else
            log_error "未找到 pnpm 或 npm"
            exit 1
        fi
        
        local pid=$!
        save_pid "$pid" "$FRONTEND_PID_FILE"
        
        # 等待服务启动
        local count=0
        while ! check_port "$FRONTEND_PORT" && [ $count -lt 30 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        if check_port "$FRONTEND_PORT"; then
            log_success "前端服务已启动 (PID: $pid, 端口: $FRONTEND_PORT)"
        else
            log_warn "前端服务可能启动较慢，请稍后检查: http://localhost:$FRONTEND_PORT"
        fi
    )
}

# 停止后端
stop_backend() {
    log_info "停止后端服务..."
    
    local pid=$(read_pid "$BACKEND_PID_FILE")
    local stopped=false
    
    # 尝试通过 PID 文件停止
    if [ -n "$pid" ] && check_process "$pid"; then
        kill -9 "$pid" 2>/dev/null || true
        stopped=true
    fi
    
    # 尝试通过端口查找并停止
    if check_port "$BACKEND_PORT"; then
        local port_pid=$(get_pid_by_port "$BACKEND_PORT")
        if [ -n "$port_pid" ]; then
            kill -9 "$port_pid" 2>/dev/null || true
            stopped=true
        fi
    fi
    
    rm -f "$BACKEND_PID_FILE"
    
    if [ "$stopped" = true ]; then
        log_success "后端服务已停止"
    else
        log_warn "后端服务未运行"
    fi
}

# 停止前端
stop_frontend() {
    log_info "停止前端服务..."
    
    local pid=$(read_pid "$FRONTEND_PID_FILE")
    local stopped=false
    
    # 尝试通过 PID 文件停止
    if [ -n "$pid" ] && check_process "$pid"; then
        kill -9 "$pid" 2>/dev/null || true
        stopped=true
    fi
    
    # 尝试查找 vite 进程并停止
    local vite_pids=$(pgrep -f "vite" | grep -v grep | xargs)
    if [ -n "$vite_pids" ]; then
        for vite_pid in $vite_pids; do
            # 检查是否是当前项目的 vite
            if ps -p "$vite_pid" -o command= | grep -q "$WEB_DIR"; then
                kill -9 "$vite_pid" 2>/dev/null || true
                stopped=true
            fi
        done
    fi
    
    rm -f "$FRONTEND_PID_FILE"
    
    if [ "$stopped" = true ]; then
        log_success "前端服务已停止"
    else
        log_warn "前端服务未运行"
    fi
}

# 查看状态
show_status() {
    log_info "服务状态:"
    echo ""
    
    # 后端状态
    local backend_running=false
    local backend_pid=$(read_pid "$BACKEND_PID_FILE")
    if check_port "$BACKEND_PORT"; then
        backend_running=true
        local actual_pid=$(get_pid_by_port "$BACKEND_PORT")
        echo -e "  后端: ${GREEN}运行中${NC} (PID: $actual_pid, 端口: $BACKEND_PORT)"
    elif [ -n "$backend_pid" ] && check_process "$backend_pid"; then
        backend_running=true
        echo -e "  后端: ${GREEN}运行中${NC} (PID: $backend_pid, 端口: $BACKEND_PORT)"
    else
        echo -e "  后端: ${RED}未运行${NC}"
    fi
    
    # 前端状态
    local frontend_running=false
    local frontend_pid=$(read_pid "$FRONTEND_PID_FILE")
    if check_port "$FRONTEND_PORT"; then
        frontend_running=true
        local actual_pid=$(get_pid_by_port "$FRONTEND_PORT")
        echo -e "  前端: ${GREEN}运行中${NC} (PID: $actual_pid, 端口: $FRONTEND_PORT)"
    elif [ -n "$frontend_pid" ] && check_process "$frontend_pid"; then
        frontend_running=true
        echo -e "  前端: ${GREEN}运行中${NC} (PID: $frontend_pid)"
    else
        echo -e "  前端: ${RED}未运行${NC}"
    fi
    
    echo ""
    if [ "$backend_running" = true ] && [ "$frontend_running" = true ]; then
        log_success "所有服务正常运行"
        echo ""
        echo "  前端访问: http://localhost:$FRONTEND_PORT"
        echo "  后端访问: http://localhost:$BACKEND_PORT"
    fi
}

# 查看日志
show_logs() {
    local service=$1
    
    case "$service" in
        backend|be)
            if [ -f /tmp/autofill_backend.log ]; then
                tail -f /tmp/autofill_backend.log
            else
                log_error "后端日志不存在"
            fi
            ;;
        frontend|fe)
            if [ -f /tmp/autofill_frontend.log ]; then
                tail -f /tmp/autofill_frontend.log
            else
                log_error "前端日志不存在"
            fi
            ;;
        *)
            log_error "用法: ./start.sh logs [backend|frontend]"
            exit 1
            ;;
    esac
}

# 启动所有服务
start_all() {
    log_info "启动所有服务..."
    echo ""
    start_backend
    echo ""
    start_frontend
    echo ""
    log_success "所有服务启动完成！"
    echo ""
    echo "  前端访问: http://localhost:$FRONTEND_PORT"
    echo "  后端访问: http://localhost:$BACKEND_PORT"
    echo ""
    echo "查看日志:"
    echo "  ./start.sh logs backend  - 查看后端日志"
    echo "  ./start.sh logs frontend - 查看前端日志"
}

# 停止所有服务
stop_all() {
    log_info "停止所有服务..."
    echo ""
    stop_frontend
    stop_backend
    echo ""
    log_success "所有服务已停止"
}

# 重启所有服务
restart_all() {
    log_info "重启所有服务..."
    echo ""
    stop_all
    echo ""
    sleep 2
    start_all
}

# 显示帮助
show_help() {
    echo "用法: ./start.sh [命令]"
    echo ""
    echo "命令:"
    echo "  up, start       启动前后端服务"
    echo "  down, stop      停止前后端服务"
    echo "  restart, r      重启前后端服务"
    echo "  status, s       查看服务状态"
    echo "  logs [服务]     查看日志 (backend|frontend)"
    echo "  help, h         显示帮助信息"
    echo ""
    echo "示例:"
    echo "  ./start.sh up              # 启动所有服务"
    echo "  ./start.sh restart         # 重启所有服务"
    echo "  ./start.sh status          # 查看服务状态"
    echo "  ./start.sh logs backend    # 查看后端日志"
}

# 主函数
main() {
    case "${1:-}" in
        up|start)
            start_all
            ;;
        down|stop)
            stop_all
            ;;
        restart|r)
            restart_all
            ;;
        status|s)
            show_status
            ;;
        logs)
            show_logs "$2"
            ;;
        help|h|--help|-h)
            show_help
            ;;
        *)
            show_help
            exit 1
            ;;
    esac
}

main "$@"
