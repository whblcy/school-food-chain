"""Finance router"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user
from app.models import StockIn, StockOut, User

router = APIRouter()


@router.get("/monthly-summary")
def monthly_summary(
    year: int = datetime.now().year,
    month: int = datetime.now().month,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """月度财务汇总"""
    total_in = db.query(func.coalesce(func.sum(StockIn.total_price), 0)).filter(
        extract('year', StockIn.created_at) == year,
        extract('month', StockIn.created_at) == month
    ).scalar()
    
    total_out = db.query(func.coalesce(func.sum(StockOut.total_price), 0)).filter(
        extract('year', StockOut.created_at) == year,
        extract('month', StockOut.created_at) == month
    ).scalar()
    
    return {
        "year": year,
        "month": month,
        "total_in": float(total_in),
        "total_out": float(total_out),
        "balance": float(total_in - total_out)
    }


@router.get("/yearly-trend")
def yearly_trend(
    year: int = datetime.now().year,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """年度月度趋势"""
    result = []
    for m in range(1, 13):
        total_in = db.query(func.coalesce(func.sum(StockIn.total_price), 0)).filter(
            extract('year', StockIn.created_at) == year,
            extract('month', StockIn.created_at) == m
        ).scalar()
        
        total_out = db.query(func.coalesce(func.sum(StockOut.total_price), 0)).filter(
            extract('year', StockOut.created_at) == year,
            extract('month', StockOut.created_at) == m
        ).scalar()
        
        result.append({
            "month": m,
            "in_amount": float(total_in),
            "out_amount": float(total_out)
        })
    
    return result


@router.get("/category-breakdown")
def category_breakdown(
    year: int = datetime.now().year,
    month: int = datetime.now().month,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """按分类统计采购金额"""
    from app.models import Ingredient, Category
    
    results = db.query(
        Category.name,
        func.coalesce(func.sum(StockIn.total_price), 0).label('amount')
    ).join(Ingredient, StockIn.ingredient_id == Ingredient.id
    ).join(Category, Ingredient.category_id == Category.id
    ).filter(
        extract('year', StockIn.created_at) == year,
        extract('month', StockIn.created_at) == month
    ).group_by(Category.name).all()
    
    return [{"category": r.name, "amount": float(r.amount)} for r in results]
