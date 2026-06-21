"""
Redis 客户端 — 全局共享连接池。

用途:
  - 登录限流（滑动窗口）
  - Token 黑名单
  - 业务缓存层（fastapi-cache2 backend）
  - WebSocket Pub/Sub（实时推送）

设计:
  - 懒加载，首次使用时建立连接
  - Redis 不可用时返回 None，调用方需自行降级
  - 连接失败后 30 秒内不再重试，避免每次请求都超时
  - decode_responses=True，所有返回值为 str
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import redis as redis_lib

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis_lib.Redis] = None
_last_check_ts: float = 0
_check_interval: float = 30.0  # 连接失败后 30 秒内不重试


def get_redis() -> Optional[redis_lib.Redis]:
    """获取全局 Redis 客户端（单例）。Redis 不可用时返回 None。"""
    global _redis_client, _last_check_ts

    if _redis_client is not None:
        return _redis_client

    # 连接失败后冷却期内直接返回 None，避免每次请求都超时
    now = time.time()
    if now - _last_check_ts < _check_interval:
        return None

    _last_check_ts = now
    try:
        client = redis_lib.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=1,          # 缩短超时，快速失败
            socket_connect_timeout=1,
            retry_on_timeout=False,
            health_check_interval=30,
        )
        client.ping()
        _redis_client = client
        logger.info("Redis connected: %s", settings.REDIS_URL)
    except Exception as e:
        logger.debug("Redis unavailable (degraded mode): %s", e)
        _redis_client = None

    return _redis_client


def is_redis_available() -> bool:
    """检查 Redis 是否可用。"""
    return get_redis() is not None
