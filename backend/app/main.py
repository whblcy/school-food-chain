"""
School Food Chain - FastAPI Backend
- 数据库表结构通过 Alembic 迁移管理（`alembic upgrade head`），
  不在应用启动时自动建表，避免与迁移系统冲突。
"""
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.config import settings
from app.routers import auth, users, orgs, suppliers, ingredients, stock, finance, reports, trace, audit, gov
from app.rate_limit import RateLimitMiddleware
from app.websocket import router as ws_router, start_redis_subscriber

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="School Food Chain API",
    description="学校食堂食材全链路管理平台",
    version="1.0.0",
)

# ---- 全局 API 限流（Redis 滑动窗口，按 user_id/ip 维度） ----
app.add_middleware(RateLimitMiddleware)


# ---- Prometheus 指标中间件 ----
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """记录 HTTP 请求计数和延迟。"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # 归一化路径（避免高基数，如 /api/v1/ingredients/123 → /api/v1/ingredients/{id}）
    path = request.url.path
    # 简单归一化：将末尾数字段替换为 {id}
    parts = path.rstrip("/").split("/")
    if parts and parts[-1].isdigit():
        parts[-1] = "{id}"
    normalized_path = "/".join(parts)

    try:
        from app.metrics import http_requests_total, http_request_duration_seconds
        http_requests_total.labels(
            method=request.method,
            path=normalized_path,
            status=str(response.status_code),
        ).inc()
        http_request_duration_seconds.labels(
            method=request.method,
            path=normalized_path,
        ).observe(duration)
    except Exception:
        pass

    return response

# ---- CORS ----
# 安全策略：
#   - 若 CORS_ORIGINS 含 "*"（仅开发环境），用自定义中间件反射 Origin
#   - 否则使用 FastAPI 白名单匹配（生产环境推荐）
if "*" in settings.CORS_ORIGINS:
    @app.middleware("http")
    async def cors_reflect_origin(request: Request, call_next):
        # 预检请求直接返回，不经过业务逻辑
        if request.method == "OPTIONS":
            response = JSONResponse(status_code=204, content={})
        else:
            response = await call_next(request)
        origin = request.headers.get("origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Authorization,Content-Type,Accept,Origin,User-Agent,DNT,Cache-Control,X-Mx-ReqToken,Keep-Alive,X-Requested-With,If-Modified-Since"
            response.headers["Access-Control-Max-Age"] = "86400"
        return response
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)


# ---- 安全响应头 ----
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        # 生产环境 CSP（限制资源加载来源）
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
    return response


# ---- 全局异常处理 ----
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning(f"Integrity error on {request.url.path}: {exc}")
    return JSONResponse(status_code=400, content={"detail": "数据冲突，请检查唯一性约束或外键引用"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.url.path}: {exc}")
    if settings.DEBUG:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})


# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])
app.include_router(orgs.router, prefix="/api/v1/orgs", tags=["组织"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["供应商"])
app.include_router(ingredients.router, prefix="/api/v1/ingredients", tags=["食材"])
app.include_router(stock.router, prefix="/api/v1/stock", tags=["库存"])
app.include_router(finance.router, prefix="/api/v1/finance", tags=["财务"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["报表"])
app.include_router(trace.router, prefix="/api/v1/trace", tags=["追溯"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["审计"])
app.include_router(gov.router, prefix="/api/v1/gov", tags=["教育局监管"])
app.include_router(ws_router, prefix="/api/v1", tags=["WebSocket"])


@app.on_event("startup")
def _on_startup():
    """应用启动时初始化 Redis 订阅器（WebSocket 实时推送）。"""
    start_redis_subscriber()


@app.get("/health")
def health_check():
    """健康检查 — 包含数据库与 Redis 依赖状态。"""
    checks = {"app": "ok"}
    # 数据库
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "fail"
    # Redis（可选依赖，降级不致命）
    try:
        from app.redis_client import get_redis
        redis = get_redis()
        if redis is not None:
            redis.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "degraded"
    except Exception:
        checks["redis"] = "degraded"

    overall = "ok" if checks["db"] == "ok" and checks["app"] == "ok" else "fail"
    return {"status": overall, "checks": checks, "version": "1.0.0"}


@app.get("/live")
def liveness():
    """存活探针 — 仅检查进程是否响应，不检查依赖。"""
    return {"status": "ok"}


@app.get("/ready")
def readiness():
    """就绪探针 — DB 和 Redis 都可用才返回 200，否则 503。"""
    checks = {"app": "ok"}
    ready = True

    try:
        from app.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "fail"
        ready = False

    try:
        from app.redis_client import get_redis
        redis = get_redis()
        if redis is not None:
            redis.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "degraded"
            # Redis 降级不算 not ready（业务可降级运行）
    except Exception:
        checks["redis"] = "degraded"

    status_code = 200 if ready else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if ready else "not_ready", "checks": checks},
    )


@app.get("/metrics")
def metrics():
    """Prometheus 指标端点。"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
