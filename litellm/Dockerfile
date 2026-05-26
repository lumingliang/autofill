# LiteLLM Dockerfile - 使用 Python 安装
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    openssl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# 安装 LiteLLM 和数据库依赖
RUN pip install --no-cache-dir litellm[proxy] prisma

# 复制配置文件
COPY config.yaml /app/config.yaml

# 暴露端口
EXPOSE 4000

# 启动命令 - 使用环境变量DATABASE_URL
CMD ["sh", "-c", "prisma generate && litellm --config /app/config.yaml --port 4000 --host 0.0.0.0"]
