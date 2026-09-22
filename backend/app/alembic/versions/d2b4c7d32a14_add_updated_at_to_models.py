"""Add updated_at to User, Item and Branch

Revision ID: d2b4c7d32a14
Revises: fe56fa70289e
Create Date: 2026-09-22 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

# revision identifiers, used by Alembic.
revision = "d2b4c7d32a14"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "branch", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "item", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "user", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("user", "updated_at")
    op.drop_column("item", "updated_at")
    op.drop_column("branch", "updated_at")
