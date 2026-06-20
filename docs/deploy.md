# 部署指南

本文档详细说明 School Food Chain（学校食材供应链管理平台）的部署流程，包括 Docker Compose 一键部署、手动部署、Nginx 反向代理配置、SSL 证书配置、数据库迁移及常见问题排查。

---

## 目录

- [环境要求](#环境要求)
- [Docker Compose 部署（推荐）](#docker-compose-部署推荐)
- [手动部署](#手动部署)
- [Nginx 反向代理配置](#nginx-反向代理配置)
- [SSL/HTTPS 配置](#sslhttps-配置)
- [数据库迁移（Alembic）](#数据库迁移alembic)
- [环境变量说明](#环境变量说明)
- [常见问题 FAQ](#常见问题-faq)

---

## 环境要求

### 硬件要求

| 规格 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 20 GB | 50 GB SSD |

### 软件要求

| 软件 | 版本要求 | 说明 |
|------|----------|------|
| Docker | >= 20.10 | 容器运行时 |
| Docker Compose | >= 2.0 | 容器编排 |
| Python | >= 3.11 | 后端运行时（手动部署时） |
| Node.js | >= 18.x | 前端构建（手动部署时） |
| Nginx | >= 1.20 | 反向代理（手动部署时） |
| PostgreSQL | >= 16 | 数据库（手动部署时） |
| Redis | >= 7.0 | 缓存/消息队列（手动部署时） |
| Git | >= 2.30 | 版本管理 |

### 操作系统支持

- Ubuntu 20.04 / 22.04 LTS
- CentOS 7 / 8
- Debian 11 / 12
- macOS（开发环境）
- Windows Server 2019+（需 WSL2）

---

## Docker Compose 部署（推荐）

### 1. 克隆项目

```bash
git clone https://github.com/whblcy/school-food-chain.git
cd school-food-chain
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，**务必修改以下关键配置**：

```bash
# 生成安全的密钥（使用以下命令生成随机密钥）
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 将生成的密钥填入 .env
SECRET_KEY=<生成的随机密钥>

# 修改数据库密码
POSTGRES_PASSWORD=<强密码>

# 修改 MinIO 密钥
MINIO_ACCESS_KEY=<自定义AccessKey>
MINIO_SECRET_KEY=<自定义SecretKey>
```

### 3. 构建并启动服务

```bash
# 构建镜像并后台启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看实时日志
docker-compose logs -f
```

### 4. 初始化数据库

```bash
# 执行数据库迁移
docker-compose exec backend alembic upgrade head

# 创建初始管理员账户（可选）
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
db = SessionLocal()
admin = User(
    username='admin',
    hashed_password=pwd_context.hash('admin123'),
    role='admin',
    is_active=True
)
db.add(admin)
db.commit()
print('管理员账户创建成功: admin / admin123')
"
```

### 5. 验证部署

```bash
# 健康检查
curl http://localhost/health

# 访问 API 文档
# 浏览器打开 http://localhost:8000/docs
```

### 6. 生产环境优化

在生产环境中，建议修改 `docker-compose.yml`：

```yaml
# 1. 限制资源
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G

# 2. 调整日志级别
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

# 3. 健康检查
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 常用运维命令

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（谨慎！会丢失数据）
docker-compose down -v

# 重启单个服务
docker-compose restart backend

# 查看某个服务的日志
docker-compose logs -f backend --tail=100

# 更新并重新部署
git pull
docker-compose up -d --build

# 进入容器内部
docker-compose exec backend bash
```

---

## 手动部署

### 后端部署

```bash
# 1. 安装系统依赖（Ubuntu）
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip \
    libpq-dev gcc build-essential

# 2. 创建虚拟环境
cd backend
python3.11 -m venv venv
source venv/bin/activate

# 3. 安装 Python 依赖
pip install --upgrade pip
pip install -r requirements.txt

# 4. 配置环境变量
cp ../.env.example .env
# 编辑 .env，配置数据库、Redis、密钥等

# 5. 数据库迁移
alembic upgrade head

# 6. 启动服务（开发模式）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 7. 启动服务（生产模式 - 使用 Gunicorn）
pip install gunicorn
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
```

#### 使用 Systemd 管理后端服务

创建 `/etc/systemd/system/school-food-backend.service`：

```ini
[Unit]
Description=School Food Chain Backend API
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/school-food-chain/backend
EnvironmentFile=/opt/school-food-chain/backend/.env
ExecStart=/opt/school-food-chain/backend/venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable school-food-backend
sudo systemctl start school-food-backend
sudo systemctl status school-food-backend
```

#### Celery Worker 配置

创建 `/etc/systemd/system/school-food-celery.service`：

```ini
[Unit]
Description=School Food Chain Celery Worker
After=network.target redis.service
Requires=redis.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/school-food-chain/backend
EnvironmentFile=/opt/school-food-chain/backend/.env
ExecStart=/opt/school-food-chain/backend/venv/bin/celery \
    -A app.celery worker \
    --loglevel=info \
    --concurrency=4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

创建 `/etc/systemd/system/school-food-celery-beat.service`：

```ini
[Unit]
Description=School Food Chain Celery Beat
After=network.target redis.service
Requires=redis.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/school-food-chain/backend
EnvironmentFile=/opt/school-food-chain/backend/.env
ExecStart=/opt/school-food-chain/backend/venv/bin/celery \
    -A app.celery beat \
    --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 前端部署

```bash
# 1. 安装 Node.js 18（如未安装）
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 2. 安装依赖
cd web
npm install

# 3. 修改 API 地址
# 编辑 src/api/index.js，将 baseURL 修改为实际后端地址

# 4. 生产构建
npm run build

# 5. 将构建产物部署到 Nginx 静态目录
# 构建产物在 web/dist/ 目录
sudo cp -r dist/* /usr/share/nginx/html/
```

### 桌面端打包

```bash
cd desktop

# 1. 安装依赖
pip install -r requirements.txt
pip install pyinstaller

# 2. 打包为单个可执行文件
pyinstaller --onefile --windowed \
    --name "SchoolFoodChain" \
    --icon=assets/icon.ico \
    --add-data "ui:ui" \
    --add-data "core:core" \
    main.py

# 3. 打包产物在 dist/SchoolFoodChain.exe（Windows）或 dist/SchoolFoodChain（Linux/macOS）

# 4. macOS 额外步骤：创建 .app 包
pyinstaller --onefile --windowed \
    --osx-bundle-identifier com.schoolfoodchain.desktop \
    --name "SchoolFoodChain" \
    main.py
```

---

## Nginx 反向代理配置

项目根目录已提供 `nginx.conf` 配置文件，可直接使用。以下是配置要点说明：

### 配置文件位置

| 部署方式 | 配置文件路径 |
|----------|-------------|
| Docker Compose | 项目根目录 `nginx.conf`（自动挂载） |
| 手动部署 | `/etc/nginx/conf.d/school-food-chain.conf` |

### 手动部署时安装配置

```bash
# 1. 安装 Nginx
sudo apt-get install -y nginx

# 2. 复制配置文件
sudo cp nginx.conf /etc/nginx/conf.d/school-food-chain.conf

# 3. 删除默认配置（避免冲突）
sudo rm -f /etc/nginx/sites-enabled/default

# 4. 测试配置
sudo nginx -t

# 5. 重载 Nginx
sudo systemctl reload nginx
```

### 配置要点

- **upstream backend**: 指向后端服务 `localhost:8000`
- **location /api/**: 反向代理到后端 API
- **location /**: 静态文件服务，指向 Vue 构建产物
- **WebSocket**: 支持 `/ws/` 路径的 WebSocket 连接
- **gzip**: 开启压缩，减小传输体积
- **安全头**: 包含 X-Frame-Options、X-Content-Type-Options 等安全响应头

---

## SSL/HTTPS 配置

### 使用 Let's Encrypt（免费证书）

```bash
# 1. 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 2. 申请证书（替换 your-domain.com）
sudo certbot --nginx -d your-domain.com -d api.your-domain.com

# 3. 自动续期（Certbot 会自动设置定时任务）
sudo certbot renew --dry-run
```

### 手动配置 SSL

在 `nginx.conf` 的 server 块中添加：

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/nginx/ssl/your-domain.com.crt;
    ssl_certificate_key /etc/nginx/ssl/your-domain.com.key;

    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # HSTS（启用前请确保配置正确）
    add_header Strict-Transport-Security "max-age=63072000" always;

    # 其余配置与 HTTP 相同...
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 数据库迁移（Alembic）

### 基本操作

```bash
cd backend

# 查看当前迁移状态
alembic current

# 查看迁移历史
alembic history --verbose

# 执行所有待执行的迁移
alembic upgrade head

# 回滚到上一个版本
alembic downgrade -1

# 回滚到指定版本
alembic downgrade <revision_id>

# 创建新的迁移脚本
alembic revision --autogenerate -m "描述本次变更"
```

### Docker 环境中执行迁移

```bash
# 在容器内执行
docker-compose exec backend alembic upgrade head

# 创建新迁移
docker-compose exec backend alembic revision --autogenerate -m "add new table"
```

### 迁移最佳实践

1. **每次修改模型后立即生成迁移**，不要积累多个变更
2. **迁移脚本纳入版本控制**，团队共享
3. **生产环境迁移前先备份数据库**
4. **使用 `--autogenerate` 后检查生成的脚本**，确保正确性
5. **迁移脚本添加注释**，说明变更内容

```bash
# 生产环境迁移前备份
pg_dump -U postgres school_food > backup_$(date +%Y%m%d_%H%M%S).sql

# 执行迁移
alembic upgrade head

# 验证迁移结果
alembic current
```

---

## 环境变量说明

所有环境变量在 `.env` 文件中配置，参考 `.env.example` 模板。

### 核心配置

| 变量名 | 说明 | 默认值 | 是否必填 |
|--------|------|--------|----------|
| `SECRET_KEY` | JWT 签名密钥，**生产环境必须修改** | `your-secret-key-change-in-production` | 是 |
| `DEBUG` | 调试模式，生产环境设为 `false` | `false` | 否 |
| `DATABASE_URL` | PostgreSQL 连接字符串 | `postgresql://postgres:postgres@localhost:5432/school_food` | 是 |
| `REDIS_URL` | Redis 连接字符串 | `redis://localhost:6379/0` | 是 |

### 安全配置

| 变量名 | 说明 | 默认值 | 是否必填 |
|--------|------|--------|----------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 过期时间（分钟） | `1440`（1天） | 否 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token 过期时间（天） | `7` | 否 |
| `CORS_ORIGINS` | 允许的跨域来源（逗号分隔） | `*` | 否 |

### MinIO 文件存储

| 变量名 | 说明 | 默认值 | 是否必填 |
|--------|------|--------|----------|
| `MINIO_ENDPOINT` | MinIO 服务地址 | `localhost:9000` | 是 |
| `MINIO_ACCESS_KEY` | MinIO Access Key | `minioadmin` | 是 |
| `MINIO_SECRET_KEY` | MinIO Secret Key | `minioadmin` | 是 |
| `MINIO_BUCKET` | 存储桶名称 | `school-food` | 否 |

### Docker Compose 专用

| 变量名 | 说明 | 默认值 | 是否必填 |
|--------|------|--------|----------|
| `POSTGRES_USER` | PostgreSQL 用户名 | `postgres` | 否 |
| `POSTGRES_PASSWORD` | PostgreSQL 密码 | `postgres` | 否 |
| `POSTGRES_DB` | 数据库名称 | `school_food` | 否 |

---

## 常见问题 FAQ

### Q1: Docker Compose 启动失败，后端服务不断重启

**原因**: 数据库未就绪时后端已启动，连接失败。

**解决方案**:
```bash
# 检查日志
docker-compose logs backend

# 确认 PostgreSQL 是否正常运行
docker-compose ps postgres

# 重启后端服务
docker-compose restart backend
```

### Q2: 数据库连接被拒绝

**原因**: `DATABASE_URL` 配置错误，或 PostgreSQL 未启动。

**解决方案**:
```bash
# 检查 .env 中的 DATABASE_URL
# Docker 环境：DATABASE_URL 应使用服务名
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/school_food

# 手动部署：DATABASE_URL 应使用 localhost 或 127.0.0.1
DATABASE_URL=postgresql://postgres:yourpassword@127.0.0.1:5432/school_food

# 测试数据库连接
docker-compose exec postgres psql -U postgres -d school_food -c "SELECT 1;"
```

### Q3: Nginx 502 Bad Gateway

**原因**: Nginx 无法连接到后端服务。

**解决方案**:
```bash
# 检查后端是否运行
curl http://localhost:8000/health

# 检查 Nginx 配置
sudo nginx -t

# 检查 Nginx 错误日志
sudo tail -f /var/log/nginx/error.log

# 确认 upstream 配置中的端口与后端一致
```

### Q4: 前端页面空白，API 请求 404

**原因**: 前端 API 地址配置错误，或 Nginx 代理配置有误。

**解决方案**:
```bash
# 检查前端 API 配置（web/src/api/index.js）
# 开发环境：baseURL 应为 http://localhost:8000/api/v1
# 生产环境：baseURL 应为 /api/v1（通过 Nginx 代理）

# 检查 Nginx 是否正确代理 /api/ 路径
curl http://localhost/api/v1/auth/login
```

### Q5: MinIO 文件上传失败

**原因**: MinIO 存储桶未创建或权限配置错误。

**解决方案**:
```bash
# 进入 MinIO 控制台
# 浏览器打开 http://localhost:9001
# 使用 MINIO_ACCESS_KEY / MINIO_SECRET_KEY 登录
# 创建名为 "school-food" 的存储桶
# 设置存储桶策略为公开读取（如需要）

# 或使用 mc 命令行工具
docker-compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker-compose exec minio mc mb local/school-food
docker-compose exec minio mc anonymous set download local/school-food
```

### Q6: 数据库迁移报错

**原因**: 迁移版本冲突或数据库状态不一致。

**解决方案**:
```bash
# 查看当前版本
alembic current

# 查看历史
alembic history

# 如果版本不一致，标记为当前版本（谨慎使用）
alembic stamp head

# 如果需要回滚
alembic downgrade <target_revision>
alembic upgrade head
```

### Q7: Celery 任务不执行

**原因**: Redis 连接失败或 Celery Worker 未启动。

**解决方案**:
```bash
# 检查 Redis 是否运行
docker-compose exec redis redis-cli ping

# 检查 Celery Worker 状态
docker-compose ps celery-worker
docker-compose logs celery-worker

# 重启 Celery
docker-compose restart celery-worker celery-beat
```

### Q8: 如何备份数据

```bash
# 备份 PostgreSQL
docker-compose exec postgres pg_dump -U postgres school_food > backup.sql

# 备份 Redis（如需要）
docker-compose exec redis redis-cli BGSAVE
docker cp $(docker-compose ps -q redis):/data/dump.rdb redis_backup.rdb

# 备份 MinIO 数据
docker cp $(docker-compose ps -q minio):/data minio_backup
```

### Q9: 如何重置整个环境

```bash
# 停止并删除所有容器和数据卷
docker-compose down -v

# 重新构建并启动
docker-compose up -d --build

# 重新执行迁移
docker-compose exec backend alembic upgrade head
```

### Q10: 性能优化建议

| 优化项 | 说明 |
|--------|------|
| PostgreSQL | 增加 `shared_buffers`、`effective_cache_size`；使用连接池 |
| Redis | 启用持久化（AOF）；设置合理的 maxmemory |
| Nginx | 开启 gzip、配置缓存；使用 CDN 分发静态资源 |
| 后端 | 增加 Gunicorn worker 数量（建议 2-4 x CPU 核数） |
| 前端 | 开启路由懒加载；图片使用 WebP 格式；配置 CDN |
| 数据库 | 为常用查询字段添加索引；定期 VACUUM |
