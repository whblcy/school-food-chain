"""
认证工具。
- 密码哈希 (bcrypt)
- JWT access_token / refresh_token（支持 HS256 对称 / RS256 非对称）
- Token 黑名单 (Redis / 内存 fallback)
- 登录限流（Redis 滑动窗口 / 内存 fallback，避免暴力破解）
- HttpOnly Cookie 支持（防 XSS 窃取 token）
"""
from __future__ import annotations

import time
import uuid
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Tuple

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings
from app.database import get_db
from app.models import User, UserRole
from app.redis_client import get_redis

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 密码哈希（使用 bcrypt 原生函数，避免 passlib + bcrypt 5.x 的兼容性问题）
# ---------------------------------------------------------------------------
security = HTTPBearer()


def _ensure_bytes(s):
    if isinstance(s, bytes):
        return s
    return s.encode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码 —— bcrypt 对长密码自动截断为 72 字节。"""
    try:
        return bcrypt.checkpw(_ensure_bytes(plain_password), _ensure_bytes(hashed_password))
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """生成密码哈希。"""
    return bcrypt.hashpw(_ensure_bytes(password), bcrypt.gensalt()).decode("utf-8")


# ---------------------------------------------------------------------------
# JWT 工具 — 支持 HS256（对称）与 RS256（非对称）
# ---------------------------------------------------------------------------
ALGORITHM = settings.JWT_ALGORITHM


def _load_key(content: str, path: str) -> str:
    """从字符串或文件路径加载密钥。"""
    if path:
        return Path(path).read_text(encoding="utf-8")
    return content


def _get_signing_key() -> str:
    """获取签名密钥（HS256 用 SECRET_KEY，RS256 用私钥）。"""
    if ALGORITHM.startswith("RS"):
        return _load_key(settings.JWT_PRIVATE_KEY, settings.JWT_PRIVATE_KEY_PATH)
    return settings.SECRET_KEY


def _get_verify_key() -> str:
    """获取验签密钥（HS256 用 SECRET_KEY，RS256 用公钥）。"""
    if ALGORITHM.startswith("RS"):
        return _load_key(settings.JWT_PUBLIC_KEY, settings.JWT_PUBLIC_KEY_PATH)
    return settings.SECRET_KEY


SIGNING_KEY = _get_signing_key()
VERIFY_KEY = _get_verify_key()


def _jwt_payload(sub: str, token_type: str, minutes: int) -> Tuple[Dict, datetime]:
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": sub, "type": token_type, "exp": expire}
    return payload, expire


def create_access_token(data: dict) -> str:
    """生成 access_token。data 需包含 'sub'（user.id 的字符串）。"""
    sub = data.get("sub")
    if sub is None:
        raise ValueError("create_access_token: data['sub'] is required")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(sub),
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SIGNING_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    sub = data.get("sub")
    if sub is None:
        raise ValueError("create_refresh_token: data['sub'] is required")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(sub),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SIGNING_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """解析 JWT；若签名错误/过期则返回 None。"""
    try:
        return jwt.decode(token, VERIFY_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Token 黑名单 — 支持 Redis（部署环境）与内存 fallback（开发环境）
#
# key = "jwt:bl:<token_suffix>"
# TTL = token 的剩余过期时间（max 与 token 过期一致）
# ---------------------------------------------------------------------------
class _TokenBlacklist:
    """极简的 token 黑名单实现。Redis 优先，内存 fallback。"""

    def __init__(self) -> None:
        self._memory: Dict[str, float] = {}  # key -> expire_ts (epoch seconds)

    @property
    def _redis(self):
        """懒加载全局 Redis 客户端。"""
        return get_redis()

    def _key(self, token: str) -> str:
        return f"jwt:bl:{token[-16:]}"

    def add(self, token: str, ttl_seconds: int = None) -> None:
        """把 token 加入黑名单。ttl 默认等同于 token 剩余时间，但最多不超过 24h。"""
        payload = decode_token(token)
        if payload is None:
            return
        exp = payload.get("exp")
        remaining = max(0, int(exp - time.time())) if exp else 3600
        ttl = min(ttl_seconds or remaining, 24 * 3600)
        key = self._key(token)
        redis = self._redis
        if redis is not None:
            redis.setex(key, ttl, "1")
        else:
            self._memory[key] = time.time() + ttl
            # 清理过期
            now = time.time()
            self._memory = {k: v for k, v in self._memory.items() if v > now}

    def is_blacklisted(self, token: str) -> bool:
        key = self._key(token)
        redis = self._redis
        if redis is not None:
            return bool(redis.exists(key))
        ts = self._memory.get(key)
        return bool(ts and ts > time.time())


blacklist = _TokenBlacklist()


# ---------------------------------------------------------------------------
# 登录限流 — Redis 滑动窗口（多 Worker 共享），内存 fallback
# ---------------------------------------------------------------------------
class _RateLimiter:
    """基于 Redis 的滑动窗口限流。

    - 每个 key（用户名 / IP）在 BLOCK_SECONDS 秒内最多 MAX_ATTEMPTS 次失败
    - 超过则拒绝，直到窗口内最早一条记录过期
    - Redis 不可用时降级为进程内存（仅单 Worker 有效）
    """
    MAX_ATTEMPTS = 10
    BLOCK_SECONDS = 300

    def __init__(self) -> None:
        self._failures: Dict[str, list] = {}

    def _key(self, raw_key: str) -> str:
        return f"rl:login:{raw_key}"

    def record_failure(self, key: str) -> None:
        now = time.time()
        redis = get_redis()
        if redis is not None:
            rk = self._key(key)
            pipe = redis.pipeline()
            pipe.zadd(rk, {str(now): now})
            pipe.zremrangebyscore(rk, 0, now - self.BLOCK_SECONDS)
            pipe.expire(rk, self.BLOCK_SECONDS)
            pipe.execute()
            return
        # 内存 fallback
        self._failures.setdefault(key, []).append(now)
        cutoff = now - self.BLOCK_SECONDS
        self._failures[key] = [t for t in self._failures[key] if t > cutoff]
        if len(self._failures) > 5000:
            self._failures = {k: v for k, v in self._failures.items() if v}

    def is_blocked(self, key: str) -> bool:
        redis = get_redis()
        if redis is not None:
            rk = self._key(key)
            now = time.time()
            redis.zremrangebyscore(rk, 0, now - self.BLOCK_SECONDS)
            count = redis.zcard(rk)
            return count >= self.MAX_ATTEMPTS
        # 内存 fallback
        now = time.time()
        attempts = [t for t in self._failures.get(key, []) if t > now - self.BLOCK_SECONDS]
        self._failures[key] = attempts
        return len(attempts) >= self.MAX_ATTEMPTS

    def remaining_attempts(self, key: str) -> int:
        redis = get_redis()
        if redis is not None:
            rk = self._key(key)
            now = time.time()
            redis.zremrangebyscore(rk, 0, now - self.BLOCK_SECONDS)
            count = redis.zcard(rk)
            return max(0, self.MAX_ATTEMPTS - count)
        now = time.time()
        attempts = [t for t in self._failures.get(key, []) if t > now - self.BLOCK_SECONDS]
        return max(0, self.MAX_ATTEMPTS - len(attempts))

    def reset(self, key: str) -> None:
        """登录成功后清除失败记录。"""
        redis = get_redis()
        if redis is not None:
            redis.delete(self._key(key))
            return
        self._failures.pop(key, None)


rate_limiter = _RateLimiter()


# ---------------------------------------------------------------------------
# 依赖 — 解析 token 并返回当前用户（含黑名单检查）
# ---------------------------------------------------------------------------
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
) -> User:
    token = credentials.credentials
    # 检查黑名单（用户主动登出的 token）
    if blacklist.is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    user = db.query(User).filter(User.id == uid).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


# ---------------------------------------------------------------------------
# HttpOnly Cookie 辅助 — 防 XSS 窃取 token
# ---------------------------------------------------------------------------
def set_auth_cookies(response, access_token: str, refresh_token: str) -> None:
    """将 access_token / refresh_token 写入 HttpOnly Cookie。

    - HttpOnly: JavaScript 无法读取，防 XSS
    - Secure: 仅 HTTPS 传输（生产环境强制）
    - SameSite: 防 CSRF
    """
    if not settings.COOKIE_ENABLED:
        return

    cookie_kwargs = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
    }
    if settings.COOKIE_DOMAIN:
        cookie_kwargs["domain"] = settings.COOKIE_DOMAIN

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_kwargs,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        **cookie_kwargs,
    )


def clear_auth_cookies(response) -> None:
    """清除认证 Cookie（登出时调用）。"""
    if not settings.COOKIE_ENABLED:
        return

    cookie_kwargs = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
    }
    if settings.COOKIE_DOMAIN:
        cookie_kwargs["domain"] = settings.COOKIE_DOMAIN

    response.delete_cookie(key="access_token", **cookie_kwargs)
    response.delete_cookie(key="refresh_token", **cookie_kwargs)


# ---------------------------------------------------------------------------
# 角色授权辅助函数 — 用于在路由中做权限检查
# ---------------------------------------------------------------------------
def require_roles(*roles: UserRole):
    """生成一个 FastAPI dependency：要求当前用户属于指定角色之一。

    用法:
        @app.get("/admin/stats")
        def admin_stats(current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN))):
            ...
    """
    allowed = set(roles)

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _checker


# ---------------------------------------------------------------------------
# 多租户隔离辅助
# ---------------------------------------------------------------------------
# 约定:
#   - UserRole.SUPER_ADMIN 可跨组织查看（平台管理员 / 教育局全局视角）
#   - 其它角色(ADMIN/MANAGER/OPERATOR/VIEWER) 仅能查看 org_id == 所属组织的数据
#     （教育局 ADMIN 的"本组织+子组织"视角由 gov.py 自行实现，不走 _TenantContext）
# ---------------------------------------------------------------------------
def has_cross_org_access(user: User) -> bool:
    return user.role == UserRole.SUPER_ADMIN


class _TenantContext:
    """携带当前用户和 org_id 过滤策略 — 作为业务路由 dependency。"""

    def __init__(self, user: User):
        self.user = user
        self.is_cross_org = has_cross_org_access(user)
        self.org_id = user.org_id

    def filter(self, model_cls, query):
        """给 SQLAlchemy query 加上 org_id 过滤；跨组织用户不额外过滤。"""
        if self.is_cross_org:
            return query
        if self.org_id is None:
            from sqlalchemy.sql import false as sql_false
            return query.filter(sql_false())  # 无组织 -> 查不到任何东西
        return query.filter(model_cls.org_id == self.org_id)

    def assign(self, instance):
        """新创建对象时自动赋 org_id（避免用户越权创建其它组织对象）。

        - SUPER_ADMIN：允许创建在指定组织，但默认回退到用户自己的组织
        - 其它角色：强制覆盖为自身 org_id，禁止越权
        """
        if not hasattr(instance, "org_id"):
            return instance

        if self.is_cross_org:
            # 超级管理员允许创建在指定组织，但默认回退到用户自己的组织
            if getattr(instance, "org_id", None) is None and self.org_id is not None:
                instance.org_id = self.org_id
        else:
            # 普通用户：强制使用自身组织，禁止越权
            if self.org_id is not None:
                instance.org_id = self.org_id
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="当前用户未分配组织，无法创建数据",
                )
        return instance


def get_tenant(current_user: User = Depends(get_current_user)) -> _TenantContext:
    return _TenantContext(current_user)
