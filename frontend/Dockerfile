FROM node:20-alpine AS builder

WORKDIR /app

# 复制前端文件
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# 生产环境
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Zeabur 强制注入 PORT=8080，nginx 需监听 8080（见 nginx.conf）
ENV PORT=8080
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
