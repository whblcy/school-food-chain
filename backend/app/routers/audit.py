"""Audit logs router"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import AuditLog, User

router = APIRouter()


@router.get("/")
def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: int = None,
    action: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """审计日志查询"""
    query = db.query(AuditLog)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    
    logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return [{
        "id": log.id,
        "user_id": log.user_id,
        "action": log.action,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "old_value": log.old_value,
        "new_value": log.new_value,
        "ip_address": log.ip_address,
        "created_at": log.created_at
    } for log in logs]
