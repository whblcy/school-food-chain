# ============================================================
# 前端镜像 — Vue3 + Vite -> 静态资源托管于 nginx
#
# 关键路径约定:
#   - Vite 默认 outDir = dist（项目的 vite.config.js 未自定义）
#   - 本 Dockerfile 将 ./dist 拷贝到 nginx /usr/share/nginx/html
#   - 其它地方引用必须与此一致（如 docker-compose 卷挂载）
# ============================================================

# ---------- 阶段 1: 构建 ----------
FROM node:20-alpine AS builder

WORKDIR /app

# 依赖优先
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund --loglevel=error

# 源码
COPY . .

# 生产构建 -> /app/dist
RUN npm run build

# ---------- 阶段 2: 运行 ----------
FROM nginx:1.27-alpine

# 自定义 nginx 配置（包含 /api 反向代理与 SPA fallback）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 产物来自 builder 阶段的 dist（Vite 默认 outDir）
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
