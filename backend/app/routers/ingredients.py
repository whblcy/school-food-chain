"""食材管理路由 — 多租户 org_id 隔离 + 角色权限"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.auth import get_tenant, require_roles
from app.models import (
    User, UserRole,
    Ingredient as IngredientModel,
    Supplier as SupplierModel,
    Category as CategoryModel,
    StockIn as StockInModel, StockOut as StockOutModel,
)
from app.schemas import IngredientCreate, Ingredient
from app.audit_utils import write_audit_log

router = APIRouter()


def _get_for_update(db: Session, ingredient_id: int, tenant) -> IngredientModel:
    query = tenant.filter(IngredientModel, db.query(IngredientModel))
    obj = query.filter(IngredientModel.id == ingredient_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="食材不存在")
    return obj


def _validate_supplier(db: Session, supplier_id: Optional[int], tenant) -> None:
    """校验供应商属于当前租户。"""
    if supplier_id is None:
        return
    sup = tenant.filter(SupplierModel, db.query(SupplierModel)).filter(
        SupplierModel.id == supplier_id
    ).first()
    if not sup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="供应商不存在")


def _enrich_ingredient(obj: IngredientModel, db: Session) -> dict:
    """补充 category_name / supplier_name。"""
    cat = db.query(CategoryModel).filter(CategoryModel.id == obj.category_id).first() if obj.category_id else None
    sup = db.query(SupplierModel).filter(SupplierModel.id == obj.supplier_id).first() if obj.supplier_id else None
    d = Ingredient.model_validate(obj).model_dump()
    d["category_name"] = cat.name if cat else None
    d["supplier_name"] = sup.name if sup else None
    return d


@router.get("/", response_model=List[Ingredient])
def list_ingredients(
    skip: int = 0,
    limit: int = Query(100, ge=1, le=500),
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
):
    query = tenant.filter(IngredientModel, db.query(IngredientModel))
    if category_id:
        query = query.filter(IngredientModel.category_id == category_id)
    records = query.offset(skip).limit(limit).all()
    # 批量加载关联名称，避免 N+1
    cat_ids = {r.category_id for r in records if r.category_id}
    sup_ids = {r.supplier_id for r in records if r.supplier_id}
    cat_map = {c.id: c.name for c in db.query(CategoryModel).filter(CategoryModel.id.in_(cat_ids)).all()} if cat_ids else {}
    sup_map = {s.id: s.name for s in db.query(SupplierModel).filter(SupplierModel.id.in_(sup_ids)).all()} if sup_ids else {}
    result = []
    for r in records:
        d = Ingredient.model_validate(r).model_dump()
        d["category_name"] = cat_map.get(r.category_id) if r.category_id else None
        d["supplier_name"] = sup_map.get(r.supplier_id) if r.supplier_id else None
        result.append(d)
    return result


@router.post("/", response_model=Ingredient)
def create_ingredient(
    ingredient: IngredientCreate,
    request: Request,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    # code 查重
    if ingredient.code:
        existing = tenant.filter(IngredientModel, db.query(IngredientModel)).filter(
            IngredientModel.code == ingredient.code
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="食材编码已存在")
    # 校验供应商归属
    _validate_supplier(db, ingredient.supplier_id, tenant)
    obj = IngredientModel(**ingredient.model_dump())
    tenant.assign(obj)
    db.add(obj)
    write_audit_log(
        db, request, current_user,
        action="create", target_type="ingredient", target_id=None,
        new_value=ingredient.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(obj)
    return _enrich_ingredient(obj, db)


@router.get("/{ingredient_id}", response_model=Ingredient)
def get_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
):
    obj = _get_for_update(db, ingredient_id, tenant)
    return _enrich_ingredient(obj, db)


@router.put("/{ingredient_id}", response_model=Ingredient)
def update_ingredient(
    ingredient_id: int,
    ingredient: IngredientCreate,
    request: Request,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    obj = _get_for_update(db, ingredient_id, tenant)
    old_value = Ingredient.model_validate(obj).model_dump(mode="json")
    update_data = ingredient.model_dump(exclude_unset=True)
    # 校验供应商归属（仅当显式传入 supplier_id 时）
    if "supplier_id" in update_data:
        _validate_supplier(db, update_data["supplier_id"], tenant)
    for key, value in update_data.items():
        setattr(obj, key, value)
    write_audit_log(
        db, request, current_user,
        action="update", target_type="ingredient", target_id=obj.id,
        old_value=old_value,
        new_value=ingredient.model_dump(exclude_unset=True, mode="json"),
    )
    db.commit()
    db.refresh(obj)
    return _enrich_ingredient(obj, db)


@router.delete("/{ingredient_id}")
def delete_ingredient(
    ingredient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    obj = _get_for_update(db, ingredient_id, tenant)
    # 级联保护：有库存记录时阻止删除
    ref_count = tenant.filter(StockInModel, db.query(StockInModel)).filter(
        StockInModel.ingredient_id == ingredient_id
    ).count()
    ref_count += tenant.filter(StockOutModel, db.query(StockOutModel)).filter(
        StockOutModel.ingredient_id == ingredient_id
    ).count()
    if ref_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该食材仍有 {ref_count} 条库存记录，无法删除",
        )
    write_audit_log(
        db, request, current_user,
        action="delete", target_type="ingredient", target_id=obj.id,
        old_value={"name": obj.name, "code": obj.code},
    )
    db.delete(obj)
    db.commit()
    return {"message": "Ingredient deleted"}
