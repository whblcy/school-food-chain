"""Reports router"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.auth import get_current_user
from app.models import Ingredient, StockIn, User

router = APIRouter()


@router.get("/stock-summary")
def stock_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """库存汇总"""
    from app.models import Category
    
    results = db.query(
        Category.name,
        func.count(Ingredient.id).label('count'),
        func.coalesce(func.sum(Ingredient.current_stock), 0).label('total_stock')
    ).join(Category, Ingredient.category_id == Category.id
    ).filter(Ingredient.is_active == True
    ).group_by(Category.name).all()
    
    return [{"category": r.name, "count": r.count, "total_stock": float(r.total_stock)} for r in results]


@router.get("/low-stock")
def low_stock(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """低库存预警"""
    items = db.query(Ingredient).filter(
        Ingredient.current_stock <= Ingredient.safety_stock,
        Ingredient.is_active == True
    ).all()
    
    return [{"id": i.id, "name": i.name, "current": i.current_stock, "safety": i.safety_stock} for i in items]


@router.get("/inventory-value")
def inventory_value(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """库存总值"""
    total = db.query(func.coalesce(func.sum(Ingredient.current_stock * StockIn.unit_price), 0)).join(
        StockIn, Ingredient.id == StockIn.ingredient_id
    ).filter(Ingredient.is_active == True).scalar()
    
    return {"total_value": float(total)}
