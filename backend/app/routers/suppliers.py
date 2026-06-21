"""供应商路由 — 多租户 org_id 隔离 + 角色权限"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.auth import get_tenant, require_roles
from app.models import (
    User, UserRole, SupplierStatus,
    Supplier as SupplierModel, Ingredient as IngredientModel,
)
from app.schemas import SupplierCreate, SupplierUpdate, Supplier, SupplierBlacklist
from app.audit_utils import write_audit_log
from app.cache import invalidate_pattern
from app.websocket import publish_blacklist_alert

router = APIRouter()


def _get_for_update(db: Session, supplier_id: int, tenant) -> SupplierModel:
    query = tenant.filter(SupplierModel, db.query(SupplierModel))
    obj = query.filter(SupplierModel.id == supplier_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="供应商不存在")
    return obj


@router.get("/", response_model=List[Supplier])
def list_suppliers(
    skip: int = 0,
    limit: int = Query(100, ge=1, le=500),
    status: Optional[SupplierStatus] = None,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
):
    query = tenant.filter(SupplierModel, db.query(SupplierModel))
    if status:
        query = query.filter(SupplierModel.status == status)
    return query.offset(skip).limit(limit).all()


@router.post("/", response_model=Supplier)
def create_supplier(
    supplier: SupplierCreate,
    request: Request,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    # code 查重
    if supplier.code:
        existing = tenant.filter(SupplierModel, db.query(SupplierModel)).filter(
            SupplierModel.code == supplier.code
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="供应商编码已存在")
    obj = SupplierModel(**supplier.model_dump())
    tenant.assign(obj)
    db.add(obj)
    write_audit_log(
        db, request, current_user,
        action="create", target_type="supplier", target_id=None,
        new_value=supplier.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{supplier_id}", response_model=Supplier)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
):
    return _get_for_update(db, supplier_id, tenant)


@router.put("/{supplier_id}", response_model=Supplier)
def update_supplier(
    supplier_id: int,
    supplier: SupplierUpdate,
    request: Request,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    obj = _get_for_update(db, supplier_id, tenant)
    old_value = Supplier.model_validate(obj).model_dump(mode="json")
    update_data = supplier.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(obj, key, value)
    write_audit_log(
        db, request, current_user,
        action="update", target_type="supplier", target_id=obj.id,
        old_value=old_value,
        new_value=supplier.model_dump(exclude_unset=True, mode="json"),
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{supplier_id}")
def delete_supplier(
    supplier_id: int,
    request: Request,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    obj = _get_for_update(db, supplier_id, tenant)
    # 级联保护：有食材引用时阻止删除
    ref_count = tenant.filter(IngredientModel, db.query(IngredientModel)).filter(
        IngredientModel.supplier_id == supplier_id
    ).count()
    if ref_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该供应商仍有 {ref_count} 个关联食材，无法删除",
        )
    write_audit_log(
        db, request, current_user,
        action="delete", target_type="supplier", target_id=obj.id,
        old_value={"name": obj.name, "code": obj.code},
    )
    db.delete(obj)
    db.commit()
    return {"message": "Supplier deleted"}


@router.post("/{supplier_id}/blacklist", response_model=Supplier)
def blacklist_supplier(
    supplier_id: int,
    payload: SupplierBlacklist,
    request: Request,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    obj = _get_for_update(db, supplier_id, tenant)
    old_value = {
        "status": obj.status.value if obj.status else None,
        "blacklist_reason": obj.blacklist_reason,
    }
    obj.status = SupplierStatus.BLACKLISTED
    obj.blacklist_reason = payload.reason
    write_audit_log(
        db, request, current_user,
        action="blacklist", target_type="supplier", target_id=obj.id,
        old_value=old_value,
        new_value={"status": obj.status.value, "blacklist_reason": payload.reason},
    )
    db.commit()
    db.refresh(obj)
    # 失效缓存 + 推送黑名单告警
    invalidate_pattern("gov:*")
    invalidate_pattern("reports:*")
    publish_blacklist_alert(obj.name, payload.reason, obj.org_id or 0)
    return obj


@router.post("/{supplier_id}/unblacklist", response_model=Supplier)
def unblacklist_supplier(
    supplier_id: int,
    request: Request,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    obj = _get_for_update(db, supplier_id, tenant)
    old_value = {
        "status": obj.status.value if obj.status else None,
        "blacklist_reason": obj.blacklist_reason,
    }
    obj.status = SupplierStatus.ACTIVE
    obj.blacklist_reason = None
    write_audit_log(
        db, request, current_user,
        action="unblacklist", target_type="supplier", target_id=obj.id,
        old_value=old_value,
        new_value={"status": obj.status.value, "blacklist_reason": None},
    )
    db.commit()
    db.refresh(obj)
    return obj
