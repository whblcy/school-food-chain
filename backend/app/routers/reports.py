"""报表路由 — 多租户 org_id 隔离"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_tenant, require_roles
from app.cache import cached
from app.database import get_db
from app.models import Category, Ingredient, StockIn, User, UserRole

router = APIRouter()


@router.get("/stock-summary")
@cached(ttl=120, key_prefix="reports:stock_summary")
def stock_summary(
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPER_ADMIN)),
):
    """分类库存汇总"""
    base = tenant.filter(Ingredient, db.query(Ingredient)).filter(Ingredient.is_active.is_(True))
    subq = base.subquery()

    results = db.query(
        Category.name,
        func.count(subq.c.id).label("count"),
        func.coalesce(func.sum(subq.c.current_stock), 0).label("total_stock"),
    ).join(
        subq, subq.c.category_id == Category.id, isouter=True
    ).group_by(Category.name).all()

    return [{"category": r.name, "count": r.count, "total_stock": float(r.total_stock)} for r in results]


@router.get("/low-stock")
@cached(ttl=60, key_prefix="reports:low_stock")
def low_stock(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPER_ADMIN)),
):
    """低库存预警（当前租户）"""
    q = tenant.filter(Ingredient, db.query(Ingredient))
    items = q.filter(
        Ingredient.current_stock <= Ingredient.safety_stock,
        Ingredient.is_active.is_(True),
    ).order_by(Ingredient.id).offset(skip).limit(limit).all()
    return [
        {"id": i.id, "name": i.name, "current": i.current_stock, "safety": i.safety_stock}
        for i in items
    ]


@router.get("/inventory-value")
@cached(ttl=120, key_prefix="reports:inventory_value")
def inventory_value(
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPER_ADMIN)),
):
    """当前租户库存总值 — 基于最近一次入库单价

    修复 N+1：先批量查每个食材的最新 StockIn.unit_price（窗口函数），再在内存中计算。
    """
    ings = tenant.filter(Ingredient, db.query(Ingredient)).filter(
        Ingredient.is_active.is_(True)
    ).all()
    if not ings:
        return {"total_value": 0.0}

    ing_ids = [i.id for i in ings]
    ing_stock_map = {i.id: float(i.current_stock or 0) for i in ings}

    # 窗口函数：按 ingredient_id 分组取 created_at 最新的一条 StockIn
    inner = db.query(
        StockIn.ingredient_id,
        StockIn.unit_price,
        func.row_number().over(
            partition_by=StockIn.ingredient_id,
            order_by=StockIn.created_at.desc(),
        ).label("rn"),
    ).filter(StockIn.ingredient_id.in_(ing_ids)).subquery()

    latest_rows = db.query(
        inner.c.ingredient_id, inner.c.unit_price
    ).filter(inner.c.rn == 1).all()

    price_map = {r.ingredient_id: float(r.unit_price or 0) for r in latest_rows}

    total = sum(ing_stock_map.get(iid, 0.0) * price_map.get(iid, 0.0) for iid in ing_ids)
    return {"total_value": float(total or 0)}
