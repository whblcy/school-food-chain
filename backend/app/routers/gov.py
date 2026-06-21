"""教育局监管路由 — 提供给教育局的数据看板和上报接口。

权限策略：
- SUPER_ADMIN: 全平台数据
- ADMIN: 本组织 + 子组织数据
- 其它角色: 拒绝访问
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.cache import cached
from app.models import (
    User, UserRole, Organization, OrgType,
    StockIn, StockOut, Ingredient,
    InventoryCheck, Supplier, SupplierStatus, TraceRecord,
)

router = APIRouter()


# =========================================================================
# 权限与租户过滤辅助
# =========================================================================
def _require_gov_access(current_user=Depends(get_current_user)):
    # TODO: OrgType 枚举目前没有 EDUCATION_BUREAU 类型，暂只检查角色。
    # 待 OrgType 增加 EDUCATION_BUREAU 后，非 SUPER_ADMIN 应额外校验
    # current_user.org.org_type == OrgType.EDUCATION_BUREAU。
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="需要监管权限（admin/super_admin 角色）")
    return current_user


def _get_all_descendant_org_ids(db: Session, org_id: int) -> List[int]:
    """递归获取 org_id 的所有子孙组织 ID（包含自身）。

    采用逐层循环查询的方式，兼容 SQLite 与 PostgreSQL。
    PostgreSQL 也可用 `WITH RECURSIVE` CTE 实现，但此处为保持双库
    一致而使用循环遍历，组织层级通常较浅，性能可接受。
    """
    result: List[int] = [org_id]
    pending: List[int] = [org_id]
    while pending:
        children = (
            db.query(Organization.id)
            .filter(Organization.parent_id.in_(pending))
            .all()
        )
        child_ids = [c[0] for c in children]
        if not child_ids:
            break
        result.extend(child_ids)
        pending = child_ids
    return result


def _accessible_org_ids(db: Session, current_user) -> Optional[List[int]]:
    if current_user.role == UserRole.SUPER_ADMIN:
        return None
    if current_user.org_id is None:
        return []
    return _get_all_descendant_org_ids(db, current_user.org_id)


def _filter_by_org_ids(query, model, accessible_org_ids: Optional[List[int]]):
    if accessible_org_ids is None:
        return query
    if not accessible_org_ids:
        return query.filter(False)
    return query.filter(model.org_id.in_(accessible_org_ids))


# =========================================================================
# 统计接口
# =========================================================================
@router.get("/dashboard")
@cached(ttl=60, key_prefix="gov:dashboard")
def gov_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_gov_access),
):
    """教育局监管总览看板 — 按当前用户权限过滤数据。"""
    accessible = _accessible_org_ids(db, current_user)

    # 学校数
    org_query = db.query(Organization).filter(
        Organization.org_type.in_([OrgType.CAMPUS, OrgType.CANTEEN])
    )
    if accessible is not None:
        org_query = org_query.filter(Organization.id.in_(accessible))
    school_count = org_query.count()

    today = datetime.now().date()
    # 今日 00:00 ~ 明日 00:00，使用范围查询走索引（避免 func.date() 全表扫描）
    today_start = datetime.combine(today, datetime.min.time())
    tomorrow_start = datetime.combine(today + timedelta(days=1), datetime.min.time())

    # 今日出入库（仅统计可见组织的）
    stock_in_q = _filter_by_org_ids(db.query(func.coalesce(func.sum(StockIn.quantity), 0)), StockIn, accessible)
    today_in = stock_in_q.filter(
        StockIn.created_at >= today_start,
        StockIn.created_at < tomorrow_start,
    ).scalar() or 0

    stock_out_q = _filter_by_org_ids(db.query(func.coalesce(func.sum(StockOut.quantity), 0)), StockOut, accessible)
    today_out = stock_out_q.filter(
        StockOut.created_at >= today_start,
        StockOut.created_at < tomorrow_start,
    ).scalar() or 0

    # 低库存预警数
    low_stock_q = _filter_by_org_ids(db.query(Ingredient), Ingredient, accessible)
    low_stock_count = low_stock_q.filter(
        Ingredient.current_stock <= Ingredient.safety_stock
    ).count()

    # 供应商总数（按可见组织过滤）
    supplier_q = _filter_by_org_ids(db.query(Supplier), Supplier, accessible)
    supplier_count = supplier_q.count()
    active_supplier_count = supplier_q.filter(
        Supplier.status == SupplierStatus.ACTIVE
    ).count()

    # 最近 7 天趋势（按可见组织过滤）— 单次 GROUP BY 查询，内存补齐 7 天
    seven_days_ago = datetime.combine(today - timedelta(days=6), datetime.min.time())
    trend_in_rows = (
        _filter_by_org_ids(
            db.query(
                func.date(StockIn.created_at).label("d"),
                func.coalesce(func.sum(StockIn.quantity), 0).label("s"),
            ),
            StockIn, accessible,
        )
        .filter(StockIn.created_at >= seven_days_ago)
        .group_by(func.date(StockIn.created_at))
        .all()
    )
    trend_in_map = {str(r.d): float(r.s) for r in trend_in_rows}

    trend_out_rows = (
        _filter_by_org_ids(
            db.query(
                func.date(StockOut.created_at).label("d"),
                func.coalesce(func.sum(StockOut.quantity), 0).label("s"),
            ),
            StockOut, accessible,
        )
        .filter(StockOut.created_at >= seven_days_ago)
        .group_by(func.date(StockOut.created_at))
        .all()
    )
    trend_out_map = {str(r.d): float(r.s) for r in trend_out_rows}

    trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_key = day.isoformat()
        trend.append({
            "date": day_key,
            "stock_in": trend_in_map.get(day_key, 0.0),
            "stock_out": trend_out_map.get(day_key, 0.0),
        })

    return {
        "school_count": school_count,
        "today_stock_in": float(today_in),
        "today_stock_out": float(today_out),
        "low_stock_alert": low_stock_count,
        "supplier_count": supplier_count,
        "active_supplier_count": active_supplier_count,
        "weekly_trend": trend,
    }


@router.get("/schools")
@cached(ttl=60, key_prefix="gov:schools")
def list_schools(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_gov_access),
):
    """学校列表及关键指标。"""
    accessible = _accessible_org_ids(db, current_user)

    org_query = db.query(Organization).filter(
        Organization.org_type.in_([OrgType.CAMPUS, OrgType.CANTEEN])
    )
    if accessible is not None:
        org_query = org_query.filter(Organization.id.in_(accessible))
    schools = org_query.offset(skip).limit(limit).all()

    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    tomorrow_start = datetime.combine(today + timedelta(days=1), datetime.min.time())
    school_ids = [s.id for s in schools]

    # 一次性聚合所有学校的 ingredient_count / low_count / today_in，消除 N+1
    if school_ids:
        ingredient_rows = (
            db.query(
                Ingredient.org_id,
                func.count(Ingredient.id).label("c"),
            )
            .filter(Ingredient.org_id.in_(school_ids))
            .group_by(Ingredient.org_id)
            .all()
        )
        ingredient_map = {r[0]: r[1] for r in ingredient_rows}

        low_rows = (
            db.query(
                Ingredient.org_id,
                func.count(Ingredient.id).label("c"),
            )
            .filter(Ingredient.org_id.in_(school_ids))
            .filter(Ingredient.current_stock <= Ingredient.safety_stock)
            .group_by(Ingredient.org_id)
            .all()
        )
        low_map = {r[0]: r[1] for r in low_rows}

        today_in_rows = (
            db.query(
                StockIn.org_id,
                func.coalesce(func.sum(StockIn.total_price), 0).label("s"),
            )
            .filter(StockIn.org_id.in_(school_ids))
            .filter(StockIn.created_at >= today_start)
            .filter(StockIn.created_at < tomorrow_start)
            .group_by(StockIn.org_id)
            .all()
        )
        today_in_map = {r[0]: float(r[1]) for r in today_in_rows}
    else:
        ingredient_map = {}
        low_map = {}
        today_in_map = {}

    result = []
    for school in schools:
        result.append({
            "id": school.id,
            "name": school.name,
            "code": school.code,
            "org_type": school.org_type.value,
            "ingredient_count": ingredient_map.get(school.id, 0),
            "today_purchase": today_in_map.get(school.id, 0.0),
            "low_stock_count": low_map.get(school.id, 0),
            "is_active": school.is_active,
        })
    return result


@router.get("/schools/{school_id}/detail")
def school_detail(
    school_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_gov_access),
):
    """单个学校的详细监管数据 — 权限检查确保学校在可见集合内。"""
    accessible = _accessible_org_ids(db, current_user)
    if accessible is not None and school_id not in accessible:
        raise HTTPException(status_code=404, detail="学校不在您的监管范围内")

    school = db.query(Organization).filter(Organization.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")

    ingredient_total = (
        db.query(Ingredient).filter(Ingredient.org_id == school_id).count()
    )
    ingredients = (
        db.query(Ingredient)
        .filter(Ingredient.org_id == school_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    ingredient_list = [
        {
            "id": i.id,
            "name": i.name,
            "current_stock": i.current_stock,
            "safety_stock": i.safety_stock,
            "unit": i.unit,
            "status": "正常" if i.current_stock > i.safety_stock else "预警",
        }
        for i in ingredients
    ]

    # 用于名称查找的全部食材（仅 id/name，避免分页后查不到名称）
    all_ingredient_names = {
        i.id: i.name
        for i in db.query(Ingredient.id, Ingredient.name)
        .filter(Ingredient.org_id == school_id)
        .all()
    }

    recent_in = (
        db.query(StockIn)
        .filter(StockIn.org_id == school_id)
        .order_by(StockIn.created_at.desc())
        .limit(10)
        .all()
    )
    recent_in_list = [
        {
            "batch_no": r.batch_no,
            "ingredient_name": all_ingredient_names.get(r.ingredient_id, "未知"),
            "quantity": r.quantity,
            "unit_price": r.unit_price,
            "total_price": r.total_price,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_in
    ]

    recent_check = (
        db.query(InventoryCheck)
        .filter(InventoryCheck.org_id == school_id)
        .order_by(InventoryCheck.created_at.desc())
        .limit(5)
        .all()
    )
    check_list = [
        {
            "ingredient_name": all_ingredient_names.get(c.ingredient_id, "未知"),
            "system_stock": c.system_stock,
            "actual_stock": c.actual_stock,
            "difference": c.difference,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in recent_check
    ]

    return {
        "school": {
            "id": school.id,
            "name": school.name,
            "code": school.code,
            "address": school.address,
            "contact_person": school.contact_person,
            "contact_phone": school.contact_phone,
        },
        "ingredients": ingredient_list,
        "ingredient_total": ingredient_total,
        "recent_stock_in": recent_in_list,
        "recent_inventory_checks": check_list,
    }


@router.get("/alerts")
@cached(ttl=30, key_prefix="gov:alerts")
def get_alerts(
    alert_type: Optional[str] = Query(None, description="alert类型: low_stock, expiry, supplier"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_gov_access),
):
    """各类预警。"""
    accessible = _accessible_org_ids(db, current_user)

    alerts = []
    now = datetime.now()

    if alert_type is None or alert_type == "low_stock":
        q = _filter_by_org_ids(db.query(Ingredient), Ingredient, accessible)
        items = q.filter(Ingredient.current_stock <= Ingredient.safety_stock).all()
        # 批量预加载相关 Organization，消除 N+1
        org_ids = {i.org_id for i in items if i.org_id}
        org_map = {
            o.id: o.name
            for o in db.query(Organization).filter(Organization.id.in_(org_ids)).all()
        } if org_ids else {}
        for item in items:
            alerts.append({
                "type": "low_stock",
                "level": "warning" if item.current_stock > 0 else "critical",
                "title": f"库存预警: {item.name}",
                "message": f"当前库存 {item.current_stock}{item.unit}，低于安全库存 {item.safety_stock}{item.unit}",
                "school_name": org_map.get(item.org_id, "未知") if item.org_id else "未知",
                "created_at": now.isoformat(),
            })

    if alert_type is None or alert_type == "expiry":
        cutoff = now + timedelta(days=30)
        q = _filter_by_org_ids(db.query(StockIn), StockIn, accessible)
        items = (
            q.filter(StockIn.expiry_date.isnot(None))
            .filter(StockIn.expiry_date <= cutoff)
            .filter(StockIn.expiry_date >= now)
            .all()
        )
        # 批量预加载相关 Ingredient 和 Organization，消除 N+1
        ingredient_ids = {i.ingredient_id for i in items if i.ingredient_id}
        org_ids = {i.org_id for i in items if i.org_id}
        ingredient_map = {
            ing.id: ing.name
            for ing in db.query(Ingredient).filter(Ingredient.id.in_(ingredient_ids)).all()
        } if ingredient_ids else {}
        org_map = {
            o.id: o.name
            for o in db.query(Organization).filter(Organization.id.in_(org_ids)).all()
        } if org_ids else {}
        for item in items:
            days_left = (item.expiry_date - now).days if item.expiry_date else 0
            alerts.append({
                "type": "expiry",
                "level": "warning" if days_left > 7 else "critical",
                "title": f"临期预警: {ingredient_map.get(item.ingredient_id, '未知食材')}",
                "message": f"批次 {item.batch_no} 将于 {days_left} 天后过期",
                "school_name": org_map.get(item.org_id, "未知") if item.org_id else "未知",
                "created_at": now.isoformat(),
            })

    if alert_type is None or alert_type == "supplier":
        blacklisted_q = _filter_by_org_ids(db.query(Supplier), Supplier, accessible)
        blacklisted = blacklisted_q.filter(Supplier.status == SupplierStatus.BLACKLISTED).all()
        for s in blacklisted:
            alerts.append({
                "type": "supplier",
                "level": "critical",
                "title": f"黑名单供应商: {s.name}",
                "message": f"供应商 {s.name} 已被列入黑名单",
                "school_name": "",
                "created_at": now.isoformat(),
            })

    total = len(alerts)
    paged = alerts[skip:skip + limit]
    return {"total": total, "items": paged}


@router.get("/reports/monthly")
def monthly_report(
    year: int = Query(default_factory=lambda: datetime.now().year),
    month: int = Query(default_factory=lambda: datetime.now().month),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_gov_access),
):
    """月度监管报告。"""
    accessible = _accessible_org_ids(db, current_user)
    from datetime import date as _date
    month_start = _date(year, month, 1)
    month_end = _date(year + 1, 1, 1) if month == 12 else _date(year, month + 1, 1)

    stock_in_q = _filter_by_org_ids(db.query(StockIn), StockIn, accessible)
    month_in = (
        stock_in_q.with_entities(func.coalesce(func.sum(StockIn.total_price), 0))
        .filter(StockIn.created_at >= month_start)
        .filter(StockIn.created_at < month_end)
        .scalar() or 0
    )

    stock_out_q = _filter_by_org_ids(db.query(StockOut), StockOut, accessible)
    month_out = (
        stock_out_q.with_entities(func.coalesce(func.sum(StockOut.total_price), 0))
        .filter(StockOut.created_at >= month_start)
        .filter(StockOut.created_at < month_end)
        .scalar() or 0
    )

    # 分类统计
    category_stats = (
        db.query(
            Ingredient.category_id,
            func.coalesce(func.sum(StockIn.total_price), 0).label("total"),
        )
        .select_from(StockIn)
        .join(Ingredient, Ingredient.id == StockIn.ingredient_id)
        .filter(StockIn.created_at >= month_start)
        .filter(StockIn.created_at < month_end)
    )
    category_stats = _filter_by_org_ids(category_stats, StockIn, accessible)
    category_stats = category_stats.group_by(Ingredient.category_id).all()

    # 学校排行
    school_stats = (
        db.query(
            Organization.name,
            func.coalesce(func.sum(StockIn.total_price), 0).label("total"),
        )
        .select_from(StockIn)
        .join(Ingredient, Ingredient.id == StockIn.ingredient_id)
        .join(Organization, Organization.id == Ingredient.org_id)
        .filter(StockIn.created_at >= month_start)
        .filter(StockIn.created_at < month_end)
    )
    school_stats = _filter_by_org_ids(school_stats, StockIn, accessible)
    school_stats = school_stats.group_by(Organization.id, Organization.name).order_by(
        func.sum(StockIn.total_price).desc()
    ).limit(10).all()

    return {
        "year": year,
        "month": month,
        "total_purchase": float(month_in),
        "total_consumption": float(month_out),
        "category_breakdown": [
            {"category_id": c[0], "amount": float(c[1])} for c in category_stats
        ],
        "school_ranking": [
            {"school_name": s[0], "amount": float(s[1])} for s in school_stats
        ],
    }
