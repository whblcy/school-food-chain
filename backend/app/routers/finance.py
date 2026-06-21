"""财务路由 — 多租户 org_id 隔离"""
from datetime import datetime, date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.auth import get_tenant, require_roles
from app.cache import cached
from app.database import get_db
from app.models import Category, Ingredient, StockIn, StockOut, User, UserRole

router = APIRouter()


def _in_q(db, tenant):
    return tenant.filter(StockIn, db.query(StockIn))


def _out_q(db, tenant):
    return tenant.filter(StockOut, db.query(StockOut))


def _month_range(year: int, month: int) -> tuple[date, date]:
    """返回 [month_start, next_month_start) 的日期范围，用于索引友好的范围查询。"""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


@router.get("/monthly-summary")
@cached(ttl=120, key_prefix="finance:monthly_summary")
def monthly_summary(
    year: int = Query(default_factory=lambda: datetime.now().year, ge=2000, le=2100),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12),
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPER_ADMIN)),
):
    """月度财务汇总（当前租户）"""
    start, end = _month_range(year, month)
    in_q = _in_q(db, tenant).filter(
        StockIn.created_at >= start,
        StockIn.created_at < end,
    )
    out_q = _out_q(db, tenant).filter(
        StockOut.created_at >= start,
        StockOut.created_at < end,
    )

    total_in = in_q.with_entities(func.coalesce(func.sum(StockIn.total_price), 0)).scalar()
    total_out = out_q.with_entities(func.coalesce(func.sum(StockOut.total_price), 0)).scalar()

    return {
        "year": year,
        "month": month,
        "total_in": float(total_in or 0),
        "total_out": float(total_out or 0),
        "balance": float((total_in or 0) - (total_out or 0)),
    }


@router.get("/yearly-trend")
@cached(ttl=300, key_prefix="finance:yearly_trend")
def yearly_trend(
    year: int = Query(default_factory=lambda: datetime.now().year, ge=2000, le=2100),
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPER_ADMIN)),
):
    """年度月度趋势（当前租户）— 单次 GROUP BY 查询，避免 N+1"""
    year_start = date(year, 1, 1)
    year_end = date(year + 1, 1, 1)

    # 入库：按月聚合
    in_rows = _in_q(db, tenant).filter(
        StockIn.created_at >= year_start,
        StockIn.created_at < year_end,
    ).with_entities(
        extract("month", StockIn.created_at).label("m"),
        func.coalesce(func.sum(StockIn.total_price), 0).label("amount"),
    ).group_by("m").all()
    in_map = {int(r.m): float(r.amount or 0) for r in in_rows}

    # 出库：按月聚合
    out_rows = _out_q(db, tenant).filter(
        StockOut.created_at >= year_start,
        StockOut.created_at < year_end,
    ).with_entities(
        extract("month", StockOut.created_at).label("m"),
        func.coalesce(func.sum(StockOut.total_price), 0).label("amount"),
    ).group_by("m").all()
    out_map = {int(r.m): float(r.amount or 0) for r in out_rows}

    # 补齐无数据的月份
    return [
        {
            "month": m,
            "in_amount": in_map.get(m, 0.0),
            "out_amount": out_map.get(m, 0.0),
        }
        for m in range(1, 13)
    ]


@router.get("/category-breakdown")
@cached(ttl=120, key_prefix="finance:category_breakdown")
def category_breakdown(
    year: int = Query(default_factory=lambda: datetime.now().year, ge=2000, le=2100),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12),
    db: Session = Depends(get_db),
    tenant=Depends(get_tenant),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPER_ADMIN)),
):
    """按分类统计采购金额（当前租户）"""
    start, end = _month_range(year, month)
    # 先按租户过滤 stock_in，再关联分类
    stock_in_subq = _in_q(db, tenant).filter(
        StockIn.created_at >= start,
        StockIn.created_at < end,
    ).subquery()

    results = db.query(
        Category.name,
        func.coalesce(func.sum(stock_in_subq.c.total_price), 0).label("amount"),
    ).select_from(stock_in_subq).join(
        Ingredient, Ingredient.id == stock_in_subq.c.ingredient_id
    ).join(
        Category, Category.id == Ingredient.category_id
    ).group_by(Category.name).all()

    return [{"category": r.name, "amount": float(r.amount)} for r in results]
