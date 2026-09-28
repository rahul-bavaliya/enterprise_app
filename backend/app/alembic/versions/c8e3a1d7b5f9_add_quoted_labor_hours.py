"""add quoted labor hours to work orders

Revision ID: c8e3a1d7b5f9
Revises: f2a6c9e4b7d1
Create Date: 2026-09-25 00:20:00.000000

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "c8e3a1d7b5f9"
down_revision = "f2a6c9e4b7d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "work_order",
        sa.Column("quoted_labor_hours", sa.Numeric(8, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("work_order", "quoted_labor_hours")
