"""add indexes for common work order and part queries

The list endpoints filter by branch and status and sort by created_at. Without
indexes Postgres falls back to a sequential scan plus sort on each request.

Revision ID: d7a1f4c9b2e5
Revises: c4d9e6b3f8a2
Create Date: 2026-09-25 00:00:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "d7a1f4c9b2e5"
down_revision = "c4d9e6b3f8a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backs `WHERE branch_id = ...` combined with the created_at ordering.
    op.create_index(
        op.f("ix_work_order_branch_id_created_at"),
        "work_order",
        ["branch_id", "created_at"],
    )
    # Backs `WHERE status = ...` combined with the created_at ordering.
    op.create_index(
        op.f("ix_work_order_status_created_at"),
        "work_order",
        ["status", "created_at"],
    )
    # Backs the parts catalog filter on active flag.
    op.create_index(
        op.f("ix_part_is_active"), "part", ["is_active"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_part_is_active"), table_name="part")
    op.drop_index(
        op.f("ix_work_order_status_created_at"), table_name="work_order"
    )
    op.drop_index(
        op.f("ix_work_order_branch_id_created_at"), table_name="work_order"
    )
