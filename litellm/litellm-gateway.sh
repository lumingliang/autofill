#!/bin/bash
# LiteLLM 网关管理脚本
# 功能：启动、停止、重启、查看状态

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
CONDA_ENV="dev"
LITELLM_CONFIG="/Users/lu/code/code/py/autofill/litellm/config.yaml"
LITELLM_PORT=4000
LITELLM_HOST="0.0.0.0"
PID_FILE="/tmp/litellm-gateway.pid"
LOG_FILE="/Users/lu/code/code/py/autofill/logs/litellm-gateway.log"

# 确保日志目录存在
mkdir -p "$(dirname "$LOG_FILE")"

# 帮助信息
show_help() {
    echo -e "${BLUE}LiteLLM 网关管理脚本${NC}"
    echo ""
    echo "用法: $0 {start|stop|restart|status|logs}"
    echo ""
    echo "命令:"
    echo "  start    - 启动 LiteLLM 网关服务"
    echo "  stop     - 停止 LiteLLM 网关服务"
    echo "  restart  - 重启 LiteLLM 网关服务"
    echo "  status   - 查看服务状态"
    echo "  logs     - 查看实时日志"
    echo ""
    echo "配置:"
    echo "  配置文件: $LITELLM_CONFIG"
    echo "  服务地址: $LITELLM_HOST:$LITELLM_PORT"
    echo "  Conda 环境: $CONDA_ENV"
}

# 检查是否在 conda 环境中
check_conda_env() {
    if [[ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV" ]]; then
        echo -e "${YELLOW}警告: 当前不在 $CONDA_ENV 环境中${NC}"
        echo -e "${YELLOW}正在尝试激活 $CONDA_ENV 环境...${NC}"
        
        # 尝试激活环境
        if command -v conda &> /dev/null; then
            eval "$(conda shell.bash hook)"
            conda activate "$CONDA_ENV"
        else
            echo -e "${RED}错误: 无法找到 conda 命令${NC}"
            exit 1
        fi
        
        # 再次检查
        if [[ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV" ]]; then
            echo -e "${RED}错误: 无法激活 $CONDA_ENV 环境${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✓ 当前环境: $CONDA_DEFAULT_ENV${NC}"
}

# 检查配置文件
check_config() {
    if [[ ! -f "$LITELLM_CONFIG" ]]; then
        echo -e "${RED}错误: 配置文件不存在: $LITELLM_CONFIG${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ 配置文件: $LITELLM_CONFIG${NC}"
}

# 检查端口是否被占用
check_port() {
    if lsof -Pi :"$LITELLM_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 获取进程 ID
get_pid() {
    if [[ -f "$PID_FILE" ]]; then
        cat "$PID_FILE"
    else
        # 尝试从端口查找
        lsof -Pi :"$LITELLM_PORT" -sTCP:LISTEN -t 2>/dev/null || echo ""
    fi
}

# 启动服务
start_service() {
    echo -e "${BLUE}=== 启动 LiteLLM 网关服务 ===${NC}"
    
    # 检查环境
    check_conda_env
    check_config
    
    # 检查是否已在运行
    if check_port; then
        PID=$(get_pid)
        echo -e "${YELLOW}服务已在运行 (PID: $PID)${NC}"
        echo -e "${YELLOW}如需重启，请使用: $0 restart${NC}"
        return 0
    fi
    
    # 检查 litellm 是否安装
    if ! command -v litellm &> /dev/null; then
        echo -e "${RED}错误: litellm 命令未找到${NC}"
        echo -e "${YELLOW}请先安装: pip install litellm${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}正在启动 LiteLLM 网关...${NC}"
    echo -e "${BLUE}配置文件: $LITELLM_CONFIG${NC}"
    echo -e "${BLUE}日志文件: $LOG_FILE${NC}"
    
    # 等待端口释放（避免重启时端口占用）
    echo -e "${BLUE}检查端口可用性...${NC}"
    for i in {1..5}; do
        if ! check_port; then
            break
        fi
        echo -e "${YELLOW}等待端口释放... ($i/5)${NC}"
        sleep 1
    done
    
    # 启动服务
    nohup litellm --config "$LITELLM_CONFIG" >> "$LOG_FILE" 2>&1 &
    PID=$!
    
    # 保存 PID
    echo $PID > "$PID_FILE"
    
    echo -e "${BLUE}等待服务启动 (PID: $PID)...${NC}"
    sleep 3
    
    # 检查进程是否存在
    if ! kill -0 $PID 2>/dev/null; then
        echo -e "${RED}✗ 服务进程已退出${NC}"
        echo -e "${RED}日志文件: $LOG_FILE${NC}"
        rm -f "$PID_FILE"
        exit 1
    fi
    
    # 检查端口是否监听
    if check_port; then
        echo -e "${GREEN}✓ LiteLLM 网关启动成功!${NC}"
        echo -e "${GREEN}  PID: $PID${NC}"
        echo -e "${GREEN}  地址: http://$LITELLM_HOST:$LITELLM_PORT${NC}"
        echo -e "${GREEN}  文档: http://$LITELLM_HOST:$LITELLM_PORT/docs${NC}"
        echo ""
        echo -e "${BLUE}查看日志: $0 logs${NC}"
    else
        echo -e "${YELLOW}! 服务正在启动中，端口尚未监听${NC}"
        echo -e "${YELLOW}  PID: $PID${NC}"
        echo -e "${YELLOW}  请稍后使用 '$0 status' 检查状态${NC}"
        echo -e "${BLUE}查看日志: $0 logs${NC}"
    fi
}

# 停止服务
stop_service() {
    echo -e "${BLUE}=== 停止 LiteLLM 网关服务 ===${NC}"
    
    PID=$(get_pid)
    
    if [[ -z "$PID" ]]; then
        echo -e "${YELLOW}服务未在运行${NC}"
        return 0
    fi
    
    echo -e "${BLUE}正在停止服务 (PID: $PID)...${NC}"
    
    # 尝试优雅停止
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
        
        # 等待进程结束
        for i in {1..10}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                break
            fi
            echo -e "${BLUE}等待服务停止... ($i/10)${NC}"
            sleep 1
        done
        
        # 强制终止
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${YELLOW}强制终止进程...${NC}"
            kill -9 "$PID" 2>/dev/null || true
        fi
    fi
    
    # 清理 PID 文件
    rm -f "$PID_FILE"
    
    # 检查端口是否释放
    if check_port; then
        echo -e "${RED}✗ 端口 $LITELLM_PORT 仍被占用${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ 服务已停止${NC}"
    fi
}

# 重启服务
restart_service() {
    echo -e "${BLUE}=== 重启 LiteLLM 网关服务 ===${NC}"
    stop_service
    echo ""
    start_service
}

# 查看状态
show_status() {
    echo -e "${BLUE}=== LiteLLM 网关状态 ===${NC}"
    
    PID=$(get_pid)
    
    if check_port; then
        echo -e "${GREEN}状态: 运行中${NC}"
        echo -e "${GREEN}PID: $PID${NC}"
        echo -e "${GREEN}地址: http://$LITELLM_HOST:$LITELLM_PORT${NC}"
        
        # 显示运行时间
        if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
            START_TIME=$(ps -o lstart= -p "$PID" 2>/dev/null || echo "未知")
            echo -e "${GREEN}启动时间: $START_TIME${NC}"
        fi
        
        # 检查健康状态
        echo -e "${BLUE}检查健康状态...${NC}"
        if curl -s "http://$LITELLM_HOST:$LITELLM_PORT/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ 健康检查通过${NC}"
        else
            echo -e "${YELLOW}! 健康检查未响应${NC}"
        fi
    else
        echo -e "${YELLOW}状态: 未运行${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}配置信息:${NC}"
    echo -e "  配置文件: $LITELLM_CONFIG"
    echo -e "  日志文件: $LOG_FILE"
    echo -e "  Conda 环境: $CONDA_ENV"
}

# 查看日志
show_logs() {
    echo -e "${BLUE}=== LiteLLM 网关日志 ===${NC}"
    
    if [[ ! -f "$LOG_FILE" ]]; then
        echo -e "${YELLOW}日志文件不存在: $LOG_FILE${NC}"
        return 0
    fi
    
    echo -e "${BLUE}按 Ctrl+C 退出日志查看${NC}"
    echo ""
    
    # 使用 tail -f 实时查看
    tail -f "$LOG_FILE"
}

# 主程序
case "${1:-}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    *)
        show_help
        exit 1
        ;;
esac
