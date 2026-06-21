"""SQLAlchemy models

设计要点：
- 金额字段使用 Numeric(12,2)，避免 Float 精度丢失
- DateTime 统一带时区（timezone=True）
- 外键显式声明 ondelete 策略（CASCADE / SET NULL / RESTRICT）
- 多租户 code 字段使用 (org_id, code) 复合唯一约束，而非全局唯一
- 关键数值字段附加 CHECK 约束（非负、范围）
- relationship 配对 back_populates，避免 N+1 时可显式 joinedload
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey,
    Text, Enum, JSON, Numeric, CheckConstraint, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------
class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


class OrgType(str, enum.Enum):
    GROUP = "group"
    CAMPUS = "campus"
    CANTEEN = "canteen"
    STALL = "stall"


class SupplierStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BLACKLISTED = "blacklisted"


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    DELIVERING = "delivering"
    RECEIVED = "received"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# 用户与组织
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20))
    hashed_password = Column(String(255), nullable=False)
    real_name = Column(String(50))
    role = Column(Enum(UserRole), default=UserRole.OPERATOR, nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    org = relationship("Organization", back_populates="users")


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_org_no_self_ref"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, index=True)
    org_type = Column(Enum(OrgType), nullable=False)
    parent_id = Column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True)
    address = Column(String(255))
    contact_person = Column(String(50))
    contact_phone = Column(String(20))
    license_no = Column(String(100))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="org")
    parent = relationship("Organization", remote_side=[id], back_populates="children")
    children = relationship("Organization", back_populates="parent")


# ---------------------------------------------------------------------------
# 供应商
# ---------------------------------------------------------------------------
class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_supplier_org_code"),
        CheckConstraint("rating >= 0 AND rating <= 5", name="ck_supplier_rating_range"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), index=True)
    contact_person = Column(String(50))
    phone = Column(String(20))
    email = Column(String(100))
    address = Column(String(255))
    business_license = Column(String(255))
    food_license = Column(String(255))
    haccp_cert = Column(String(255))
    iso22000_cert = Column(String(255))
    status = Column(Enum(SupplierStatus), default=SupplierStatus.ACTIVE, nullable=False)
    rating = Column(Numeric(2, 1), default=5.0)
    blacklist_reason = Column(Text)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    org = relationship("Organization")
    ingredients = relationship("Ingredient", back_populates="supplier")


# ---------------------------------------------------------------------------
# 食材分类与食材
# ---------------------------------------------------------------------------
class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_category_org_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    code = Column(String(30), index=True)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)

    ingredients = relationship("Ingredient", back_populates="category")


class Ingredient(Base):
    __tablename__ = "ingredients"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_ingredient_org_code"),
        CheckConstraint("safety_stock >= 0", name="ck_ingredient_safety_stock_nonneg"),
        CheckConstraint("current_stock >= 0", name="ck_ingredient_current_stock_nonneg"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    unit = Column(String(20), nullable=False)
    specification = Column(String(255))
    safety_stock = Column(Numeric(12, 2), default=0)
    current_stock = Column(Numeric(12, 2), default=0)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="ingredients")
    supplier = relationship("Supplier", back_populates="ingredients")


# ---------------------------------------------------------------------------
# 采购订单
# ---------------------------------------------------------------------------
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        UniqueConstraint("org_id", "order_no", name="uq_purchase_order_org_no"),
    )

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"))
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"))
    status = Column(Enum(OrderStatus), default=OrderStatus.DRAFT)
    total_amount = Column(Numeric(14, 2), default=0)
    delivery_date = Column(DateTime(timezone=True))
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    approved_at = Column(DateTime(timezone=True))
    remark = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("PurchaseOrderItem", back_populates="order", cascade="all, delete-orphan")
    supplier = relationship("Supplier")
    approver = relationship("User", foreign_keys=[approved_by])
    creator = relationship("User", foreign_keys=[created_by])


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_poi_quantity_nonneg"),
        CheckConstraint("unit_price >= 0", name="ck_poi_unit_price_nonneg"),
        CheckConstraint("total_price >= 0", name="ck_poi_total_price_nonneg"),
    )

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="SET NULL"))
    quantity = Column(Numeric(12, 2), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_price = Column(Numeric(14, 2), nullable=False)

    order = relationship("PurchaseOrder", back_populates="items")
    ingredient = relationship("Ingredient")


# ---------------------------------------------------------------------------
# 库存：入库 / 出库 / 盘点
# ---------------------------------------------------------------------------
class StockIn(Base):
    __tablename__ = "stock_in"
    __table_args__ = (
        UniqueConstraint("org_id", "batch_no", name="uq_stock_in_org_batch"),
        CheckConstraint("quantity >= 0", name="ck_stock_in_quantity_nonneg"),
        CheckConstraint("unit_price >= 0", name="ck_stock_in_unit_price_nonneg"),
        CheckConstraint("total_price >= 0", name="ck_stock_in_total_price_nonneg"),
        CheckConstraint(
            "expiry_date IS NULL OR production_date IS NULL OR expiry_date > production_date",
            name="ck_stock_in_expiry_after_production",
        ),
        Index("ix_stock_in_org_created", "org_id", "created_at"),
        Index("ix_stock_in_org_ingredient", "org_id", "ingredient_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    batch_no = Column(String(50), index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), index=True)
    quantity = Column(Numeric(12, 2), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_price = Column(Numeric(14, 2), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="SET NULL"))
    production_date = Column(DateTime(timezone=True))
    expiry_date = Column(DateTime(timezone=True))
    batch_number = Column(String(100))
    inspector1_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    inspector2_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    inspection_images = Column(JSON)
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    remark = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    ingredient = relationship("Ingredient")
    supplier = relationship("Supplier")
    operator = relationship("User", foreign_keys=[operator_id])
    inspector1 = relationship("User", foreign_keys=[inspector1_id])
    inspector2 = relationship("User", foreign_keys=[inspector2_id])


class StockOut(Base):
    __tablename__ = "stock_out"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_stock_out_quantity_nonneg"),
        Index("ix_stock_out_org_created", "org_id", "created_at"),
        Index("ix_stock_out_org_ingredient", "org_id", "ingredient_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), index=True)
    quantity = Column(Numeric(12, 2), nullable=False)
    unit_price = Column(Numeric(12, 2))
    total_price = Column(Numeric(14, 2))
    purpose = Column(String(100))
    department = Column(String(100))
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    remark = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    ingredient = relationship("Ingredient")
    operator = relationship("User", foreign_keys=[operator_id])


class InventoryCheck(Base):
    __tablename__ = "inventory_checks"
    __table_args__ = (
        CheckConstraint("system_stock >= 0", name="ck_invchk_system_nonneg"),
        CheckConstraint("actual_stock >= 0", name="ck_invchk_actual_nonneg"),
        Index("ix_invchk_org_created", "org_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), index=True)
    system_stock = Column(Numeric(12, 2), nullable=False)
    actual_stock = Column(Numeric(12, 2), nullable=False)
    difference = Column(Numeric(12, 2), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    remark = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    ingredient = relationship("Ingredient")
    operator = relationship("User", foreign_keys=[operator_id])


# ---------------------------------------------------------------------------
# 追溯
# ---------------------------------------------------------------------------
class TraceRecord(Base):
    __tablename__ = "trace_records"
    __table_args__ = (
        Index("ix_trace_org_ingredient", "org_id", "ingredient_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    trace_code = Column(String(100), unique=True, index=True)  # 公开追溯码，全局唯一
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), index=True)
    batch_no = Column(String(50))
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"))
    stock_in_id = Column(Integer, ForeignKey("stock_in.id", ondelete="SET NULL"))
    production_date = Column(DateTime(timezone=True))
    expiry_date = Column(DateTime(timezone=True))
    test_report = Column(String(255))
    quarantine_cert = Column(String(255))
    trace_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ingredient = relationship("Ingredient")
    supplier = relationship("Supplier")
    stock_in = relationship("StockIn")


# ---------------------------------------------------------------------------
# 审计日志
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_org_created", "org_id", "created_at"),
        Index("ix_audit_target", "target_type", "target_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action = Column(String(50), nullable=False)
    target_type = Column(String(50), index=True)
    target_id = Column(Integer, index=True)
    old_value = Column(JSON)
    new_value = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", foreign_keys=[user_id])
    org = relationship("Organization", foreign_keys=[org_id])
