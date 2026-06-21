"""库存管理路由 — 多租户 org_id 隔离 + 行锁防竞态 + 审计日志"""
from __future__ import annotations

import uuid
from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.auth import get_tenant, require_roles
from app.database import get_db
from app.models import (
    User, UserRole,
    Ingredient as IngredientModel,
    Supplier as SupplierModel,
    StockIn as StockInModel,
    StockOut as StockOutModel,
    InventoryCheck as InventoryCheckModel,
    SupplierStatus,
)
from app.schemas import (
    StockInCreate, StockOutCreate, InventoryCheckCreate,
    StockIn as StockInOut, StockOut as StockOutOut, InventoryCheck as InventoryCheckOut,
)
from app.audit_utils import write_audit_log
from app.cache import invalidate_pattern
from app.websocket import publish_stock_update, publish_low_stock_alert

router = APIRouter()


def _invalidate_stock_cache():
    """入库/出库/盘点后失效相关报表缓存。"""
    invalidate_pattern("reports:*")
    invalidate_pattern("finance:*")
    invalidate_pattern("gov:*")


def _check_and_alert_low_stock(ingredient: IngredientModel, org_id: int) -> None:
    """检查库存是否低于安全线，若低于则推送实时告警。"""
    try:
        current = float(ingredient.current_stock or 0)
        safety = float(ingredient.safety_stock or 0)
        if current <= safety:
            publish_low_stock_alert(
                ingredient_name=ingredient.name,
                current_stock=current,
                safety_stock=safety,
                unit=ingredient.unit or "",
                org_id=org_id,
            )
    except Exception:
        pass  # 告警推送失败不影响主流程


# ---------------------------------------------------------------------------
# 辅助 — 校验食材/供应商归属（加行锁防并发）
# ---------------------------------------------------------------------------
def _get_ingredient_for_update(db: Session, ingredient_id: int, tenant) -> IngredientModel:
    q = tenant.filter(IngredientModel, db.query(IngredientModel))
    ing = q.filter(IngredientModel.id == ingredient_id).with_for_update().first()
    if not ing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="食材不存在")
    return ing


def _validate_supplier(db: Session, supplier_id: Optional[int], tenant) -> None:
    """校验供应商属于当前租户且未被拉黑。"""
    if supplier_id is None:
        return
    sup = tenant.filter(SupplierModel, db.query(SupplierModel)).filter(
        SupplierModel.id == supplier_id
    ).first()
    if not sup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="供应商不存在")
    if sup.status == SupplierStatus.BLACKLISTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"供应商 {sup.name} 已被列入黑名单，禁止入库",
        )


def _validate_user_in_org(db: Session, user_id: Optional[int], tenant) -> None:
    """校验用户属于当前租户组织。"""
    if user_id is None:
        return
    from app.models import User as UserModel
    u = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="验收人不存在")
    if not tenant.is_cross_org and u.org_id != tenant.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="验收人不在当前组织")


# ---------------------------------------------------------------------------
# 入库
# ---------------------------------------------------------------------------
@router.post("/in", response_model=StockInOut)
def stock_in(
    data: StockInCreate,
    request: Request,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    ingredient = _get_ingredient_for_update(db, data.ingredient_id, tenant)
    _validate_supplier(db, data.supplier_id, tenant)
    _validate_user_in_org(db, data.inspector1_id, tenant)
    _validate_user_in_org(db, data.inspector2_id, tenant)

    batch_no = f"IN{uuid.uuid4().hex[:12].upper()}"
    record = StockInModel(
        batch_no=batch_no,
        ingredient_id=data.ingredient_id,
        quantity=data.quantity,
        unit_price=data.unit_price,
        total_price=data.quantity * data.unit_price,
        supplier_id=data.supplier_id,
        production_date=data.production_date,
        expiry_date=data.expiry_date,
        batch_number=data.batch_number,
        inspector1_id=data.inspector1_id,
        inspector2_id=data.inspector2_id,
        operator_id=tenant.user.id,
        remark=data.remark,
    )
    tenant.assign(record)
    db.add(record)

    ingredient.current_stock += data.quantity
    write_audit_log(
        db, request, current_user,
        action="stock_in", target_type="stock_in", target_id=None,
        new_value={"batch_no": batch_no, "ingredient_id": data.ingredient_id,
                   "quantity": str(data.quantity), "unit_price": str(data.unit_price)},
    )
    db.commit()
    db.refresh(record)
    _invalidate_stock_cache()
    # 实时推送入库通知 + 低库存检查
    publish_stock_update("stock_in", ingredient.name, float(data.quantity), ingredient.org_id or 0)
    _check_and_alert_low_stock(ingredient, ingredient.org_id or 0)
    return _enrich_stock_in(record, db)


def _enrich_stock_in(record: StockInModel, db: Session) -> dict:
    """补充 ingredient_name / supplier_name。"""
    ing = db.query(IngredientModel).filter(IngredientModel.id == record.ingredient_id).first()
    sup = db.query(SupplierModel).filter(SupplierModel.id == record.supplier_id).first() if record.supplier_id else None
    return {
        **StockInOut.model_validate(record).model_dump(),
        "ingredient_name": ing.name if ing else None,
        "supplier_name": sup.name if sup else None,
    }


# ---------------------------------------------------------------------------
# 出库
# ---------------------------------------------------------------------------
@router.post("/out", response_model=StockOutOut)
def stock_out(
    data: StockOutCreate,
    request: Request,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    ingredient = _get_ingredient_for_update(db, data.ingredient_id, tenant)

    if ingredient.current_stock < data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="库存不足，无法出库",
        )

    record = StockOutModel(
        ingredient_id=data.ingredient_id,
        quantity=data.quantity,
        unit_price=data.unit_price,
        total_price=data.quantity * (data.unit_price or 0),
        purpose=data.purpose,
        department=data.department,
        operator_id=tenant.user.id,
        remark=data.remark,
    )
    tenant.assign(record)
    db.add(record)

    ingredient.current_stock -= data.quantity
    write_audit_log(
        db, request, current_user,
        action="stock_out", target_type="stock_out", target_id=None,
        new_value={"ingredient_id": data.ingredient_id,
                   "quantity": str(data.quantity), "purpose": data.purpose},
    )
    db.commit()
    db.refresh(record)
    ing = db.query(IngredientModel).filter(IngredientModel.id == record.ingredient_id).first()
    out = StockOutOut.model_validate(record)
    out.ingredient_name = ing.name if ing else None
    _invalidate_stock_cache()
    # 实时推送出库通知 + 低库存检查
    if ing:
        publish_stock_update("stock_out", ing.name, float(data.quantity), ing.org_id or 0)
        _check_and_alert_low_stock(ing, ing.org_id or 0)
    return out


# ---------------------------------------------------------------------------
# 盘点
# ---------------------------------------------------------------------------
@router.post("/check", response_model=InventoryCheckOut)
def inventory_check(
    data: InventoryCheckCreate,
    request: Request,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    ingredient = _get_ingredient_for_update(db, data.ingredient_id, tenant)

    system_stock = ingredient.current_stock
    difference = data.actual_stock - system_stock
    record = InventoryCheckModel(
        ingredient_id=data.ingredient_id,
        system_stock=system_stock,
        actual_stock=data.actual_stock,
        difference=difference,
        operator_id=tenant.user.id,
        remark=data.remark,
    )
    tenant.assign(record)
    db.add(record)
    ingredient.current_stock = data.actual_stock
    write_audit_log(
        db, request, current_user,
        action="inventory_check", target_type="inventory_check", target_id=None,
        new_value={"ingredient_id": data.ingredient_id,
                   "system_stock": str(system_stock),
                   "actual_stock": str(data.actual_stock),
                   "difference": str(difference)},
    )
    db.commit()
    db.refresh(record)
    ing = db.query(IngredientModel).filter(IngredientModel.id == record.ingredient_id).first()
    out = InventoryCheckOut.model_validate(record)
    out.ingredient_name = ing.name if ing else None
    _invalidate_stock_cache()
    # 实时推送盘点通知 + 低库存检查
    if ing:
        publish_stock_update("inventory_check", ing.name, float(data.actual_stock), ing.org_id or 0)
        _check_and_alert_low_stock(ing, ing.org_id or 0)
    return out


# ---------------------------------------------------------------------------
# 列表
# ---------------------------------------------------------------------------
@router.get("/in", response_model=List[StockInOut])
def list_stock_in(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    ingredient_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
):
    q = tenant.filter(StockInModel, db.query(StockInModel))
    if ingredient_id:
        q = q.filter(StockInModel.ingredient_id == ingredient_id)
    if supplier_id:
        q = q.filter(StockInModel.supplier_id == supplier_id)
    records = q.order_by(StockInModel.created_at.desc()).offset(skip).limit(limit).all()
    # 批量加载关联名称，避免 N+1
    ing_ids = {r.ingredient_id for r in records}
    sup_ids = {r.supplier_id for r in records if r.supplier_id}
    ing_map = {i.id: i.name for i in db.query(IngredientModel).filter(IngredientModel.id.in_(ing_ids)).all()} if ing_ids else {}
    sup_map = {s.id: s.name for s in db.query(SupplierModel).filter(SupplierModel.id.in_(sup_ids)).all()} if sup_ids else {}
    result = []
    for r in records:
        d = StockInOut.model_validate(r).model_dump()
        d["ingredient_name"] = ing_map.get(r.ingredient_id)
        d["supplier_name"] = sup_map.get(r.supplier_id) if r.supplier_id else None
        result.append(d)
    return result


@router.get("/out", response_model=List[StockOutOut])
def list_stock_out(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    ingredient_id: Optional[int] = None,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
):
    q = tenant.filter(StockOutModel, db.query(StockOutModel))
    if ingredient_id:
        q = q.filter(StockOutModel.ingredient_id == ingredient_id)
    records = q.order_by(StockOutModel.created_at.desc()).offset(skip).limit(limit).all()
    ing_ids = {r.ingredient_id for r in records}
    ing_map = {i.id: i.name for i in db.query(IngredientModel).filter(IngredientModel.id.in_(ing_ids)).all()} if ing_ids else {}
    result = []
    for r in records:
        d = StockOutOut.model_validate(r).model_dump()
        d["ingredient_name"] = ing_map.get(r.ingredient_id)
        result.append(d)
    return result


@router.get("/check", response_model=List[InventoryCheckOut])
def list_inventory_checks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    ingredient_id: Optional[int] = None,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
):
    """盘点记录列表 — 补齐前端缺失的 GET /stock/check 端点。"""
    q = tenant.filter(InventoryCheckModel, db.query(InventoryCheckModel))
    if ingredient_id:
        q = q.filter(InventoryCheckModel.ingredient_id == ingredient_id)
    records = q.order_by(InventoryCheckModel.created_at.desc()).offset(skip).limit(limit).all()
    ing_ids = {r.ingredient_id for r in records}
    ing_map = {i.id: i.name for i in db.query(IngredientModel).filter(IngredientModel.id.in_(ing_ids)).all()} if ing_ids else {}
    result = []
    for r in records:
        d = InventoryCheckOut.model_validate(r).model_dump()
        d["ingredient_name"] = ing_map.get(r.ingredient_id)
        result.append(d)
    return result
