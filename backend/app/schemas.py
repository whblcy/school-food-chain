"""Pydantic schemas"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

from app.models import UserRole, OrgType, SupplierStatus, OrderStatus


# Base schemas
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    real_name: Optional[str] = None
    role: UserRole = UserRole.OPERATOR
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    real_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: int
    org_id: Optional[int] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class OrgBase(BaseModel):
    name: str
    code: str
    org_type: OrgType
    parent_id: Optional[int] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    license_no: Optional[str] = None


class OrgCreate(OrgBase):
    pass


class Org(OrgBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class SupplierBase(BaseModel):
    name: str
    code: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    status: SupplierStatus = SupplierStatus.ACTIVE


class SupplierCreate(SupplierBase):
    pass


class Supplier(SupplierBase):
    id: int
    rating: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int
    is_active: bool
    
    class Config:
        from_attributes = True


class IngredientBase(BaseModel):
    name: str
    code: str
    category_id: int
    unit: str
    specification: Optional[str] = None
    safety_stock: float = 0
    supplier_id: Optional[int] = None
    org_id: int


class IngredientCreate(IngredientBase):
    pass


class Ingredient(IngredientBase):
    id: int
    current_stock: float
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class StockInBase(BaseModel):
    ingredient_id: int
    quantity: float
    unit_price: float
    supplier_id: Optional[int] = None
    production_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    batch_number: Optional[str] = None
    remark: Optional[str] = None


class StockInCreate(StockInBase):
    inspector1_id: int
    inspector2_id: int


class StockIn(StockInBase):
    id: int
    batch_no: str
    total_price: float
    operator_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class StockOutBase(BaseModel):
    ingredient_id: int
    quantity: float
    unit_price: Optional[float] = None
    purpose: Optional[str] = None
    department: Optional[str] = None
    remark: Optional[str] = None


class StockOutCreate(StockOutBase):
    pass


class StockOut(StockOutBase):
    id: int
    total_price: Optional[float] = None
    operator_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class InventoryCheckBase(BaseModel):
    ingredient_id: int
    system_stock: float
    actual_stock: float
    remark: Optional[str] = None


class InventoryCheckCreate(InventoryCheckBase):
    pass


class InventoryCheck(InventoryCheckBase):
    id: int
    difference: float
    operator_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: List
