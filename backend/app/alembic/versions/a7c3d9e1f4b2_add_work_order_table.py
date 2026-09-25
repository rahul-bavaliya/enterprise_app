"""add work_order table

Revision ID: a7c3d9e1f4b2
Revises: d2b4c7d32a14
Create Date: 2026-09-24 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

# revision identifiers, used by Alembic.
revision = "a7c3d9e1f4b2"
down_revision = "d2b4c7d32a14"
branch_labels = None
depends_on = None

STATUS_VALUES = ("open", "in_progress", "completed", "cancelled")
PRIORITY_VALUES = ("low", "medium", "high", "urgent")


def upgrade() -> None:
    op.create_table(
        "work_order",
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True
        ),
        sa.Column(
            "status",
            sa.Enum(
                *STATUS_VALUES,
                name="workorderstatus",
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                *PRIORITY_VALUES,
                name="workorderpriority",
            ),
            nullable=False,
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "assigned_to", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("branch_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branch.id"],
            name="fk_work_order_branch_id_branch",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_work_order_title"), "work_order", ["title"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_work_order_title"), table_name="work_order")
    op.drop_table("work_order")
    sa.Enum(name="workorderpriority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="workorderstatus").drop(op.get_bind(), checkfirst=True)
