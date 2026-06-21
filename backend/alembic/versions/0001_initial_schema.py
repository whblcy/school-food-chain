"""
0001 — 初始数据库 schema（所有核心表）。
- users（用户）
- organizations（组织/学校/教育局）
- suppliers（供应商）
- categories（食材分类）
- ingredients（食材）
- purchase_orders + purchase_order_items（采购订单）
- stock_in, stock_out（出入库）
- inventory_checks（盘点）
- trace_records（溯源码）
- audit_logs（审计日志）

生成日期：2025-01-01（首次部署）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import func

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


UserRole = sa.Enum("SUPER_ADMIN", "ADMIN", "MANAGER", "OPERATOR", "VIEWER", name="user_role")
OrgType = sa.Enum("GROUP", "CAMPUS", "CANTEEN", "STALL", name="org_type")
SupplierStatus = sa.Enum("ACTIVE", "SUSPENDED", "BLACKLISTED", name="supplier_status")
OrderStatus = sa.Enum(
    "DRAFT", "PENDING", "APPROVED", "DELIVERING", "RECEIVED", "REJECTED",
    name="order_status"
)


def upgrade() -> None:
    # --- organizations ---
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("org_type", OrgType, nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("contact_person", sa.String(length=50), nullable=True),
        sa.Column("contact_phone", sa.String(length=20), nullable=True),
        sa.Column("license_no", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
    )
    op.create_index(op.f("ix_organizations_code"), "organizations", ["code"], unique=True)

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("real_name", sa.String(length=50), nullable=True),
        sa.Column("role", UserRole, server_default="OPERATOR"),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_login", sa.DateTime(timezone=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=func.now(),
                  onupdate=func.now()),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_org_id"), "users", ["org_id"], unique=False)

    # --- suppliers ---
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("contact_person", sa.String(length=50), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("business_license", sa.String(length=255), nullable=True),
        sa.Column("food_license", sa.String(length=255), nullable=True),
        sa.Column("haccp_cert", sa.String(length=255), nullable=True),
        sa.Column("iso22000_cert", sa.String(length=255), nullable=True),
        sa.Column("status", SupplierStatus, server_default="ACTIVE"),
        sa.Column("rating", sa.Float(), server_default="5.0"),
        sa.Column("blacklist_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=func.now(),
                  onupdate=func.now()),
    )
    op.create_index(op.f("ix_suppliers_code"), "suppliers", ["code"], unique=True)

    # --- categories ---
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
    )
    op.create_index(op.f("ix_categories_code"), "categories", ["code"], unique=True)

    # --- ingredients ---
    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("specification", sa.String(length=255), nullable=True),
        sa.Column("safety_stock", sa.Float(), server_default="0"),
        sa.Column("current_stock", sa.Float(), server_default="0"),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
    )
    op.create_index(op.f("ix_ingredients_code"), "ingredients", ["code"], unique=True)
    op.create_index(op.f("ix_ingredients_org_id"), "ingredients", ["org_id"], unique=False)
    op.create_index(op.f("ix_ingredients_category_id"), "ingredients", ["category_id"], unique=False)

    # --- purchase_orders ---
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_no", sa.String(length=50), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("status", OrderStatus, server_default="DRAFT"),
        sa.Column("total_amount", sa.Float(), server_default="0"),
        sa.Column("delivery_date", sa.DateTime(timezone=False), nullable=True),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
    )
    op.create_index(op.f("ix_purchase_orders_order_no"), "purchase_orders", ["order_no"], unique=True)

    # --- purchase_order_items ---
    op.create_table(
        "purchase_order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("purchase_orders.id"), nullable=True),
        sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("ingredients.id"), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("total_price", sa.Float(), nullable=False),
    )
    op.create_index(op.f("ix_purchase_order_items_order_id"), "purchase_order_items", ["order_id"])

    # --- stock_in ---
    op.create_table(
        "stock_in",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_no", sa.String(length=50), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("ingredients.id"), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("total_price", sa.Float(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("purchase_orders.id"), nullable=True),
        sa.Column("production_date", sa.DateTime(timezone=False), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=False), nullable=True),
        sa.Column("batch_number", sa.String(length=100), nullable=True),
        sa.Column("inspector1_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("inspector2_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("inspection_images", sa.JSON(), nullable=True),
        sa.Column("operator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
    )
    op.create_index(op.f("ix_stock_in_batch_no"), "stock_in", ["batch_no"], unique=True)
    op.create_index(op.f("ix_stock_in_ingredient_id"), "stock_in", ["ingredient_id"])
    op.create_index(op.f("ix_stock_in_created_at"), "stock_in", ["created_at"])

    # --- stock_out ---
    op.create_table(
        "stock_out",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("ingredients.id"), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=True),
        sa.Column("total_price", sa.Float(), nullable=True),
        sa.Column("purpose", sa.String(length=100), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("operator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
    )
    op.create_index(op.f("ix_stock_out_ingredient_id"), "stock_out", ["ingredient_id"])
    op.create_index(op.f("ix_stock_out_created_at"), "stock_out", ["created_at"])

    # --- inventory_checks ---
    op.create_table(
        "inventory_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("ingredients.id"), nullable=True),
        sa.Column("system_stock", sa.Float(), nullable=False),
        sa.Column("actual_stock", sa.Float(), nullable=False),
        sa.Column("difference", sa.Float(), nullable=False),
        sa.Column("operator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
    )

    # --- trace_records ---
    op.create_table(
        "trace_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trace_code", sa.String(length=100), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("ingredients.id"), nullable=True),
        sa.Column("batch_no", sa.String(length=50), nullable=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=True),
        sa.Column("stock_in_id", sa.Integer(), sa.ForeignKey("stock_in.id"), nullable=True),
        sa.Column("production_date", sa.DateTime(timezone=False), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=False), nullable=True),
        sa.Column("test_report", sa.String(length=255), nullable=True),
        sa.Column("quarantine_cert", sa.String(length=255), nullable=True),
        sa.Column("trace_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
    )
    op.create_index(op.f("ix_trace_records_trace_code"), "trace_records", ["trace_code"], unique=True)

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=func.now()),
    )
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"])
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"])
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_trace_records_trace_code"), table_name="trace_records")
    op.drop_table("trace_records")

    op.drop_table("inventory_checks")

    op.drop_index(op.f("ix_stock_out_created_at"), table_name="stock_out")
    op.drop_index(op.f("ix_stock_out_ingredient_id"), table_name="stock_out")
    op.drop_table("stock_out")

    op.drop_index(op.f("ix_stock_in_created_at"), table_name="stock_in")
    op.drop_index(op.f("ix_stock_in_ingredient_id"), table_name="stock_in")
    op.drop_index(op.f("ix_stock_in_batch_no"), table_name="stock_in")
    op.drop_table("stock_in")

    op.drop_index(op.f("ix_purchase_order_items_order_id"), table_name="purchase_order_items")
    op.drop_table("purchase_order_items")
    op.drop_index(op.f("ix_purchase_orders_order_no"), table_name="purchase_orders")
    op.drop_table("purchase_orders")

    op.drop_index(op.f("ix_ingredients_category_id"), table_name="ingredients")
    op.drop_index(op.f("ix_ingredients_org_id"), table_name="ingredients")
    op.drop_index(op.f("ix_ingredients_code"), table_name="ingredients")
    op.drop_table("ingredients")

    op.drop_index(op.f("ix_categories_code"), table_name="categories")
    op.drop_table("categories")

    op.drop_index(op.f("ix_suppliers_code"), table_name="suppliers")
    op.drop_table("suppliers")

    op.drop_index(op.f("ix_users_org_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_organizations_code"), table_name="organizations")
    op.drop_table("organizations")

    # 枚举类型
    for enum_type in [UserRole, OrgType, SupplierStatus, OrderStatus]:
        try:
            op.execute(f"DROP TYPE IF EXISTS {enum_type.name}")
        except Exception:
            pass
