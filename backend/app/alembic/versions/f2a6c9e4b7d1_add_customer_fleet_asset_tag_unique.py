"""make fleet asset tags unique per customer

Revision ID: f2a6c9e4b7d1
Revises: e5b2c8d1a7f4
Create Date: 2026-09-25 00:05:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "f2a6c9e4b7d1"
down_revision = "e5b2c8d1a7f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_fleet_customer_id_asset_tag", "fleet", ["customer_id", "asset_tag"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_fleet_customer_id_asset_tag", "fleet", type_="unique")
