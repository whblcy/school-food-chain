"""Pydantic schemas

设计要点：
- 金额字段使用 Decimal，与数据库 Numeric 对齐
- 响应模型补充关联名称字段（ingredient_name / supplier_name），避免前端 N+1
- 输入验证：非负、日期顺序、范围校验
- Supplier 黑名单操作独立 schema，强制 reason
"""
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator
from typing import Optional, List, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.models import UserRole, OrgType, SupplierStatus, OrderStatus


# ---------------------------------------------------------------------------
# 通用分页
# ---------------------------------------------------------------------------
class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @field_validator("page", "page_size")
    @classmethod
    def positive(cls, v):
        if v < 1:
            raise ValueError("分页参数必须为正数")
        return v


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: List[Any]


# ---------------------------------------------------------------------------
# 用户
# ---------------------------------------------------------------------------
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    real_name: Optional[str] = None
    role: UserRole = UserRole.OPERATOR
    is_active: bool = True
    org_id: Optional[int] = None


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("密码长度至少 6 位")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    real_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    org_id: Optional[int] = None


class User(UserBase):
    id: int
    org_id: Optional[int] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------------------------------------------------------------------------
# 组织
# ---------------------------------------------------------------------------
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


class OrgUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    license_no: Optional[str] = None
    is_active: Optional[bool] = None
    parent_id: Optional[int] = None


class Org(OrgBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 供应商
# ---------------------------------------------------------------------------
class SupplierBase(BaseModel):
    name: str
    code: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None


class SupplierCreate(SupplierBase):
    business_license: Optional[str] = None
    food_license: Optional[str] = None
    haccp_cert: Optional[str] = None
    iso22000_cert: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    business_license: Optional[str] = None
    food_license: Optional[str] = None
    haccp_cert: Optional[str] = None
    iso22000_cert: Optional[str] = None
    rating: Optional[Decimal] = None

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError("评分必须在 0-5 之间")
        return v


class SupplierBlacklist(BaseModel):
    """黑名单操作专用 schema — 强制要求 reason。"""
    reason: str

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v):
        if not v.strip():
            raise ValueError("黑名单原因不能为空")
        return v.strip()


class Supplier(SupplierBase):
    id: int
    business_license: Optional[str] = None
    food_license: Optional[str] = None
    haccp_cert: Optional[str] = None
    iso22000_cert: Optional[str] = None
    status: SupplierStatus = SupplierStatus.ACTIVE
    rating: Decimal
    blacklist_reason: Optional[str] = None
    org_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 分类
# ---------------------------------------------------------------------------
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
    org_id: int

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 食材
# ---------------------------------------------------------------------------
class IngredientBase(BaseModel):
    name: str
    code: str
    category_id: int
    unit: str
    specification: Optional[str] = None
    safety_stock: Decimal = Decimal("0")
    supplier_id: Optional[int] = None

    @field_validator("safety_stock")
    @classmethod
    def safety_stock_nonneg(cls, v):
        if v < 0:
            raise ValueError("安全库存不能为负数")
        return v


class IngredientCreate(IngredientBase):
    pass


class Ingredient(IngredientBase):
    id: int
    org_id: Optional[int] = None
    current_stock: Decimal
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    # 关联名称（路由层 JOIN 填充）
    category_name: Optional[str] = None
    supplier_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 库存：入库
# ---------------------------------------------------------------------------
class StockInBase(BaseModel):
    ingredient_id: int
    quantity: Decimal
    unit_price: Decimal
    supplier_id: Optional[int] = None
    production_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    batch_number: Optional[str] = None
    remark: Optional[str] = None

    @field_validator("quantity", "unit_price")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("数量和单价必须为正数")
        return v

    @field_validator("expiry_date")
    @classmethod
    def expiry_after_production(cls, v, info):
        prod = info.data.get("production_date")
        if v is not None and prod is not None and v <= prod:
            raise ValueError("过期日期必须晚于生产日期")
        return v


class StockInCreate(StockInBase):
    inspector1_id: int
    inspector2_id: int


class StockIn(StockInBase):
    id: int
    batch_no: str
    total_price: Decimal
    operator_id: int
    inspector1_id: Optional[int] = None
    inspector2_id: Optional[int] = None
    created_at: datetime
    # 关联名称（路由层 JOIN 填充）
    ingredient_name: Optional[str] = None
    supplier_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 库存：出库
# ---------------------------------------------------------------------------
class StockOutBase(BaseModel):
    ingredient_id: int
    quantity: Decimal
    unit_price: Optional[Decimal] = None
    purpose: Optional[str] = None
    department: Optional[str] = None
    remark: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("出库数量必须为正数")
        return v

    @field_validator("unit_price")
    @classmethod
    def unit_price_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("单价不能为负数")
        return v


class StockOutCreate(StockOutBase):
    pass


class StockOut(StockOutBase):
    id: int
    total_price: Optional[Decimal] = None
    operator_id: int
    created_at: datetime
    ingredient_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 库存：盘点
# ---------------------------------------------------------------------------
class InventoryCheckBase(BaseModel):
    ingredient_id: int
    actual_stock: Decimal
    remark: Optional[str] = None

    @field_validator("actual_stock")
    @classmethod
    def actual_stock_nonneg(cls, v):
        if v < 0:
            raise ValueError("实际库存不能为负数")
        return v


class InventoryCheckCreate(InventoryCheckBase):
    pass


class InventoryCheck(InventoryCheckBase):
    id: int
    system_stock: Decimal
    difference: Decimal
    operator_id: int
    created_at: datetime
    ingredient_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 追溯
# ---------------------------------------------------------------------------
class TraceRecordBase(BaseModel):
    ingredient_id: int
    batch_no: Optional[str] = None
    supplier_id: Optional[int] = None
    stock_in_id: Optional[int] = None
    production_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    test_report: Optional[str] = None
    quarantine_cert: Optional[str] = None


class TraceRecordCreate(TraceRecordBase):
    pass


class TraceRecord(TraceRecordBase):
    id: int
    trace_code: str
    org_id: int
    created_at: datetime
    ingredient_name: Optional[str] = None
    supplier_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 审计日志
# ---------------------------------------------------------------------------
class AuditLog(BaseModel):
    id: int
    org_id: Optional[int] = None
    user_id: Optional[int] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    # 关联名称
    username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
