"""add work order assignment, labor actuals, and activity timeline

Revision ID: b8f3c2d7e914
Revises: d4f6a8c1e2b7
Create Date: 2026-09-25 12:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b8f3c2d7e914"
down_revision = "d4f6a8c1e2b7"
branch_labels = None
depends_on = None

userrole = postgresql.ENUM(
    "admin", "dispatcher", "technician", name="userrole", create_type=False
)
workordereventtype = postgresql.ENUM(
    "created",
    "note",
    "status_changed",
    "assigned",
    "completed",
    "reopened",
    "voided",
    "part_added",
    "part_removed",
    name="workordereventtype",
    create_type=False,
)
# The work-order status type already exists, so these columns only reference it.
workorderstatus = postgresql.ENUM(
    "open",
    "in_progress",
    "completed",
    "cancelled",
    "voided",
    name="workorderstatus",
    create_type=False,
)


def upgrade() -> None:
    userrole.create(op.get_bind(), checkfirst=True)
    workordereventtype.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "user",
        sa.Column(
            "role",
            userrole,
            nullable=False,
            server_default="technician",
        ),
    )
    op.add_column(
        "user",
        sa.Column("branch_id", sa.Uuid(), nullable=True),
    )
    op.create_index(op.f("ix_user_branch_id"), "user", ["branch_id"], unique=False)
    op.create_foreign_key(
        "fk_user_branch_id_branch",
        "user",
        "branch",
        ["branch_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "work_order",
        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "work_order",
        sa.Column("actual_labor_hours", sa.Numeric(8, 2), nullable=True),
    )
    op.add_column(
        "work_order",
        sa.Column("labor_rate", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "work_order",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "work_order",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_work_order_assigned_user_id"),
        "work_order",
        ["assigned_user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_work_order_assigned_user_id_user",
        "work_order",
        "user",
        ["assigned_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "work_order_event",
        sa.Column("event_type", workordereventtype, nullable=False),
        sa.Column("body", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column("from_status", workorderstatus, nullable=True),
        sa.Column("to_status", workorderstatus, nullable=True),
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column(
            "author_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["user.id"],
            name="fk_work_order_event_author_id_user",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["work_order.id"],
            name="fk_work_order_event_work_order_id_work_order",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_work_order_event_work_order_id"),
        "work_order_event",
        ["work_order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_work_order_event_author_id"),
        "work_order_event",
        ["author_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_work_order_event_author_id"), table_name="work_order_event")
    op.drop_index(
        op.f("ix_work_order_event_work_order_id"), table_name="work_order_event"
    )
    op.drop_table("work_order_event")

    op.drop_constraint(
        "fk_work_order_assigned_user_id_user", "work_order", type_="foreignkey"
    )
    op.drop_index(op.f("ix_work_order_assigned_user_id"), table_name="work_order")
    op.drop_column("work_order", "completed_at")
    op.drop_column("work_order", "started_at")
    op.drop_column("work_order", "labor_rate")
    op.drop_column("work_order", "actual_labor_hours")
    op.drop_column("work_order", "assigned_user_id")

    op.drop_constraint("fk_user_branch_id_branch", "user", type_="foreignkey")
    op.drop_index(op.f("ix_user_branch_id"), table_name="user")
    op.drop_column("user", "branch_id")
    op.drop_column("user", "role")

    workordereventtype.drop(op.get_bind(), checkfirst=True)
    userrole.drop(op.get_bind(), checkfirst=True)
