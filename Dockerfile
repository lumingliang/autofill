# 统一构建镜像 - 基于 Ubuntu 22.04
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

# 使用阿里云镜像源并设置中国时区
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# 安装必要的基础工具
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装 Miniforge (使用南京大学镜像，自动检测架构)
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ]; then \
    wget https://mirrors.nju.edu.cn/github-release/conda-forge/miniforge/LatestRelease/Miniforge3-Linux-aarch64.sh -O /tmp/miniforge.sh; \
    else \
    wget https://mirrors.nju.edu.cn/github-release/conda-forge/miniforge/LatestRelease/Miniforge3-Linux-x86_64.sh -O /tmp/miniforge.sh; \
    fi && \
    bash /tmp/miniforge.sh -b -p /opt/miniforge && \
    rm /tmp/miniforge.sh

# 设置 conda 环境变量
ENV PATH=/opt/miniforge/bin:$PATH

# 配置 conda 使用官方源（ARM64架构国内镜像支持不完善）
RUN conda config --set show_channel_urls true

# 创建 Python 3.12 + Node.js 20 环境
RUN conda create -n app python=3.12 nodejs=20 -y && \
    conda clean -afy

# 设置激活环境的变量
ENV CONDA_DEFAULT_ENV=app
ENV PATH=/opt/miniforge/envs/app/bin:$PATH

# 配置 npm 使用阿里云镜像
RUN npm config set registry https://registry.npmmirror.com

# 设置 pip 使用阿里云镜像
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 设置工作目录
WORKDIR /app

# 复制后端依赖文件
COPY requirements.txt ./
COPY pyproject.toml ./

# 安装 Python 依赖
RUN pip install -r requirements.txt

# 复制前端依赖文件
COPY frontend/package*.json ./frontend/

# 安装前端依赖
WORKDIR /app/frontend
RUN npm install

# 复制前端源代码并构建
WORKDIR /app
COPY frontend/ ./frontend/
WORKDIR /app/frontend
# 设置 DOCKER_BUILD 环境变量，使 vite.config.ts 中的 base 路径设置为 '/web/'
ENV DOCKER_BUILD=true
RUN npm run build

# 回到应用根目录
WORKDIR /app

# 复制后端源代码
COPY . .

# 创建必要的目录
RUN mkdir -p uploads logs web

# 复制前端构建结果到 web 目录
RUN cp -r frontend/dist/* web/

# 暴露端口
EXPOSE 9999

# 启动命令
CMD ["python", "run.py"]
