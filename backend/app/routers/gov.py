"""教育局监管路由 - 提供给教育局的数据看板和上报接口"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.auth import get_current_user
from app.models import (
    User, Organization, OrgType, StockIn, StockOut, Ingredient,
    InventoryCheck, Supplier, SupplierStatus, TraceRecord
)
from app.schemas import UserRole

router = APIRouter()


def check_gov_access(current_user: User = Depends(get_current_user)):
    """检查是否为教育局监管人员"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        # 实际项目中这里会检查是否为教育局账号
        pass
    return current_user


@router.get("/dashboard")
def gov_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_gov_access)
):
    """教育局监管总览看板"""
    # 统计学校数量
    school_count = db.query(Organization).filter(
        Organization.org_type.in_([OrgType.CAMPUS, OrgType.CANTEEN])
    ).count()

    # 今日入库总量
    today = datetime.now().date()
    today_in = db.query(func.sum(StockIn.quantity)).filter(
        func.date(StockIn.created_at) == today
    ).scalar() or 0

    # 今日出库总量
    today_out = db.query(func.sum(StockOut.quantity)).filter(
        func.date(StockOut.created_at) == today
    ).scalar() or 0

    # 低库存预警数量
    low_stock_count = db.query(Ingredient).filter(
        Ingredient.current_stock <= Ingredient.safety_stock
    ).count()

    # 供应商总数
    supplier_count = db.query(Supplier).count()

    # 活跃供应商
    active_supplier_count = db.query(Supplier).filter(
        Supplier.status == SupplierStatus.ACTIVE
    ).count()

    # 最近7天入库趋势
    trend = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        day_in = db.query(func.sum(StockIn.quantity)).filter(
            func.date(StockIn.created_at) == date
        ).scalar() or 0
        day_out = db.query(func.sum(StockOut.quantity)).filter(
            func.date(StockOut.created_at) == date
        ).scalar() or 0
        trend.append({
            "date": date.isoformat(),
            "stock_in": float(day_in),
            "stock_out": float(day_out)
        })

    return {
        "school_count": school_count,
        "today_stock_in": float(today_in),
        "today_stock_out": float(today_out),
        "low_stock_alert": low_stock_count,
        "supplier_count": supplier_count,
        "active_supplier_count": active_supplier_count,
        "weekly_trend": trend
    }


@router.get("/schools")
def list_schools(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_gov_access)
):
    """学校列表及关键指标"""
    schools = db.query(Organization).filter(
        Organization.org_type.in_([OrgType.CAMPUS, OrgType.CANTEEN])
    ).all()

    result = []
    for school in schools:
        ingredient_count = db.query(Ingredient).filter(
            Ingredient.org_id == school.id
        ).count()

        today = datetime.now().date()
        today_in = db.query(func.sum(StockIn.total_price)).filter(
            StockIn.created_at >= today
        ).scalar() or 0

        low_count = db.query(Ingredient).filter(
            Ingredient.org_id == school.id,
            Ingredient.current_stock <= Ingredient.safety_stock
        ).count()

        result.append({
            "id": school.id,
            "name": school.name,
            "code": school.code,
            "org_type": school.org_type.value,
            "ingredient_count": ingredient_count,
            "today_purchase": float(today_in),
            "low_stock_count": low_count,
            "is_active": school.is_active
        })

    return result


@router.get("/schools/{school_id}/detail")
def school_detail(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_gov_access)
):
    """单个学校的详细监管数据"""
    school = db.query(Organization).filter(Organization.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    ingredients = db.query(Ingredient).filter(Ingredient.org_id == school_id).all()
    ingredient_list = []
    for i in ingredients:
        ingredient_list.append({
            "id": i.id,
            "name": i.name,
            "current_stock": i.current_stock,
            "safety_stock": i.safety_stock,
            "unit": i.unit,
            "status": "正常" if i.current_stock > i.safety_stock else "预警"
        })

    recent_in = db.query(StockIn).order_by(StockIn.created_at.desc()).limit(10).all()
    recent_in_list = []
    for r in recent_in:
        ingredient = db.query(Ingredient).filter(Ingredient.id == r.ingredient_id).first()
        recent_in_list.append({
            "batch_no": r.batch_no,
            "ingredient_name": ingredient.name if ingredient else "未知",
            "quantity": r.quantity,
            "unit_price": r.unit_price,
            "total_price": r.total_price,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })

    recent_check = db.query(InventoryCheck).order_by(InventoryCheck.created_at.desc()).limit(5).all()
    check_list = []
    for c in recent_check:
        ingredient = db.query(Ingredient).filter(Ingredient.id == c.ingredient_id).first()
        check_list.append({
            "ingredient_name": ingredient.name if ingredient else "未知",
            "system_stock": c.system_stock,
            "actual_stock": c.actual_stock,
            "difference": c.difference,
            "created_at": c.created_at.isoformat() if c.created_at else None
        })

    return {
        "school": {
            "id": school.id,
            "name": school.name,
            "code": school.code,
            "address": school.address,
            "contact_person": school.contact_person,
            "contact_phone": school.contact_phone
        },
        "ingredients": ingredient_list,
        "recent_stock_in": recent_in_list,
        "recent_inventory_checks": check_list
    }


@router.get("/alerts")
def get_alerts(
    alert_type: Optional[str] = Query(None, description="alert类型: low_stock, expiry, supplier"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_gov_access)
):
    """获取各类预警信息"""
    alerts = []

    if alert_type is None or alert_type == "low_stock":
        low_items = db.query(Ingredient).filter(
            Ingredient.current_stock <= Ingredient.safety_stock
        ).all()
        for item in low_items:
            org = db.query(Organization).filter(Organization.id == item.org_id).first()
            alerts.append({
                "type": "low_stock",
                "level": "warning" if item.current_stock > 0 else "critical",
                "title": f"库存预警: {item.name}",
                "message": f"当前库存 {item.current_stock}{item.unit}，低于安全库存 {item.safety_stock}{item.unit}",
                "school_name": org.name if org else "未知",
                "created_at": datetime.now().isoformat()
            })

    if alert_type is None or alert_type == "expiry":
        expiry_date = datetime.now() + timedelta(days=30)
        expiry_items = db.query(StockIn).filter(
            StockIn.expiry_date <= expiry_date,
            StockIn.expiry_date >= datetime.now()
        ).all()
        for item in expiry_items:
            ingredient = db.query(Ingredient).filter(Ingredient.id == item.ingredient_id).first()
            days_left = (item.expiry_date - datetime.now()).days if item.expiry_date else 0
            alerts.append({
                "type": "expiry",
                "level": "warning" if days_left > 7 else "critical",
                "title": f"临期预警: {ingredient.name if ingredient else '未知食材'}",
                "message": f"批次 {item.batch_no} 将于 {days_left} 天后过期",
                "school_name": "",
                "created_at": datetime.now().isoformat()
            })

    if alert_type is None or alert_type == "supplier":
        blacklisted = db.query(Supplier).filter(Supplier.status == SupplierStatus.BLACKLISTED).all()
        for s in blacklisted:
            alerts.append({
                "type": "supplier",
                "level": "critical",
                "title": f"黑名单供应商: {s.name}",
                "message": f"供应商 {s.name} 已被列入黑名单，原因: {s.blacklist_reason or '未说明'}",
                "school_name": "",
                "created_at": datetime.now().isoformat()
            })

    return {"total": len(alerts), "items": alerts}


@router.get("/reports/monthly")
def monthly_report(
    year: int = Query(default_factory=lambda: datetime.now().year),
    month: int = Query(default_factory=lambda: datetime.now().month),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_gov_access)
):
    """月度监管报告"""
    month_in = db.query(func.sum(StockIn.total_price)).filter(
        extract('year', StockIn.created_at) == year,
        extract('month', StockIn.created_at) == month
    ).scalar() or 0

    month_out = db.query(func.sum(StockOut.total_price)).filter(
        extract('year', StockOut.created_at) == year,
        extract('month', StockOut.created_at) == month
    ).scalar() or 0

    category_stats = db.query(
        Ingredient.category_id,
        func.sum(StockIn.total_price).label("total")
    ).join(StockIn, StockIn.ingredient_id == Ingredient.id).filter(
        extract('year', StockIn.created_at) == year,
        extract('month', StockIn.created_at) == month
    ).group_by(Ingredient.category_id).all()

    school_stats = db.query(
        Organization.name,
        func.sum(StockIn.total_price).label("total")
    ).join(Ingredient, Ingredient.org_id == Organization.id).join(
        StockIn, StockIn.ingredient_id == Ingredient.id
    ).filter(
        extract('year', StockIn.created_at) == year,
        extract('month', StockIn.created_at) == month
    ).group_by(Organization.id).order_by(func.sum(StockIn.total_price).desc()).limit(10).all()

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
        ]
    }
