#!/bin/bash
# =============================================================================
# Docker Compose 快速启动脚本
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
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

# 检查 .env 文件
check_env() {
    if [ ! -f .env ]; then
        log_warn ".env 文件不存在，正在从模板创建..."
        cp .env.example .env
        log_success ".env 文件已创建，请根据需要修改配置"
        echo ""
        log_info "默认配置如下："
        grep -E "^[A-Z].*=" .env | head -20
        echo ""
        read -p "是否继续启动? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "已取消启动，请编辑 .env 文件后重新运行"
            exit 0
        fi
    fi
}

# 检查 Docker 和 Docker Compose
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    # 检查 Docker 是否运行
    if ! docker info &> /dev/null; then
        log_error "Docker 未运行，请启动 Docker"
        exit 1
    fi

    log_success "Docker 环境检查通过"
}

# 创建必要的目录
create_dirs() {
    log_info "创建必要的目录..."
    mkdir -p uploads logs data/postgres data/seekdb
    log_success "目录创建完成"
}

# 启动服务
start_services() {
    log_info "正在启动服务..."
    
    # 根据参数决定启动哪些服务
    if [ -z "$1" ]; then
        docker compose up -d
    else
        docker compose up -d "$1"
    fi
    
    log_success "服务启动命令已执行"
}

# 等待服务健康检查
wait_for_healthy() {
    log_info "等待服务健康检查..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local status=$(docker compose ps --format json 2>/dev/null | grep -c "healthy" || echo "0")
        local total=$(docker compose ps --format json 2>/dev/null | wc -l || echo "0")
        
        if [ "$status" -eq "$total" ] && [ "$total" -gt 0 ]; then
            log_success "所有服务已就绪"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo ""
    log_warn "服务启动可能需要更多时间，请稍后检查状态"
    return 1
}

# 显示服务状态
show_status() {
    echo ""
    log_info "服务状态："
    docker compose ps
    echo ""
    log_info "访问地址："
    echo "  - 主应用:    http://localhost:9999"
    echo "  - LiteLLM:   http://localhost:4000"
    echo "  - SeekDB:    localhost:2881"
    echo "  - PostgreSQL: localhost:5332"
}

# 显示帮助信息
show_help() {
    cat << EOF
Docker Compose 快速启动脚本

用法: $0 [选项] [服务名]

选项:
    -h, --help      显示帮助信息
    -s, --status    查看服务状态
    -l, --logs      查看日志
    -d, --down      停止服务
    -v, --volume    停止服务并删除数据卷

服务名:
    seekdb          只启动 SeekDB
    postgres        只启动 PostgreSQL
    litellm         只启动 LiteLLM
    app             只启动主应用

示例:
    $0              启动所有服务
    $0 seekdb       只启动 SeekDB
    $0 -s           查看服务状态
    $0 -l app       查看主应用日志
EOF
}

# 主函数
main() {
    case "${1:-}" in
        -h|--help)
            show_help
            exit 0
            ;;
        -s|--status)
            show_status
            exit 0
            ;;
        -d|--down)
            log_info "正在停止服务..."
            docker compose down
            log_success "服务已停止"
            exit 0
            ;;
        -v|--volume)
            log_warn "正在停止服务并删除数据卷..."
            read -p "确定要删除所有数据吗? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                docker compose down -v
                log_success "服务和数据卷已删除"
            else
                log_info "已取消"
            fi
            exit 0
            ;;
        -l|--logs)
            if [ -n "$2" ]; then
                docker compose logs -f "$2"
            else
                docker compose logs -f
            fi
            exit 0
            ;;
    esac

    # 正常启动流程
    echo "================================"
    echo "  Autofill Docker 启动脚本"
    echo "================================"
    echo ""

    check_docker
    check_env
    create_dirs
    start_services "$1"
    wait_for_healthy
    show_status

    echo ""
    log_success "启动完成！"
    echo ""
    log_info "常用命令："
    echo "  查看日志:    $0 -l [服务名]"
    echo "  查看状态:    $0 -s"
    echo "  停止服务:    $0 -d"
    echo "  查看帮助:    $0 -h"
}

# 运行主函数
main "$@"
