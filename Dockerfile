FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai 

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple uv

# 拷贝项目
COPY . .

# 安装依赖到系统环境（关键）
RUN uv pip install --system -e .

# 创建日志目录
RUN mkdir -p /app/logs

# 下载 supercronic
RUN curl -fsSLO https://github.com/aptible/supercronic/releases/latest/download/supercronic-linux-amd64 \
    && chmod +x supercronic-linux-amd64 \
    && mv supercronic-linux-amd64 /usr/local/bin/supercronic

# 启动 cron
CMD ["supercronic", "/app/crontab"]