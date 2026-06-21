"""
Prometheus 指标 — 请求计数、延迟直方图、DB 连接池监控。

指标列表:
  - http_requests_total: HTTP 请求总数（按 method/path/status 标签）
  - http_request_duration_seconds: HTTP 请求延迟直方图
  - db_connections_active: 当前 DB 活跃连接数
  - db_connections_pool_size: DB 连接池大小
  - cache_hits_total / cache_misses_total: 缓存命中/未命中
  - ws_connections_active: WebSocket 活跃连接数
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

logger = logging.getLogger(__name__)

# HTTP 请求指标
http_requests_total = Counter(
    "http_requests_total",
    "HTTP 请求总数",
    ["method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP 请求延迟（秒）",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# 数据库连接池指标
db_connections_active = Gauge(
    "db_connections_active",
    "当前 DB 活跃连接数",
)

db_connections_pool_size = Gauge(
    "db_connections_pool_size",
    "DB 连接池大小",
)

# 缓存指标
cache_hits_total = Counter(
    "cache_hits_total",
    "缓存命中总数",
    ["prefix"],
)

cache_misses_total = Counter(
    "cache_misses_total",
    "缓存未命中总数",
    ["prefix"],
)

# WebSocket 指标
ws_connections_active = Gauge(
    "ws_connections_active",
    "WebSocket 活跃连接数",
)


def record_cache_hit(prefix: str) -> None:
    """记录缓存命中。"""
    try:
        cache_hits_total.labels(prefix=prefix).inc()
    except Exception:
        pass


def record_cache_miss(prefix: str) -> None:
    """记录缓存未命中。"""
    try:
        cache_misses_total.labels(prefix=prefix).inc()
    except Exception:
        pass


def update_db_pool_metrics(engine) -> None:
    """更新 DB 连接池指标（定时调用）。"""
    try:
        pool = engine.pool
        db_connections_active.set(pool.checkedout())
        db_connections_pool_size.set(pool.size())
    except Exception:
        pass


def get_metrics_asgi_app():
    """返回 Prometheus ASGI 应用，可挂载到 FastAPI。"""
    return make_asgi_app()
