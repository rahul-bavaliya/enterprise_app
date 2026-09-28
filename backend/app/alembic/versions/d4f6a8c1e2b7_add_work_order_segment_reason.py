"""add work order segment reason

Revision ID: d4f6a8c1e2b7
Revises: c8e3a1d7b5f9
Create Date: 2026-09-25 00:25:00.000000

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "d4f6a8c1e2b7"
down_revision = "c8e3a1d7b5f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "work_order",
        sa.Column("segment_reason", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("work_order", "segment_reason")
