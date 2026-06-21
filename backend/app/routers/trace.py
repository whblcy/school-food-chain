"""追溯路由 — 多租户 org_id 隔离"""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.audit_utils import write_audit_log
from app.auth import get_tenant, require_roles
from app.database import get_db
from app.models import (
    User, UserRole,
    Ingredient as IngredientModel,
    StockIn as StockInModel,
    Supplier as SupplierModel,
    TraceRecord,
)
from app.schemas import TraceRecord as TraceRecordOut

router = APIRouter()


def _enrich_trace(record: TraceRecord, db: Session, ing_map: dict = None, sup_map: dict = None) -> dict:
    """补充 ingredient_name / supplier_name，支持外部预加载的 map。"""
    if ing_map is None:
        ing = db.query(IngredientModel).filter(IngredientModel.id == record.ingredient_id).first()
        ingredient_name = ing.name if ing else None
    else:
        ingredient_name = ing_map.get(record.ingredient_id)

    if sup_map is None:
        supplier_name = None
        if record.supplier_id:
            sup = db.query(SupplierModel).filter(SupplierModel.id == record.supplier_id).first()
            supplier_name = sup.name if sup else None
    else:
        supplier_name = sup_map.get(record.supplier_id) if record.supplier_id else None

    d = TraceRecordOut.model_validate(record).model_dump()
    d["ingredient_name"] = ingredient_name
    d["supplier_name"] = supplier_name
    return d


@router.get("/", response_model=List[TraceRecordOut])
def list_trace_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
):
    """追溯记录列表（当前租户）— 批量加载关联名称"""
    q = tenant.filter(TraceRecord, db.query(TraceRecord))
    records = q.order_by(TraceRecord.created_at.desc()).offset(skip).limit(limit).all()

    ing_ids = {r.ingredient_id for r in records}
    sup_ids = {r.supplier_id for r in records if r.supplier_id}
    ing_map = (
        {i.id: i.name for i in db.query(IngredientModel).filter(IngredientModel.id.in_(ing_ids)).all()}
        if ing_ids else {}
    )
    sup_map = (
        {s.id: s.name for s in db.query(SupplierModel).filter(SupplierModel.id.in_(sup_ids)).all()}
        if sup_ids else {}
    )

    return [_enrich_trace(r, db, ing_map, sup_map) for r in records]


@router.post("/generate/{ingredient_id}")
def generate_trace_code(
    ingredient_id: int,
    request: Request,
    stock_in_id: int | None = None,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    """生成追溯码 — 仅允许对本组织的食材/入库记录"""
    # 校验食材归属
    ing = tenant.filter(IngredientModel, db.query(IngredientModel)).filter(
        IngredientModel.id == ingredient_id
    ).first()
    if not ing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="食材不存在")

    # 如提供 stock_in_id，同样校验归属，并复制批次信息
    sin = None
    if stock_in_id is not None:
        sin = tenant.filter(StockInModel, db.query(StockInModel)).filter(
            StockInModel.id == stock_in_id
        ).first()
        if not sin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="入库记录不存在")
        # 校验入库记录与食材一致性
        if sin.ingredient_id != ingredient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="入库记录与食材不匹配",
            )

    trace_code = f"TR{uuid.uuid4().hex[:16].upper()}"
    record = TraceRecord(
        trace_code=trace_code,
        ingredient_id=ingredient_id,
        stock_in_id=stock_in_id,
        batch_no=sin.batch_no if sin else None,
        supplier_id=sin.supplier_id if sin else None,
        production_date=sin.production_date if sin else None,
        expiry_date=sin.expiry_date if sin else None,
        trace_data={},
    )
    tenant.assign(record)
    db.add(record)
    write_audit_log(
        db, request, current_user,
        action="trace_generate", target_type="trace_record", target_id=None,
        new_value={
            "trace_code": trace_code,
            "ingredient_id": ingredient_id,
            "stock_in_id": stock_in_id,
            "batch_no": sin.batch_no if sin else None,
        },
    )
    db.commit()
    db.refresh(record)

    return {"trace_code": trace_code, "qr_url": f"/api/v1/trace/{trace_code}"}


@router.get("/{trace_code}", response_model=TraceRecordOut)
def trace_by_code(
    trace_code: str,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
):
    """扫码追溯 — 按当前租户过滤"""
    record = tenant.filter(TraceRecord, db.query(TraceRecord)).filter(
        TraceRecord.trace_code == trace_code
    ).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="追溯记录不存在")

    return _enrich_trace(record, db)
