"""0002_add_org_id_to_stock_and_trace
Revision ID: 0002
Revises: 0001
Created Date: 2025-07-01
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    """给以下表添加 org_id 列，支持多租户隔离
    - stock_in
    - stock_out
    - inventory_checks
    - trace_records
    """
    for table_name in ("stock_in", "stock_out", "inventory_checks", "trace_records"):
        op.add_column(
            table_name,
            sa.Column("org_id", sa.Integer(), nullable=False, server_default="1"),
        )
        op.create_index(
            f"ix_{table_name}_org_id", table_name, ["org_id"], unique=False,
        )
        op.create_foreign_key(
            f"fk_{table_name}_org_id",
            table_name,
            "organizations",
            ["org_id"],
            ["id"],
        )

    # 去掉 server_default，让后续记录必须显式提供
    for table_name in ("stock_in", "stock_out", "inventory_checks", "trace_records"):
        op.alter_column(
            table_name, "org_id", existing_type=sa.Integer(), server_default=None,
        )


def downgrade():
    for table_name in ("stock_in", "stock_out", "inventory_checks", "trace_records"):
        op.drop_constraint(f"fk_{table_name}_org_id", table_name, type_="foreignkey")
        op.drop_index(f"ix_{table_name}_org_id", table_name=table_name)
        op.drop_column(table_name, "org_id")
