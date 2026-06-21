"""审计日志工具 — 提供统一的审计日志写入接口。

用法:
    from app.audit_utils import write_audit_log
    write_audit_log(db, request, current_user, action="create", target_type="supplier", target_id=obj.id, new_value=...)
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.models import AuditLog, User

logger = logging.getLogger(__name__)

# 敏感字段脱敏列表
_SENSITIVE_KEYS = {"password", "hashed_password", "token", "secret", "api_key"}


def _sanitize(value: Any) -> Any:
    """递归脱敏敏感字段。"""
    if isinstance(value, dict):
        return {k: ("***" if k.lower() in _SENSITIVE_KEYS else _sanitize(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


def write_audit_log(
    db: Session,
    request,
    user: Optional[User],
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    old_value: Any = None,
    new_value: Any = None,
) -> None:
    """写入一条审计日志。失败不阻断主业务。

    Args:
        db: SQLAlchemy session
        request: FastAPI Request 对象（用于提取 IP / User-Agent）
        user: 当前用户（可能为 None，如登录失败时）
        action: 动作名称（create / update / delete / login / logout / blacklist 等）
        target_type: 目标类型（supplier / ingredient / stock_in / user / org 等）
        target_id: 目标 ID
        old_value: 变更前的值（dict）
        new_value: 变更后的值（dict）
    """
    try:
        ip = None
        ua = None
        if request is not None:
            # 优先取 X-Forwarded-For（经过反向代理时）
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                ip = forwarded.split(",")[0].strip()
            else:
                ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent", "")

        log = AuditLog(
            org_id=user.org_id if user else None,
            user_id=user.id if user else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            old_value=_sanitize(old_value) if old_value else None,
            new_value=_sanitize(new_value) if new_value else None,
            ip_address=ip,
            user_agent=ua,
        )
        db.add(log)
        db.flush()  # 写入但不独立 commit（由调用方控制事务）
    except Exception as e:
        logger.warning(f"write_audit_log failed (non-fatal): {e}")
