"""Traceability router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app.auth import get_current_user
from app.models import TraceRecord, User
from app.schemas import User as UserSchema

router = APIRouter()


@router.post("/generate/{ingredient_id}")
def generate_trace_code(
    ingredient_id: int,
    stock_in_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """生成追溯码"""
    trace_code = f"TR{uuid.uuid4().hex[:16].upper()}"
    
    record = TraceRecord(
        trace_code=trace_code,
        ingredient_id=ingredient_id,
        stock_in_id=stock_in_id,
        trace_data={}
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    
    return {"trace_code": trace_code, "qr_url": f"/api/v1/trace/{trace_code}"}


@router.get("/{trace_code}")
def trace_by_code(
    trace_code: str,
    db: Session = Depends(get_db)
):
    """扫码追溯"""
    record = db.query(TraceRecord).filter(TraceRecord.trace_code == trace_code).first()
    if not record:
        raise HTTPException(status_code=404, detail="Trace record not found")
    
    return {
        "trace_code": record.trace_code,
        "ingredient_id": record.ingredient_id,
        "batch_no": record.batch_no,
        "production_date": record.production_date,
        "expiry_date": record.expiry_date,
        "test_report": record.test_report,
        "quarantine_cert": record.quarantine_cert,
        "created_at": record.created_at
    }
