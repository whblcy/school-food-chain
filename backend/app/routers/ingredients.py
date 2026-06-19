"""Ingredients router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import Ingredient, User
from app.schemas import IngredientCreate, Ingredient

router = APIRouter()


@router.get("/", response_model=List[Ingredient])
def list_ingredients(
    skip: int = 0,
    limit: int = 100,
    category_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Ingredient)
    if category_id:
        query = query.filter(Ingredient.category_id == category_id)
    ingredients = query.offset(skip).limit(limit).all()
    return ingredients


@router.post("/", response_model=Ingredient)
def create_ingredient(
    ingredient: IngredientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_ing = Ingredient(**ingredient.dict())
    db.add(db_ing)
    db.commit()
    db.refresh(db_ing)
    return db_ing


@router.get("/{ingredient_id}", response_model=Ingredient)
def get_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ing = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ing:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return ing


@router.put("/{ingredient_id}", response_model=Ingredient)
def update_ingredient(
    ingredient_id: int,
    ingredient: IngredientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_ing = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not db_ing:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    for key, value in ingredient.dict().items():
        setattr(db_ing, key, value)
    
    db.commit()
    db.refresh(db_ing)
    return db_ing


@router.delete("/{ingredient_id}")
def delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_ing = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not db_ing:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    db.delete(db_ing)
    db.commit()
    return {"message": "Ingredient deleted"}
