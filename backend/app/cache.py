"""
业务缓存层 — 基于 Redis 的轻量级缓存装饰器。

设计:
  - 按 org_id + 参数生成缓存 key，天然支持多租户
  - 支持 JSON 序列化（Pydantic 模型 / Decimal 自动转换）
  - Redis 不可用时自动降级（直接执行函数，不缓存）
  - 写操作后可手动调用 invalidate 清除缓存

用法:
    from app.cache import cached

    @cached(ttl=60, key_prefix="reports:stock_summary")
    def stock_summary(db, tenant, current_user):
        ...

    # 手动失效
    from app.cache import invalidate_pattern
    invalidate_pattern("reports:stock_summary:*")
"""
from __future__ import annotations

import functools
import hashlib
import json
import logging
from typing import Any, Callable, Optional

from app.redis_client import get_redis

logger = logging.getLogger(__name__)


def _record_hit(prefix: str) -> None:
    try:
        from app.metrics import record_cache_hit
        record_cache_hit(prefix)
    except Exception:
        pass


def _record_miss(prefix: str) -> None:
    try:
        from app.metrics import record_cache_miss
        record_cache_miss(prefix)
    except Exception:
        pass


class _DecimalEncoder(json.JSONEncoder):
    """支持 Decimal / datetime / UUID 等类型的 JSON 编码器。"""
    def default(self, o):
        if hasattr(o, "isoformat"):
            return o.isoformat()
        if hasattr(o, "value"):  # Enum
            return o.value
        if isinstance(o, float):
            return o
        try:
            return float(o)
        except (TypeError, ValueError):
            return str(o)


def _build_cache_key(key_prefix: str, args: tuple, kwargs: dict) -> str:
    """根据函数参数生成缓存 key。

    策略：从 args/kwargs 中提取 org_id 和关键参数，拼成可读 key。
    若无法提取 org_id，则用参数哈希。
    """
    # 尝试从 args 中提取 org_id（通常是 tenant 对象的 org_id 属性）
    org_id = None
    for arg in args:
        org_id = getattr(arg, "org_id", None)
        if org_id is not None:
            break

    # 提取 kwargs 中的关键参数
    significant_kwargs = {k: v for k, v in kwargs.items() if k not in ("db", "current_user", "tenant")}
    parts = [key_prefix]
    if org_id is not None:
        parts.append(f"org:{org_id}")
    if significant_kwargs:
        # 参数排序后哈希，避免顺序问题
        sig_str = json.dumps(significant_kwargs, sort_keys=True, default=str)
        sig_hash = hashlib.md5(sig_str.encode(), usedforsecurity=False).hexdigest()[:8]
        parts.append(sig_hash)
    return ":".join(parts)


def cached(ttl: int = 60, key_prefix: str = "cache") -> Callable:
    """Redis 缓存装饰器。

    Args:
        ttl: 缓存存活时间（秒）
        key_prefix: 缓存 key 前缀，如 "reports:stock_summary"
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            redis = get_redis()
            if redis is None:
                # Redis 不可用，直接执行
                return func(*args, **kwargs)

            cache_key = _build_cache_key(key_prefix, args, kwargs)
            try:
                cached_value = redis.get(cache_key)
                if cached_value is not None:
                    _record_hit(key_prefix)
                    return json.loads(cached_value)
                _record_miss(key_prefix)
            except Exception as e:
                logger.warning("Cache read error for %s: %s", cache_key, e)

            # 执行函数
            result = func(*args, **kwargs)

            # 写入缓存
            try:
                redis.setex(
                    cache_key,
                    ttl,
                    json.dumps(result, cls=_DecimalEncoder),
                )
            except Exception as e:
                logger.warning("Cache write error for %s: %s", cache_key, e)

            return result
        wrapper._cache_prefix = key_prefix  # type: ignore
        return wrapper
    return decorator


def invalidate_pattern(pattern: str) -> int:
    """按模式批量失效缓存。返回删除的 key 数量。

    Args:
        pattern: 如 "reports:stock_summary:*"
    """
    redis = get_redis()
    if redis is None:
        return 0
    try:
        # 使用 SCAN 避免阻塞（不用 KEYS）
        deleted = 0
        for key in redis.scan_iter(match=pattern, count=100):
            redis.delete(key)
            deleted += 1
        return deleted
    except Exception as e:
        logger.warning("Cache invalidate error for %s: %s", pattern, e)
        return 0


def invalidate_prefix(key_prefix: str) -> int:
    """按前缀失效缓存。"""
    return invalidate_pattern(f"{key_prefix}:*")
