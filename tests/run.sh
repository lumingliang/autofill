#!/bin/bash

# API 测试框架快速启动脚本

cd "$(dirname "$0")"

echo "=========================================="
echo "API 自动化测试框架"
echo "=========================================="
echo ""

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠ 未找到 .env 配置文件"
    echo "正在从 .env.example 创建..."
    cp .env.example .env
    echo "✓ 已创建 .env 文件"
    echo ""
    echo "请编辑 .env 文件配置测试参数"
    echo ""
    echo "主要配置项:"
    echo "  - TEST_BASE_URL: 后端服务地址"
    echo "  - TEST_ADMIN_USERNAME/PASSWORD: 超管账号"
    echo "  - TEST_MODULE_*: 模块开关"
    echo ""
    read -p "是否现在运行测试? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        echo "已退出，请先配置 .env 文件"
        exit 0
    fi
fi

# 检查依赖
echo "检查依赖..."
python3 -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠ 缺少 requests 库，正在安装..."
    pip install requests python-dotenv
    echo "✓ 依赖安装完成"
fi

echo ""
echo "开始运行测试..."
echo ""

# 运行测试
python3 main.py

exit $?
