"""add voided to workorderstatus enum

Work orders are now voided instead of hard-deleted, so the status enum needs
a terminal ``voided`` state.

Revision ID: b8e4d2f7a1c6
Revises: a7c3d9e1f4b2
Create Date: 2026-09-25 00:00:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "b8e4d2f7a1c6"
down_revision = "a7c3d9e1f4b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE workorderstatus ADD VALUE IF NOT EXISTS 'voided'")


def downgrade() -> None:
    # PostgreSQL cannot remove a single value from an enum. Rebuild the type
    # without 'voided' and remap any voided rows to 'cancelled' first.
    op.execute("UPDATE work_order SET status = 'cancelled' WHERE status = 'voided'")
    op.execute("ALTER TYPE workorderstatus RENAME TO workorderstatus_old")
    op.execute(
        "CREATE TYPE workorderstatus AS ENUM "
        "('open', 'in_progress', 'completed', 'cancelled')"
    )
    op.execute(
        "ALTER TABLE work_order ALTER COLUMN status TYPE workorderstatus "
        "USING status::text::workorderstatus"
    )
    op.execute("DROP TYPE workorderstatus_old")
