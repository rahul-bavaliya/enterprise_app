import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import ConfigDict, field_validator
from sqlmodel import Field, SQLModel

from .part import WorkOrderPartPublic


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
        description="Current lifecycle status of the work order.",
        schema_extra={"example": WorkOrderStatus.OPEN},
    )
    priority: WorkOrderPriority = Field(
        default=WorkOrderPriority.MEDIUM,
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
    quoted_labor_hours: Decimal | None = Field(
        default=None,
        max_digits=8,
        decimal_places=2,
        ge=0,
        description="Quoted labor time for this work order.",
        schema_extra={"example": "4.00"},
    )
    segment_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Required reason when continuing an active work-order group.",
        schema_extra={"example": "Customer requested a follow-up visit."},
    )
    assigned_user_id: uuid.UUID | None = Field(
        default=None,
        description="User account the work is assigned to.",
        schema_extra={"example": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a"},
    )
    actual_labor_hours: Decimal | None = Field(
        default=None,
        max_digits=8,
        decimal_places=2,
        ge=0,
        description="Labor time actually spent on this work order.",
        schema_extra={"example": "3.50"},
    )
    labor_rate: Decimal | None = Field(
        default=None,
        max_digits=10,
        decimal_places=2,
        ge=0,
        description="Hourly labor rate used to price this work order.",
        schema_extra={"example": "95.00"},
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
    customer_id: uuid.UUID | None = Field(
        default=None,
        description="Customer the work is carried out for.",
        schema_extra={"example": "5d1b7e93-2c48-4a6f-9b31-7e0d5c2a8f14"},
    )
    fleet_id: uuid.UUID | None = Field(
        default=None,
        description="Customer asset selected for this work order.",
        schema_extra={"example": "9a3d6c18-77b2-4e05-8c41-2d9f0b7a6e53"},
    )
    customerless_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Optional reason when the work order has no customer.",
        schema_extra={"example": "Emergency callout, customer not yet registered."},
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
        description="Updated free-text assignee of the work order.",
        schema_extra={"example": "John Smith"},
    )
    assigned_user_id: uuid.UUID | None = Field(
        default=None,
        description="Updated user account the work is assigned to.",
        schema_extra={"example": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a"},
    )
    actual_labor_hours: Decimal | None = Field(
        default=None,
        max_digits=8,
        decimal_places=2,
        ge=0,
        description="Updated labor time actually spent on the work order.",
        schema_extra={"example": "3.50"},
    )
    labor_rate: Decimal | None = Field(
        default=None,
        max_digits=10,
        decimal_places=2,
        ge=0,
        description="Updated hourly labor rate used to price the work order.",
        schema_extra={"example": "95.00"},
    )
    quoted_labor_hours: Decimal | None = Field(
        default=None,
        max_digits=8,
        decimal_places=2,
        ge=0,
        description="Updated quoted labor time for the work order.",
        schema_extra={"example": "4.00"},
    )
    segment_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Updated reason for continuing an active work-order group.",
        schema_extra={"example": "Customer requested a follow-up visit."},
    )
    branch_id: uuid.UUID | None = Field(
        default=None,
        description="Updated branch the work order is assigned to.",
        schema_extra={"example": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d"},
    )
    customer_id: uuid.UUID | None = Field(
        default=None,
        description="Updated customer for the work order.",
        schema_extra={"example": "5d1b7e93-2c48-4a6f-9b31-7e0d5c2a8f14"},
    )
    fleet_id: uuid.UUID | None = Field(
        default=None,
        description="Updated customer asset for the work order.",
        schema_extra={"example": "9a3d6c18-77b2-4e05-8c41-2d9f0b7a6e53"},
    )
    customerless_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Updated reason for having no customer.",
        schema_extra={"example": "Walk-in request."},
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
    customer_id: uuid.UUID | None = Field(
        default=None,
        description="Customer the work is carried out for.",
        schema_extra={"example": "5d1b7e93-2c48-4a6f-9b31-7e0d5c2a8f14"},
    )
    fleet_id: uuid.UUID | None = Field(
        default=None,
        description="Customer asset selected for this work order.",
        schema_extra={"example": "9a3d6c18-77b2-4e05-8c41-2d9f0b7a6e53"},
    )
    customerless_reason: str | None = Field(
        default=None,
        description="Reason recorded when this work order has no customer.",
        schema_extra={"example": "Emergency callout."},
    )
    work_order_number: str | None = Field(
        default=None,
        description="Generated human-readable work order reference.",
        schema_extra={"example": "NYC-0926-0001"},
    )
    segment: int = Field(
        default=1,
        description="Segment position within the work-order group.",
        schema_extra={"example": 1},
    )
    parent_work_order_id: uuid.UUID | None = Field(
        default=None,
        description="Previous segment in the work-order group.",
        schema_extra={"example": "1f824249-0442-431c-9aba-f26fa07aacef"},
    )
    assigned_user_id: uuid.UUID | None = Field(
        default=None,
        description="User account the work is assigned to.",
        schema_extra={"example": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a"},
    )
    started_at: datetime | None = Field(
        default=None,
        description="When work first moved into progress. Empty until then.",
        schema_extra={"example": "2026-09-25T09:00:00Z"},
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When the work order was completed. Empty until then.",
        schema_extra={"example": "2026-09-25T15:30:00Z"},
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


class WorkOrderEventType(StrEnum):
    """Kinds of entries recorded on a work order's timeline."""

    CREATED = "created"
    NOTE = "note"
    STATUS_CHANGED = "status_changed"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    REOPENED = "reopened"
    VOIDED = "voided"
    PART_ADDED = "part_added"
    PART_REMOVED = "part_removed"


class WorkOrderNoteCreate(SQLModel):
    """Payload for appending a hand-written note to a work order."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "body": "Replaced the failed capacitor and tested under load.",
            }
        }
    )

    body: str = Field(
        min_length=1,
        max_length=2000,
        description="Note text. Whitespace-only notes are rejected.",
        schema_extra={"example": "Replaced the failed capacitor and tested."},
    )

    @field_validator("body")
    @classmethod
    def _reject_blank_body(cls, value: str) -> str:
        """Reject whitespace-only notes here so they fail as 422, not 409."""
        if not value.strip():
            raise ValueError("A note cannot be empty")
        return value


class WorkOrderEventPublic(SQLModel):
    event_type: WorkOrderEventType = Field(
        description="Kind of activity this entry records.",
        schema_extra={"example": WorkOrderEventType.NOTE},
    )
    body: str | None = Field(
        default=None,
        description=(
            "Free-text detail. Always set for a note, optional for an automated "
            "event such as a status change."
        ),
        schema_extra={"example": "Replaced the failed capacitor and tested."},
    )
    from_status: WorkOrderStatus | None = Field(
        default=None,
        description="Status the work order held before the event. Set on status changes.",
        schema_extra={"example": WorkOrderStatus.OPEN},
    )
    to_status: WorkOrderStatus | None = Field(
        default=None,
        description="Status the work order moved to. Set on status changes.",
        schema_extra={"example": WorkOrderStatus.IN_PROGRESS},
    )
    id: uuid.UUID = Field(
        description="Unique identifier for the timeline entry.",
        schema_extra={"example": "3d7b9a11-0c2e-4f5a-8e13-6b4d2a9c7e50"},
    )
    work_order_id: uuid.UUID = Field(
        description="Work order the entry belongs to.",
        schema_extra={"example": "1f824249-0442-431c-9aba-f26fa07aacef"},
    )
    author_id: uuid.UUID | None = Field(
        default=None,
        description="User who caused the entry. Empty when the account was deleted.",
        schema_extra={"example": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a"},
    )
    author_name: str | None = Field(
        default=None,
        description="Display name of the author, captured so history survives deletion.",
        schema_extra={"example": "Jane Doe"},
    )
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when the entry was recorded.",
        schema_extra={"example": "2026-09-25T11:20:00Z"},
    )


class WorkOrderClose(SQLModel):
    """Optional extras recorded when a work order is completed."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "actual_labor_hours": "3.50",
                "body": "Replaced the compressor and verified under load.",
            }
        }
    )

    actual_labor_hours: Decimal | None = Field(
        default=None,
        max_digits=8,
        decimal_places=2,
        ge=0,
        description="Labor time actually spent, recorded on the work order.",
        schema_extra={"example": "3.50"},
    )
    body: str | None = Field(
        default=None,
        max_length=2000,
        description="Closing note explaining what was done. Added to the timeline.",
        schema_extra={"example": "Replaced the compressor and verified under load."},
    )


class WorkOrderReopen(SQLModel):
    """Reason recorded when a closed work order is returned to open."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "body": "Compressor failed again within the warranty period.",
            }
        }
    )

    body: str | None = Field(
        default=None,
        max_length=2000,
        description="Why the work order is being reopened. Added to the timeline.",
        schema_extra={"example": "Compressor failed again within the warranty period."},
    )


class WorkOrderTotals(SQLModel):
    """Money and time roll-up for one work order."""

    parts_total: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="Sum of quantity times unit price across all parts lines.",
        schema_extra={"example": "149.70"},
    )
    labor_hours: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=8,
        decimal_places=2,
        description="Actual labor hours billed, falling back to quoted hours when unset.",
        schema_extra={"example": "3.50"},
    )
    labor_total: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="Labor hours multiplied by the labor rate.",
        schema_extra={"example": "332.50"},
    )
    total_cost: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="Parts total plus labor total.",
        schema_extra={"example": "482.20"},
    )


class WorkOrderSummary(SQLModel):
    """Everything a client needs to render one work order screen."""

    work_order: WorkOrderPublic = Field(description="The work order itself.")
    parts: list[WorkOrderPartPublic] = Field(
        default_factory=list,
        description="Parts attached to this work order.",
    )
    events: list[WorkOrderEventPublic] = Field(
        default_factory=list,
        description="Timeline entries, oldest first.",
    )
    totals: WorkOrderTotals = Field(
        default_factory=WorkOrderTotals,
        description="Computed parts, labor, and combined totals.",
    )
