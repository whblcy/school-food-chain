"""
全局 API 限流 — 基于 Redis 的滑动窗口。

策略:
  - 按用户 ID（已认证）或 IP（未认证）维度限流
  - 读接口: 120 req/min
  - 写接口: 60 req/min
  - 登录/刷新: 10 req/min（更严格，防暴力破解）

Redis 不可用时自动降级（不限流，仅记录警告）。
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.redis_client import get_redis

logger = logging.getLogger(__name__)

# 限流配置：路径前缀 -> (limit, window_seconds)
_RATE_RULES = [
    ("/api/v1/auth/login", 10, 60),       # 登录: 10次/分钟
    ("/api/v1/auth/refresh", 10, 60),     # 刷新: 10次/分钟
    ("/api/v1/auth/logout", 10, 60),      # 登出: 10次/分钟
]

# 默认限流：读接口 120/min，写接口 60/min
_DEFAULT_READ_LIMIT = 120
_DEFAULT_WRITE_LIMIT = 60
_WINDOW = 60  # 秒

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _get_client_id(request: Request) -> str:
    """获取客户端标识：优先用 user_id（从已解析的 state 中取），其次 IP。"""
    user = getattr(request.state, "user", None)
    if user is not None:
        uid = getattr(user, "id", None)
        if uid is not None:
            return f"u:{uid}"
    # IP（取 X-Forwarded-For 第一个或 connection.host）
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


def _get_rate_limit(request: Request) -> tuple[int, int]:
    """根据路径和方法返回 (limit, window)。"""
    path = request.url.path
    for prefix, limit, window in _RATE_RULES:
        if path.startswith(prefix):
            return limit, window
    # 默认
    if request.method in _WRITE_METHODS:
        return _DEFAULT_WRITE_LIMIT, _WINDOW
    return _DEFAULT_READ_LIMIT, _WINDOW


class RateLimitMiddleware(BaseHTTPMiddleware):
    """全局 API 限流中间件。"""

    async def dispatch(self, request: Request, call_next):
        # 健康检查不限流
        if request.url.path in ("//health", "/health", "/live", "/ready", "/metrics"):
            return await call_next(request)

        redis = get_redis()
        if redis is None:
            # Redis 不可用，跳过限流
            return await call_next(request)

        client_id = _get_client_id(request)
        limit, window = _get_rate_limit(request)
        bucket = f"rl:api:{client_id}:{request.url.path}"

        now = time.time()
        pipe = redis.pipeline()
        pipe.zremrangebyscore(bucket, 0, now - window)
        pipe.zadd(bucket, {str(now): now})
        pipe.zcard(bucket)
        pipe.expire(bucket, window)
        results = pipe.execute()
        count = results[2]

        if count > limit:
            logger.warning(
                "Rate limit exceeded: client=%s path=%s count=%d limit=%d",
                client_id, request.url.path, count, limit,
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试"},
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response
