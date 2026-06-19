"""SQLAlchemy models"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


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


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20))
    hashed_password = Column(String(255), nullable=False)
    real_name = Column(String(50))
    role = Column(Enum(UserRole), default=UserRole.OPERATOR)
    org_id = Column(Integer, ForeignKey("organizations.id"))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    org = relationship("Organization", back_populates="users")


class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, index=True)
    org_type = Column(Enum(OrgType), nullable=False)
    parent_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    address = Column(String(255))
    contact_person = Column(String(50))
    contact_phone = Column(String(20))
    license_no = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    users = relationship("User", back_populates="org")
    parent = relationship("Organization", remote_side=[id], backref="children")


class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, index=True)
    contact_person = Column(String(50))
    phone = Column(String(20))
    email = Column(String(100))
    address = Column(String(255))
    business_license = Column(String(255))  # 营业执照文件路径
    food_license = Column(String(255))  # 食品经营许可证
    haccp_cert = Column(String(255))  # HACCP认证
    iso22000_cert = Column(String(255))  # ISO22000认证
    status = Column(Enum(SupplierStatus), default=SupplierStatus.ACTIVE)
    rating = Column(Float, default=5.0)  # 评分 1-5
    blacklist_reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    code = Column(String(30), unique=True)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class Ingredient(Base):
    __tablename__ = "ingredients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    unit = Column(String(20), nullable=False)
    specification = Column(String(255))
    safety_stock = Column(Float, default=0)
    current_stock = Column(Float, default=0)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    org_id = Column(Integer, ForeignKey("organizations.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    category = relationship("Category")
    supplier = relationship("Supplier")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), unique=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    org_id = Column(Integer, ForeignKey("organizations.id"))
    status = Column(Enum(OrderStatus), default=OrderStatus.DRAFT)
    total_amount = Column(Float, default=0)
    delivery_date = Column(DateTime)
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    remark = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)


class StockIn(Base):
    __tablename__ = "stock_in"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_no = Column(String(50), unique=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    order_id = Column(Integer, ForeignKey("purchase_orders.id"))
    production_date = Column(DateTime)
    expiry_date = Column(DateTime)
    batch_number = Column(String(100))
    inspector1_id = Column(Integer, ForeignKey("users.id"))  # 验收人1
    inspector2_id = Column(Integer, ForeignKey("users.id"))  # 验收人2
    inspection_images = Column(JSON)  # 验收照片
    operator_id = Column(Integer, ForeignKey("users.id"))
    remark = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class StockOut(Base):
    __tablename__ = "stock_out"
    
    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float)
    total_price = Column(Float)
    purpose = Column(String(100))  # 用途
    department = Column(String(100))  # 部门
    operator_id = Column(Integer, ForeignKey("users.id"))
    remark = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class InventoryCheck(Base):
    __tablename__ = "inventory_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    system_stock = Column(Float, nullable=False)
    actual_stock = Column(Float, nullable=False)
    difference = Column(Float, nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"))
    remark = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class TraceRecord(Base):
    __tablename__ = "trace_records"
    
    id = Column(Integer, primary_key=True, index=True)
    trace_code = Column(String(100), unique=True, index=True)  # 追溯码
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    batch_no = Column(String(50))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    stock_in_id = Column(Integer, ForeignKey("stock_in.id"))
    production_date = Column(DateTime)
    expiry_date = Column(DateTime)
    test_report = Column(String(255))  # 检测报告
    quarantine_cert = Column(String(255))  # 检疫证明
    trace_data = Column(JSON)  # 完整追溯数据
    created_at = Column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(50), nullable=False)
    target_type = Column(String(50))
    target_id = Column(Integer)
    old_value = Column(JSON)
    new_value = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
