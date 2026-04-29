# 开发环境配置总结

## 概述

本文档记录了本机开发环境的清理和重新配置过程，使用 Miniforge 统一管理 Python、Go、Node.js 等开发工具，并配置国内镜像源以加速下载。

---

## 1. 环境清理

### 1.1 删除的内容

| 工具 | 删除的目录/文件 |
|------|----------------|
| Conda/Miniconda | `/opt/homebrew/Caskroom/miniconda`, `~/.conda`, `~/.condarc` |
| SDKMAN | `~/.sdkman` |
| goenv | `~/.goenv` |
| NVM/Node.js/npm | `~/.nvm`, `~/.npm`, `~/.node-gyp`, `~/.npmrc` |
| Miniforge (旧) | `~/miniforge3` |

### 1.2 清理的 Shell 配置

从以下文件中删除了相关环境变量和初始化代码：
- `~/.zshrc`
- `~/.bashrc`
- `~/.bash_profile`
- `~/.profile`

---

## 2. Miniforge 安装与配置

### 2.1 安装

使用南京大学镜像源下载安装包：
```bash
# 下载安装包
curl -L -o ~/Miniforge3-26.1.1-3-MacOSX-arm64.sh \
  "https://mirror.nju.edu.cn/github-release/conda-forge/miniforge/LatestRelease/Miniforge3-26.1.1-3-MacOSX-arm64.sh"

# 安装到用户目录
bash ~/Miniforge3-26.1.1-3-MacOSX-arm64.sh -b -p "$HOME/miniforge3"
```

### 2.2 初始化 Shell

```bash
~/miniforge3/bin/conda init zsh bash
```

### 2.3 配置国内镜像源

```bash
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/
conda config --set show_channel_urls yes
```

---

## 3. Dev 环境创建

### 3.1 创建环境

```bash
mamba create -n dev -y
```

### 3.2 安装开发工具

```bash
mamba install -n dev go nodejs python -y
```

### 3.3 安装的版本

| 工具 | 版本 |
|------|------|
| Go | 1.26.2 |
| Node.js | 25.8.2 |
| Python | 3.14.4 |
| npm | 随 Node.js 一起安装 |

---

## 4. 国内源配置

### 4.1 npm 配置

```bash
npm config set registry https://registry.npmmirror.com
```

### 4.2 Go 配置

```bash
go env -w GOPROXY=https://goproxy.cn,direct
go env -w GOSUMDB=sum.golang.google.cn
```

### 4.3 pip 配置

创建 `~/.pip/pip.conf`：
```ini
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
```

---

## 5. 快捷命令与自动激活

### 5.1 别名配置

在 `~/.zshrc` 和 `~/.bashrc` 中添加了别名：

```bash
# Dev environment activation
alias dev='conda activate dev'
```

### 5.2 自动激活 Dev 环境

配置默认打开终端时自动激活 `dev` 环境，在 `~/.zshrc` 和 `~/.bashrc` 末尾添加：

```bash
# Auto activate dev environment
conda activate dev 2>/dev/null || true
```

**说明**：
- `2>/dev/null || true` 确保即使 conda 未初始化也不会报错
- 打开新终端时会自动进入 `dev` 环境
- 如需退出，可运行 `conda deactivate`

---

## 6. 使用指南

### 6.1 激活 Dev 环境

**自动激活**：由于已配置自动激活，打开新终端时会自动进入 `dev` 环境。

**手动激活**（如已退出环境）：
```bash
# 方式一：使用 conda 命令
conda activate dev

# 方式二：使用别名
dev
```

### 6.2 验证安装

```bash
# 检查 Go
go version

# 检查 Node.js
node --version

# 检查 npm
npm --version

# 检查 Python
python --version
```

### 6.3 退出环境

```bash
conda deactivate
```

---

## 7. 镜像源汇总

| 工具 | 国内镜像地址 |
|------|-------------|
| Conda | https://mirrors.tuna.tsinghua.edu.cn/anaconda/ |
| npm | https://registry.npmmirror.com |
| Go Proxy | https://goproxy.cn |
| pip | https://pypi.tuna.tsinghua.edu.cn/simple |

---

## 8. 注意事项

1. **重启终端**：配置完成后，请关闭并重新打开终端，或运行 `source ~/.zshrc` 使配置生效。

2. **环境隔离**：所有开发工具都安装在 `dev` 环境中，不会影响系统环境。

3. **自动激活**：已配置打开终端时自动激活 `dev` 环境，无需手动激活。如需禁用，请删除 `~/.zshrc` 和 `~/.bashrc` 中的 `conda activate dev` 行。

4. **安装包位置**：Miniforge 安装在 `~/miniforge3`，`dev` 环境位于 `~/miniforge3/envs/dev`。

---

## 9. 相关文件

- Miniforge 安装包：`~/Miniforge3-26.1.1-3-MacOSX-arm64.sh`
- Conda 配置：`~/.condarc`
- pip 配置：`~/.pip/pip.conf`
- npm 配置：`~/.npmrc`
- Shell 配置：`~/.zshrc`, `~/.bashrc`

---

*文档生成时间：2026-04-28*
