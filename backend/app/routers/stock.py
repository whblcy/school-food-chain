"""Stock management router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import (
    StockIn as StockInModel, StockOut as StockOutModel,
    InventoryCheck as InventoryCheckModel, Ingredient, User
)
from app.schemas import (
    StockInCreate, StockOutCreate, InventoryCheckCreate,
    StockIn, StockOut, InventoryCheck
)

router = APIRouter()


@router.post("/in", response_model=StockIn)
def stock_in(
    data: StockInCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """入库操作 - 自动更新库存"""
    # 检查食材
    ingredient = db.query(Ingredient).filter(Ingredient.id == data.ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    # 生成批次号
    import uuid
    batch_no = f"IN{uuid.uuid4().hex[:12].upper()}"

    # 创建入库记录
    total_price = data.quantity * data.unit_price
    record = StockInModel(
        batch_no=batch_no,
        ingredient_id=data.ingredient_id,
        quantity=data.quantity,
        unit_price=data.unit_price,
        total_price=total_price,
        supplier_id=data.supplier_id,
        production_date=data.production_date,
        expiry_date=data.expiry_date,
        batch_number=data.batch_number,
        inspector1_id=data.inspector1_id,
        inspector2_id=data.inspector2_id,
        operator_id=current_user.id,
        remark=data.remark
    )
    db.add(record)

    # 更新库存
    ingredient.current_stock += data.quantity

    db.commit()
    db.refresh(record)
    return record


@router.post("/out", response_model=StockOut)
def stock_out(
    data: StockOutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """出库操作 - 检查库存"""
    ingredient = db.query(Ingredient).filter(Ingredient.id == data.ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    if ingredient.current_stock < data.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Current: {ingredient.current_stock}, Requested: {data.quantity}"
        )

    total_price = data.quantity * (data.unit_price or 0)
    record = StockOutModel(
        ingredient_id=data.ingredient_id,
        quantity=data.quantity,
        unit_price=data.unit_price,
        total_price=total_price,
        purpose=data.purpose,
        department=data.department,
        operator_id=current_user.id,
        remark=data.remark
    )
    db.add(record)

    # 扣减库存
    ingredient.current_stock -= data.quantity

    db.commit()
    db.refresh(record)
    return record


@router.post("/check", response_model=InventoryCheck)
def inventory_check(
    data: InventoryCheckCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """库存盘点"""
    ingredient = db.query(Ingredient).filter(Ingredient.id == data.ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    difference = data.actual_stock - data.system_stock

    record = InventoryCheckModel(
        ingredient_id=data.ingredient_id,
        system_stock=data.system_stock,
        actual_stock=data.actual_stock,
        difference=difference,
        operator_id=current_user.id,
        remark=data.remark
    )
    db.add(record)

    # 校正库存
    ingredient.current_stock = data.actual_stock

    db.commit()
    db.refresh(record)
    return record


@router.get("/in", response_model=List[StockIn])
def list_stock_in(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    records = db.query(StockInModel).order_by(StockInModel.created_at.desc()).offset(skip).limit(limit).all()
    return records


@router.get("/out", response_model=List[StockOut])
def list_stock_out(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    records = db.query(StockOutModel).order_by(StockOutModel.created_at.desc()).offset(skip).limit(limit).all()
    return records
