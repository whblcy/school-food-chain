"""0003_fix_schema_drift_and_constraints

修复 0001/0002 遗留的 schema 漂移与约束缺失：
1. 给 suppliers / categories / audit_logs 补 org_id 列（致命漂移）
2. 补齐模型声明但迁移未建的索引
3. 金额字段 Float → Numeric(12,2) / Numeric(14,2)
4. DateTime → DateTime(timezone=True)
5. 多租户 code 字段：单列 unique → (org_id, code) 复合唯一
6. 外键补 ondelete 策略（PostgreSQL）
7. CHECK 约束（非负、范围、日期顺序）

Revision ID: 0003
Revises: 0002
Created Date: 2025-06-21
"""
from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger("alembic.0003")

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# 辅助：SQLite 不支持的部分操作静默跳过
# ---------------------------------------------------------------------------
def _is_sqlite():
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def _safe_drop_constraint(constraint_name, table_name):
    try:
        op.drop_constraint(constraint_name, table_name, type_="unique")
    except Exception:
        try:
            op.drop_constraint(constraint_name, table_name, type_="foreignkey")
        except Exception:
            pass


def _safe_drop_index(index_name, table_name=None):
    try:
        op.drop_index(index_name, table_name=table_name)
    except Exception:
        pass


def upgrade():
    # ===================================================================
    # 1. 补 org_id 列（致命漂移修复）
    # ===================================================================
    # suppliers.org_id
    op.add_column(
        "suppliers",
        sa.Column("org_id", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_suppliers_org_id", "suppliers", ["org_id"], unique=False)
    op.create_foreign_key(
        "fk_suppliers_org_id", "suppliers", "organizations", ["org_id"], ["id"],
        ondelete="RESTRICT",
    )

    # categories.org_id
    op.add_column(
        "categories",
        sa.Column("org_id", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_categories_org_id", "categories", ["org_id"], unique=False)
    op.create_foreign_key(
        "fk_categories_org_id", "categories", "organizations", ["org_id"], ["id"],
        ondelete="RESTRICT",
    )

    # audit_logs.org_id（可空）
    op.add_column(
        "audit_logs",
        sa.Column("org_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_audit_logs_org_id", "audit_logs", ["org_id"], unique=False)
    op.create_foreign_key(
        "fk_audit_logs_org_id", "audit_logs", "organizations", ["org_id"], ["id"],
        ondelete="SET NULL",
    )

    # 去掉 server_default
    op.alter_column("suppliers", "org_id", existing_type=sa.Integer(), server_default=None)
    op.alter_column("categories", "org_id", existing_type=sa.Integer(), server_default=None)

    # ===================================================================
    # 2. 补缺失索引
    # ===================================================================
    op.create_index("ix_organizations_parent_id", "organizations", ["parent_id"], unique=False)
    op.create_index("ix_ingredients_supplier_id", "ingredients", ["supplier_id"], unique=False)
    op.create_index("ix_stock_in_supplier_id", "stock_in", ["supplier_id"], unique=False)
    op.create_index("ix_stock_in_operator_id", "stock_in", ["operator_id"], unique=False)
    op.create_index("ix_stock_out_operator_id", "stock_out", ["operator_id"], unique=False)
    op.create_index("ix_inventory_checks_ingredient_id", "inventory_checks", ["ingredient_id"], unique=False)
    op.create_index("ix_inventory_checks_operator_id", "inventory_checks", ["operator_id"], unique=False)
    op.create_index("ix_trace_records_ingredient_id", "trace_records", ["ingredient_id"], unique=False)
    op.create_index("ix_audit_logs_target_type", "audit_logs", ["target_type"], unique=False)
    op.create_index("ix_audit_logs_target_id", "audit_logs", ["target_id"], unique=False)

    # 复合索引（高频查询）
    op.create_index("ix_stock_in_org_created", "stock_in", ["org_id", "created_at"], unique=False)
    op.create_index("ix_stock_in_org_ingredient", "stock_in", ["org_id", "ingredient_id"], unique=False)
    op.create_index("ix_stock_out_org_created", "stock_out", ["org_id", "created_at"], unique=False)
    op.create_index("ix_stock_out_org_ingredient", "stock_out", ["org_id", "ingredient_id"], unique=False)
    op.create_index("ix_invchk_org_created", "inventory_checks", ["org_id", "created_at"], unique=False)
    op.create_index("ix_trace_org_ingredient", "trace_records", ["org_id", "ingredient_id"], unique=False)
    op.create_index("ix_audit_org_created", "audit_logs", ["org_id", "created_at"], unique=False)
    op.create_index("ix_audit_target", "audit_logs", ["target_type", "target_id"], unique=False)

    # ===================================================================
    # 3. 多租户 code：单列 unique → (org_id, code) 复合唯一
    # ===================================================================
    # suppliers
    _safe_drop_index("ix_suppliers_code", "suppliers")
    op.create_unique_constraint("uq_supplier_org_code", "suppliers", ["org_id", "code"])
    op.create_index("ix_suppliers_code", "suppliers", ["code"], unique=False)

    # categories
    _safe_drop_index("ix_categories_code", "categories")
    op.create_unique_constraint("uq_category_org_code", "categories", ["org_id", "code"])
    op.create_index("ix_categories_code", "categories", ["code"], unique=False)

    # ingredients
    _safe_drop_index("ix_ingredients_code", "ingredients")
    op.create_unique_constraint("uq_ingredient_org_code", "ingredients", ["org_id", "code"])
    op.create_index("ix_ingredients_code", "ingredients", ["code"], unique=False)

    # stock_in.batch_no
    _safe_drop_index("ix_stock_in_batch_no", "stock_in")
    op.create_unique_constraint("uq_stock_in_org_batch", "stock_in", ["org_id", "batch_no"])
    op.create_index("ix_stock_in_batch_no", "stock_in", ["batch_no"], unique=False)

    # purchase_orders.order_no
    _safe_drop_index("ix_purchase_orders_order_no", "purchase_orders")
    op.create_unique_constraint("uq_purchase_order_org_no", "purchase_orders", ["org_id", "order_no"])
    op.create_index("ix_purchase_orders_order_no", "purchase_orders", ["order_no"], unique=False)

    # ===================================================================
    # 4. 金额字段 Float → Numeric（PostgreSQL 原生支持，SQLite 也兼容）
    # ===================================================================
    money_12 = sa.Numeric(12, 2)
    money_14 = sa.Numeric(14, 2)
    money_2_1 = sa.Numeric(2, 1)

    # suppliers.rating
    op.alter_column("suppliers", "rating", existing_type=sa.Float(), type_=money_2_1,
                    existing_server_default="5.0", server_default="5.0")

    # ingredients
    op.alter_column("ingredients", "safety_stock", existing_type=sa.Float(), type_=money_12,
                    existing_server_default="0", server_default="0")
    op.alter_column("ingredients", "current_stock", existing_type=sa.Float(), type_=money_12,
                    existing_server_default="0", server_default="0")

    # purchase_orders
    op.alter_column("purchase_orders", "total_amount", existing_type=sa.Float(), type_=money_14,
                    existing_server_default="0", server_default="0")

    # purchase_order_items
    op.alter_column("purchase_order_items", "quantity", existing_type=sa.Float(), type_=money_12)
    op.alter_column("purchase_order_items", "unit_price", existing_type=sa.Float(), type_=money_12)
    op.alter_column("purchase_order_items", "total_price", existing_type=sa.Float(), type_=money_14)

    # stock_in
    op.alter_column("stock_in", "quantity", existing_type=sa.Float(), type_=money_12)
    op.alter_column("stock_in", "unit_price", existing_type=sa.Float(), type_=money_12)
    op.alter_column("stock_in", "total_price", existing_type=sa.Float(), type_=money_14)

    # stock_out
    op.alter_column("stock_out", "quantity", existing_type=sa.Float(), type_=money_12)
    op.alter_column("stock_out", "unit_price", existing_type=sa.Float(), type_=money_12)
    op.alter_column("stock_out", "total_price", existing_type=sa.Float(), type_=money_14)

    # inventory_checks
    op.alter_column("inventory_checks", "system_stock", existing_type=sa.Float(), type_=money_12)
    op.alter_column("inventory_checks", "actual_stock", existing_type=sa.Float(), type_=money_12)
    op.alter_column("inventory_checks", "difference", existing_type=sa.Float(), type_=money_12)

    # ===================================================================
    # 5. DateTime → timezone=True（PostgreSQL 原生支持）
    # ===================================================================
    if not _is_sqlite():
        tz_dt = sa.DateTime(timezone=True)
        for table, cols in [
            ("users", ["last_login", "created_at", "updated_at"]),
            ("organizations", ["created_at", "updated_at"]),
            ("suppliers", ["created_at", "updated_at"]),
            ("ingredients", ["created_at", "updated_at"]),
            ("purchase_orders", ["delivery_date", "approved_at", "created_at"]),
            ("stock_in", ["production_date", "expiry_date", "created_at"]),
            ("stock_out", ["created_at"]),
            ("inventory_checks", ["created_at"]),
            ("trace_records", ["production_date", "expiry_date", "created_at"]),
            ("audit_logs", ["created_at"]),
        ]:
            for col in cols:
                try:
                    op.alter_column(table, col, existing_type=sa.DateTime(), type_=tz_dt)
                except Exception as e:
                    logger.warning(f"alter_column {table}.{col} timezone skipped: {e}")

    # ===================================================================
    # 6. CHECK 约束
    # ===================================================================
    op.create_check_constraint("ck_org_no_self_ref", "organizations",
                               "parent_id IS NULL OR parent_id <> id")
    op.create_check_constraint("ck_supplier_rating_range", "suppliers",
                               "rating >= 0 AND rating <= 5")
    op.create_check_constraint("ck_ingredient_safety_stock_nonneg", "ingredients", "safety_stock >= 0")
    op.create_check_constraint("ck_ingredient_current_stock_nonneg", "ingredients", "current_stock >= 0")
    op.create_check_constraint("ck_poi_quantity_nonneg", "purchase_order_items", "quantity >= 0")
    op.create_check_constraint("ck_poi_unit_price_nonneg", "purchase_order_items", "unit_price >= 0")
    op.create_check_constraint("ck_poi_total_price_nonneg", "purchase_order_items", "total_price >= 0")
    op.create_check_constraint("ck_stock_in_quantity_nonneg", "stock_in", "quantity >= 0")
    op.create_check_constraint("ck_stock_in_unit_price_nonneg", "stock_in", "unit_price >= 0")
    op.create_check_constraint("ck_stock_in_total_price_nonneg", "stock_in", "total_price >= 0")
    op.create_check_constraint("ck_stock_in_expiry_after_production", "stock_in",
                               "expiry_date IS NULL OR production_date IS NULL OR expiry_date > production_date")
    op.create_check_constraint("ck_stock_out_quantity_nonneg", "stock_out", "quantity >= 0")
    op.create_check_constraint("ck_invchk_system_nonneg", "inventory_checks", "system_stock >= 0")
    op.create_check_constraint("ck_invchk_actual_nonneg", "inventory_checks", "actual_stock >= 0")

    # ===================================================================
    # 7. 外键 ondelete 策略（仅 PostgreSQL，SQLite 静默跳过）
    # ===================================================================
    if not _is_sqlite():
        _recreate_fk_with_ondelete()

    # ===================================================================
    # 8. 补 updated_at 列（模型新增，迁移需对齐）
    # ===================================================================
    try:
        op.add_column("organizations", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    except Exception:
        pass
    try:
        op.add_column("ingredients", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    except Exception:
        pass

    # audit_logs.user_agent 扩展到 500
    if not _is_sqlite():
        try:
            op.alter_column("audit_logs", "user_agent", existing_type=sa.String(255), type_=sa.String(500))
        except Exception as e:
            logger.warning(f"alter audit_logs.user_agent skipped: {e}")


def _recreate_fk_with_ondelete():
    """重建外键以添加 ondelete 策略（仅 PostgreSQL）。"""
    fk_defs = [
        # (constraint_name, table, column, ref_table, ref_column, ondelete)
        ("fk_users_org_id", "users", "org_id", "organizations", "id", "SET NULL"),
        ("fk_organizations_parent_id", "organizations", "parent_id", "organizations", "id", "RESTRICT"),
        ("fk_suppliers_org_id_new", "suppliers", "org_id", "organizations", "id", "RESTRICT"),
        ("fk_categories_org_id_new", "categories", "org_id", "organizations", "id", "RESTRICT"),
        ("fk_ingredients_category_id", "ingredients", "category_id", "categories", "id", "SET NULL"),
        ("fk_ingredients_supplier_id", "ingredients", "supplier_id", "suppliers", "id", "SET NULL"),
        ("fk_ingredients_org_id", "ingredients", "org_id", "organizations", "id", "RESTRICT"),
        ("fk_poi_order_id", "purchase_order_items", "order_id", "purchase_orders", "id", "CASCADE"),
        ("fk_poi_ingredient_id", "purchase_order_items", "ingredient_id", "ingredients", "id", "SET NULL"),
        ("fk_stock_in_ingredient_id", "stock_in", "ingredient_id", "ingredients", "id", "RESTRICT"),
        ("fk_stock_in_supplier_id", "stock_in", "supplier_id", "suppliers", "id", "SET NULL"),
        ("fk_stock_in_order_id", "stock_in", "order_id", "purchase_orders", "id", "SET NULL"),
        ("fk_stock_in_inspector1", "stock_in", "inspector1_id", "users", "id", "SET NULL"),
        ("fk_stock_in_inspector2", "stock_in", "inspector2_id", "users", "id", "SET NULL"),
        ("fk_stock_in_operator_id", "stock_in", "operator_id", "users", "id", "SET NULL"),
        ("fk_stock_in_org_id_new", "stock_in", "org_id", "organizations", "id", "RESTRICT"),
        ("fk_stock_out_ingredient_id", "stock_out", "ingredient_id", "ingredients", "id", "RESTRICT"),
        ("fk_stock_out_operator_id", "stock_out", "operator_id", "users", "id", "SET NULL"),
        ("fk_stock_out_org_id_new", "stock_out", "org_id", "organizations", "id", "RESTRICT"),
        ("fk_invchk_ingredient_id", "inventory_checks", "ingredient_id", "ingredients", "id", "RESTRICT"),
        ("fk_invchk_operator_id", "inventory_checks", "operator_id", "users", "id", "SET NULL"),
        ("fk_invchk_org_id_new", "inventory_checks", "org_id", "organizations", "id", "RESTRICT"),
        ("fk_trace_ingredient_id", "trace_records", "ingredient_id", "ingredients", "id", "RESTRICT"),
        ("fk_trace_supplier_id", "trace_records", "supplier_id", "suppliers", "id", "SET NULL"),
        ("fk_trace_stock_in_id", "trace_records", "stock_in_id", "stock_in", "id", "SET NULL"),
        ("fk_trace_org_id_new", "trace_records", "org_id", "organizations", "id", "RESTRICT"),
        ("fk_audit_user_id", "audit_logs", "user_id", "users", "id", "SET NULL"),
    ]

    for name, table, col, ref_table, ref_col, ondelete in fk_defs:
        try:
            # 尝试删除旧约束（名称可能不同，用 batch 模式更安全）
            op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
        except Exception:
            pass
        try:
            op.create_foreign_key(name, table, ref_table, [col], [ref_col], ondelete=ondelete)
        except Exception as e:
            logger.warning(f"recreate FK {name} on {table}.{col} skipped: {e}")


def downgrade():
    # 本迁移涉及大量 schema 修复，downgrade 仅回滚关键结构变更
    # 复合唯一约束 → 回到单列 unique
    _safe_drop_constraint("uq_supplier_org_code", "suppliers")
    _safe_drop_constraint("uq_category_org_code", "categories")
    _safe_drop_constraint("uq_ingredient_org_code", "ingredients")
    _safe_drop_constraint("uq_stock_in_org_batch", "stock_in")
    _safe_drop_constraint("uq_purchase_order_org_no", "purchase_orders")

    # 恢复单列 unique 索引
    op.create_index("ix_suppliers_code", "suppliers", ["code"], unique=True)
    op.create_index("ix_categories_code", "categories", ["code"], unique=True)
    op.create_index("ix_ingredients_code", "ingredients", ["code"], unique=True)
    op.create_index("ix_stock_in_batch_no", "stock_in", ["batch_no"], unique=True)
    op.create_index("ix_purchase_orders_order_no", "purchase_orders", ["order_no"], unique=True)

    # 删除补加的 org_id 列
    op.drop_constraint("fk_suppliers_org_id", "suppliers", type_="foreignkey")
    op.drop_index("ix_suppliers_org_id", table_name="suppliers")
    op.drop_column("suppliers", "org_id")

    op.drop_constraint("fk_categories_org_id", "categories", type_="foreignkey")
    op.drop_index("ix_categories_org_id", table_name="categories")
    op.drop_column("categories", "org_id")

    op.drop_constraint("fk_audit_logs_org_id", "audit_logs", type_="foreignkey")
    op.drop_index("ix_audit_logs_org_id", table_name="audit_logs")
    op.drop_column("audit_logs", "org_id")
