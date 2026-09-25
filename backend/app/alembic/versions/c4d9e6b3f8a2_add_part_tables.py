"""add part and work_order_part tables

Parts live in a reusable catalog; work orders reference them through a
work_order_part line-item table that captures quantity and the unit price
that applied at the time.

Revision ID: c4d9e6b3f8a2
Revises: b8e4d2f7a1c6
Create Date: 2026-09-25 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "c4d9e6b3f8a2"
down_revision = "b8e4d2f7a1c6"
branch_labels = None
depends_on = None

UOM_VALUES = ("EA", "BOX", "CASE", "KG", "G", "L", "M", "HR", "SET")


def upgrade() -> None:
    op.create_table(
        "part",
        sa.Column("part_number", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column(
            "manufacturer", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column(
            "unit_of_measure",
            sa.Enum(*UOM_VALUES, name="partunitofmeasure"),
            nullable=False,
        ),
        sa.Column("list_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_part_part_number"), "part", ["part_number"], unique=True
    )

    op.create_table(
        "work_order_part",
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("part_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["work_order.id"],
            name="fk_work_order_part_work_order_id_work_order",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["part_id"],
            ["part.id"],
            name="fk_work_order_part_part_id_part",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "work_order_id",
            "part_id",
            name="uq_work_order_part_work_order_id_part_id",
        ),
    )
    op.create_index(
        op.f("ix_work_order_part_part_id"), "work_order_part", ["part_id"]
    )
    op.create_index(
        op.f("ix_work_order_part_work_order_id"),
        "work_order_part",
        ["work_order_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_work_order_part_work_order_id"), table_name="work_order_part")
    op.drop_index(op.f("ix_work_order_part_part_id"), table_name="work_order_part")
    op.drop_table("work_order_part")
    op.drop_index(op.f("ix_part_part_number"), table_name="part")
    op.drop_table("part")
    sa.Enum(name="partunitofmeasure").drop(op.get_bind(), checkfirst=True)
