# ============================================================
# 后端镜像 — FastAPI + Uvicorn + Celery
# 用途: docker-compose 中的 backend / celery-worker / celery-beat
# 多阶段构建：builder 编译 wheel，runtime 仅保留运行时依赖
# ============================================================

# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# builder 阶段安装编译依赖（psycopg2 编译需要 pg_config / gcc）
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 将依赖安装到独立目录，便于 runtime 阶段复制
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

LABEL org.opencontainers.image.title="school-food-chain-backend" \
      org.opencontainers.image.description="FastAPI + Celery backend for school food chain platform"

WORKDIR /app

# 运行时只需要 libpq5（psycopg2-binary 仍依赖系统 libpq）
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制已安装的 Python 依赖
COPY --from=builder /install /usr/local

# 创建非 root 用户运行应用，避免容器内以 root 权限执行
RUN groupadd --system --gid 1001 appgroup \
    && useradd --system --uid 1001 --gid appgroup --home-dir /app --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appgroup /app

# 拷贝应用代码
COPY --chown=appuser:appgroup alembic.ini ./alembic.ini
COPY --chown=appuser:appgroup alembic ./alembic
COPY --chown=appuser:appgroup app ./app

USER appuser

EXPOSE 8000

# 健康检查由 docker-compose 的 healthcheck 接管，这里仅给默认入口
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
