import uuid
from datetime import UTC, date, datetime
from enum import StrEnum

from pydantic import ConfigDict
from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


class WorkOrderStatus(StrEnum):
    """Lifecycle states for a work order."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    VOIDED = "voided"


class WorkOrderPriority(StrEnum):
    """Relative urgency of a work order."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class WorkOrderBase(SQLModel):
    title: str = Field(
        min_length=1,
        max_length=255,
        description="Short summary of the work to be done.",
        schema_extra={"example": "Replace HVAC filter"},
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Detailed description of the requested work.",
        schema_extra={"example": "Quarterly filter replacement for units 1-3."},
    )
    status: WorkOrderStatus = Field(
        default=WorkOrderStatus.OPEN,
        sa_type=SAEnum(  # type: ignore
            WorkOrderStatus,
            name="workorderstatus",
            values_callable=lambda e: [m.value for m in e],
        ),
        description="Current lifecycle status of the work order.",
        schema_extra={"example": WorkOrderStatus.OPEN},
    )
    priority: WorkOrderPriority = Field(
        default=WorkOrderPriority.MEDIUM,
        sa_type=SAEnum(  # type: ignore
            WorkOrderPriority,
            name="workorderpriority",
            values_callable=lambda e: [m.value for m in e],
        ),
        description="Relative urgency of the work order.",
        schema_extra={"example": WorkOrderPriority.MEDIUM},
    )
    due_date: date | None = Field(
        default=None,
        description="Date by which the work order should be completed.",
        schema_extra={"example": "2026-10-01"},
    )
    assigned_to: str | None = Field(
        default=None,
        max_length=255,
        description="Name or identifier of the person responsible for the work.",
        schema_extra={"example": "Jane Doe"},
    )


class WorkOrderCreate(WorkOrderBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Replace HVAC filter",
                "description": "Quarterly filter replacement for units 1-3.",
                "status": "open",
                "priority": "medium",
                "due_date": "2026-10-01",
                "assigned_to": "Jane Doe",
                "branch_id": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d",
            }
        }
    )
    branch_id: uuid.UUID | None = Field(
        default=None,
        description="Branch the work order is assigned to.",
        schema_extra={"example": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d"},
    )


class WorkOrderUpdate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Replace HVAC filters",
                "status": "in_progress",
                "priority": "high",
                "assigned_to": "John Smith",
            }
        }
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated title for the work order.",
        schema_extra={"example": "Replace HVAC filters"},
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Updated description of the requested work.",
        schema_extra={"example": "Updated scope covering units 1-6."},
    )
    status: WorkOrderStatus | None = Field(
        default=None,
        description="Updated lifecycle status of the work order.",
        schema_extra={"example": WorkOrderStatus.IN_PROGRESS},
    )
    priority: WorkOrderPriority | None = Field(
        default=None,
        description="Updated urgency of the work order.",
        schema_extra={"example": WorkOrderPriority.HIGH},
    )
    due_date: date | None = Field(
        default=None,
        description="Updated target completion date.",
        schema_extra={"example": "2026-10-15"},
    )
    assigned_to: str | None = Field(
        default=None,
        max_length=255,
        description="Updated assignee of the work order.",
        schema_extra={"example": "John Smith"},
    )
    branch_id: uuid.UUID | None = Field(
        default=None,
        description="Updated branch the work order is assigned to.",
        schema_extra={"example": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d"},
    )


class WorkOrder(WorkOrderBase, table=True):
    __tablename__ = "work_order"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="Unique identifier for the work order.",
        schema_extra={"example": "0f8f1c64-9c1e-4b1e-9f1e-3f6f4b7b6f1a"},
    )
    branch_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="branch.id",
        nullable=True,
        ondelete="SET NULL",
        description="Branch the work order belongs to.",
        schema_extra={"example": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d"},
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        description="Timestamp when the work order was created.",
        schema_extra={"example": "2026-09-22T10:00:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
        description="Timestamp when the work order was last updated. Empty until first update.",
        schema_extra={"example": "2026-09-23T10:00:00Z"},
    )


class WorkOrderPublic(WorkOrderBase):
    id: uuid.UUID = Field(
        description="Unique identifier for the work order.",
        schema_extra={"example": "0f8f1c64-9c1e-4b1e-9f1e-3f6f4b7b6f1a"},
    )
    branch_id: uuid.UUID | None = Field(
        default=None,
        description="Branch the work order belongs to.",
        schema_extra={"example": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d"},
    )
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when the work order was created.",
        schema_extra={"example": "2026-09-22T10:00:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the work order was last updated.",
        schema_extra={"example": "2026-09-23T10:00:00Z"},
    )


class WorkOrdersPublic(SQLModel):
    data: list[WorkOrderPublic] = Field(
        description="List of work orders returned by the API.",
        schema_extra={
            "example": [
                {
                    "id": "0f8f1c64-9c1e-4b1e-9f1e-3f6f4b7b6f1a",
                    "title": "Replace HVAC filter",
                    "status": "open",
                    "priority": "medium",
                }
            ]
        },
    )
    count: int = Field(
        description="Total number of work orders in the result set.",
        schema_extra={"example": 1},
    )
