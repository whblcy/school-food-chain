"""Audit logs router — 仅 ADMIN/SUPER_ADMIN 可查，按 org_id 隔离"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.auth import require_roles
from app.models import AuditLog, User, UserRole
from app.schemas import AuditLog as AuditLogOut

router = APIRouter()


@router.get("/", response_model=List[AuditLogOut])
def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    """审计日志查询 — SUPER_ADMIN 看全部，ADMIN 只看本组织"""
    query = db.query(AuditLog)
    # ADMIN 只能看本组织审计日志，SUPER_ADMIN 看全部
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(AuditLog.org_id == current_user.org_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    if target_id is not None:
        query = query.filter(AuditLog.target_id == target_id)

    logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    # 批量加载 username，避免 N+1
    user_ids = {log.user_id for log in logs if log.user_id is not None}
    user_map = (
        {u.id: u.username for u in db.query(User).filter(User.id.in_(user_ids)).all()}
        if user_ids else {}
    )

    result = []
    for log in logs:
        d = AuditLogOut.model_validate(log).model_dump()
        d["username"] = user_map.get(log.user_id) if log.user_id else None
        result.append(d)
    return result
