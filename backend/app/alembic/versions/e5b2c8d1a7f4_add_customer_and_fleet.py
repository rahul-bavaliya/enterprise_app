"""add customer and fleet tables, extend work order

Customers register with their full details, each customer's fleet holds the
machines they own, and a work order can point at both. Work orders gain an
auto-generated BranchCode-mmyy-0001 reference plus a segment number so one
job can span several phases.

Revision ID: e5b2c8d1a7f4
Revises: d7a1f4c9b2e5
Create Date: 2026-09-25 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "e5b2c8d1a7f4"
down_revision = "d7a1f4c9b2e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column(
            "contact_person", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=320), nullable=True),
        sa.Column("phone", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column("tax_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column(
            "billing_address", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column(
            "service_address", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customer_name"), "customer", ["name"], unique=False)

    op.create_table(
        "fleet",
        sa.Column("asset_tag", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("make", sqlmodel.sql.sqltypes.AutoString(length=128), nullable=True),
        sa.Column("model", sqlmodel.sql.sqltypes.AutoString(length=128), nullable=True),
        sa.Column(
            "serial_number", sqlmodel.sql.sqltypes.AutoString(length=128), nullable=True
        ),
        sa.Column("year_manufactured", sa.Integer(), nullable=True),
        sa.Column("meter_reading", sa.Numeric(14, 2), nullable=True),
        sa.Column("location", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customer.id"],
            name="fk_fleet_customer_id_customer",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fleet_asset_tag"), "fleet", ["asset_tag"], unique=False)
    op.create_index(op.f("ix_fleet_customer_id"), "fleet", ["customer_id"], unique=False)

    op.add_column(
        "work_order", sa.Column("customer_id", sa.Uuid(), nullable=True)
    )
    op.add_column("work_order", sa.Column("fleet_id", sa.Uuid(), nullable=True))
    op.add_column(
        "work_order",
        sa.Column(
            "customerless_reason",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
    )
    op.add_column(
        "work_order",
        sa.Column(
            "work_order_number", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True
        ),
    )
    op.add_column(
        "work_order",
        sa.Column("segment", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "work_order", sa.Column("parent_work_order_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_work_order_customer_id_customer",
        "work_order",
        "customer",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_work_order_fleet_id_fleet",
        "work_order",
        "fleet",
        ["fleet_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_work_order_parent_work_order_id_work_order",
        "work_order",
        "work_order",
        ["parent_work_order_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_work_order_customer_id"), "work_order", ["customer_id"], unique=False
    )
    op.create_index(op.f("ix_work_order_fleet_id"), "work_order", ["fleet_id"], unique=False)
    op.create_index(
        op.f("ix_work_order_work_order_number"),
        "work_order",
        ["work_order_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_work_order_parent_work_order_id"),
        "work_order",
        ["parent_work_order_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_work_order_parent_work_order_id"), table_name="work_order")
    op.drop_index(op.f("ix_work_order_work_order_number"), table_name="work_order")
    op.drop_index(op.f("ix_work_order_fleet_id"), table_name="work_order")
    op.drop_index(op.f("ix_work_order_customer_id"), table_name="work_order")
    op.drop_constraint("fk_work_order_parent_work_order_id_work_order", "work_order")
    op.drop_constraint("fk_work_order_fleet_id_fleet", "work_order")
    op.drop_constraint("fk_work_order_customer_id_customer", "work_order")
    op.drop_column("work_order", "parent_work_order_id")
    op.drop_column("work_order", "segment")
    op.drop_column("work_order", "work_order_number")
    op.drop_column("work_order", "customerless_reason")
    op.drop_column("work_order", "fleet_id")
    op.drop_column("work_order", "customer_id")

    op.drop_index(op.f("ix_fleet_customer_id"), table_name="fleet")
    op.drop_index(op.f("ix_fleet_asset_tag"), table_name="fleet")
    op.drop_table("fleet")
    op.drop_index(op.f("ix_customer_name"), table_name="customer")
    op.drop_table("customer")
