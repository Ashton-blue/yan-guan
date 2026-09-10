FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY backend/ .

# 创建日志目录
RUN mkdir -p /app/logs

# Zeabur 通过环境变量强制注入 PORT=8080；默认值兜底同样为 8080
ENV PORT=8080
EXPOSE 8080

# 启动命令（shell 形式以便展开 $PORT；Zeabur 注入 PORT=8080）
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
