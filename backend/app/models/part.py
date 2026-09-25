import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import ConfigDict
from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


class PartUnitOfMeasure(StrEnum):
    """Units a part can be stocked or issued in."""

    EACH = "EA"
    BOX = "BOX"
    CASE = "CASE"
    KILOGRAM = "KG"
    GRAM = "G"
    LITRE = "L"
    METRE = "M"
    HOUR = "HR"
    SET = "SET"


class PartBase(SQLModel):
    part_number: str = Field(
        index=True,
        min_length=1,
        max_length=64,
        description="Unique manufacturer or internal part number.",
        schema_extra={"example": "BRG-6205-2RS"},
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Description of the part.",
        schema_extra={"example": "Deep groove ball bearing 6205-2RS"},
    )
    manufacturer: str | None = Field(
        default=None,
        max_length=255,
        description="Manufacturer or supplier of the part.",
        schema_extra={"example": "SKF"},
    )
    unit_of_measure: PartUnitOfMeasure = Field(
        default=PartUnitOfMeasure.EACH,
        sa_type=SAEnum(  # type: ignore
            PartUnitOfMeasure,
            name="partunitofmeasure",
            values_callable=lambda e: [m.value for m in e],
        ),
        description="Unit the part is stocked and issued in.",
        schema_extra={"example": PartUnitOfMeasure.EACH},
    )
    list_price: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        ge=0,
        description="Current list price per unit, before any discount.",
        schema_extra={"example": "24.95"},
    )
    is_active: bool = Field(
        default=True,
        description="Whether the part can be added to new work orders.",
        schema_extra={"example": True},
    )


class PartCreate(PartBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "part_number": "BRG-6205-2RS",
                "description": "Deep groove ball bearing 6205-2RS",
                "manufacturer": "SKF",
                "unit_of_measure": "EA",
                "list_price": "24.95",
                "is_active": True,
            }
        }
    )


class PartUpdate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Deep groove ball bearing 6205-2RS C3",
                "list_price": "27.50",
            }
        }
    )

    part_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Updated unique part number.",
        schema_extra={"example": "BRG-6205-2RS-C3"},
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Updated description of the part.",
        schema_extra={"example": "Deep groove ball bearing 6205-2RS C3"},
    )
    manufacturer: str | None = Field(
        default=None,
        max_length=255,
        description="Updated manufacturer or supplier.",
        schema_extra={"example": "NSK"},
    )
    unit_of_measure: PartUnitOfMeasure | None = Field(
        default=None,
        description="Updated unit the part is stocked in.",
        schema_extra={"example": PartUnitOfMeasure.BOX},
    )
    list_price: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        ge=0,
        description="Updated list price per unit.",
        schema_extra={"example": "27.50"},
    )
    is_active: bool | None = Field(
        default=None,
        description="Updated active status for the part.",
        schema_extra={"example": False},
    )


class Part(PartBase, table=True):
    __tablename__ = "part"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="Unique identifier for the part.",
        schema_extra={"example": "3b1a9c22-7f4e-4c1b-9a55-2d8f6e0c1a77"},
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        description="Timestamp when the part record was created.",
        schema_extra={"example": "2026-09-25T10:00:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
        description="Timestamp when the part record was last updated.",
        schema_extra={"example": "2026-09-26T10:00:00Z"},
    )


class PartPublic(PartBase):
    id: uuid.UUID = Field(
        description="Unique identifier for the part.",
        schema_extra={"example": "3b1a9c22-7f4e-4c1b-9a55-2d8f6e0c1a77"},
    )
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when the part record was created.",
        schema_extra={"example": "2026-09-25T10:00:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the part record was last updated.",
        schema_extra={"example": "2026-09-26T10:00:00Z"},
    )


class PartsPublic(SQLModel):
    data: list[PartPublic] = Field(
        description="List of parts returned by the API.",
        schema_extra={
            "example": [
                {
                    "id": "3b1a9c22-7f4e-4c1b-9a55-2d8f6e0c1a77",
                    "part_number": "BRG-6205-2RS",
                    "description": "Deep groove ball bearing 6205-2RS",
                    "unit_of_measure": "EA",
                    "list_price": "24.95",
                }
            ]
        },
    )
    count: int = Field(
        description="Total number of parts in the result set.",
        schema_extra={"example": 1},
    )


class WorkOrderPartBase(SQLModel):
    quantity: int = Field(
        default=1,
        ge=1,
        description="Number of units of the part required.",
        schema_extra={"example": 2},
    )
    unit_price: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        ge=0,
        description=(
            "Price per unit captured when the part was added, so historical "
            "work orders keep the price that applied at the time."
        ),
        schema_extra={"example": "24.95"},
    )


class WorkOrderPartCreate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "part_id": "3b1a9c22-7f4e-4c1b-9a55-2d8f6e0c1a77",
                "quantity": 2,
            }
        }
    )
    part_id: uuid.UUID = Field(
        description="Part to attach to the work order.",
        schema_extra={"example": "3b1a9c22-7f4e-4c1b-9a55-2d8f6e0c1a77"},
    )
    quantity: int = Field(
        default=1,
        ge=1,
        description="Number of units of the part required.",
        schema_extra={"example": 2},
    )
    unit_price: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        ge=0,
        description=(
            "Optional price override. Defaults to the part's current list price."
        ),
        schema_extra={"example": "24.95"},
    )


class WorkOrderPartUpdate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"quantity": 3, "unit_price": "22.50"}}
    )

    quantity: int | None = Field(
        default=None,
        ge=1,
        description="Updated number of units required.",
        schema_extra={"example": 3},
    )
    unit_price: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        ge=0,
        description="Updated price per unit for this work order.",
        schema_extra={"example": "22.50"},
    )


class WorkOrderPart(WorkOrderPartBase, table=True):
    __tablename__ = "work_order_part"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="Unique identifier for the work order line item.",
        schema_extra={"example": "8c4d2e51-1a7b-4f9e-b3d2-6e5a9c0b4d18"},
    )
    work_order_id: uuid.UUID = Field(
        foreign_key="work_order.id",
        index=True,
        ondelete="CASCADE",
        description="Work order the part belongs to.",
        schema_extra={"example": "1f824249-0442-431c-9aba-f26fa07aacef"},
    )
    part_id: uuid.UUID = Field(
        foreign_key="part.id",
        index=True,
        ondelete="RESTRICT",
        description="Part referenced by this line item.",
        schema_extra={"example": "3b1a9c22-7f4e-4c1b-9a55-2d8f6e0c1a77"},
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        description="Timestamp when the line item was created.",
        schema_extra={"example": "2026-09-25T10:05:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
        description="Timestamp when the line item was last updated.",
        schema_extra={"example": "2026-09-25T11:00:00Z"},
    )


class WorkOrderPartPublic(WorkOrderPartBase):
    id: uuid.UUID = Field(
        description="Unique identifier for the work order line item.",
        schema_extra={"example": "8c4d2e51-1a7b-4f9e-b3d2-6e5a9c0b4d18"},
    )
    work_order_id: uuid.UUID = Field(
        description="Work order the part belongs to.",
        schema_extra={"example": "1f824249-0442-431c-9aba-f26fa07aacef"},
    )
    part_id: uuid.UUID = Field(
        description="Part referenced by this line item.",
        schema_extra={"example": "3b1a9c22-7f4e-4c1b-9a55-2d8f6e0c1a77"},
    )
    part_number: str = Field(
        description="Part number, denormalised for display convenience.",
        schema_extra={"example": "BRG-6205-2RS"},
    )
    part_description: str | None = Field(
        default=None,
        description="Part description, denormalised for display convenience.",
        schema_extra={"example": "Deep groove ball bearing 6205-2RS"},
    )
    line_total: Decimal = Field(
        description="quantity multiplied by unit_price.",
        schema_extra={"example": "49.90"},
    )
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when the line item was created.",
        schema_extra={"example": "2026-09-25T10:05:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the line item was last updated.",
        schema_extra={"example": "2026-09-25T11:00:00Z"},
    )


class WorkOrderPartsPublic(SQLModel):
    data: list[WorkOrderPartPublic] = Field(
        description="List of parts attached to the work order.",
        schema_extra={
            "example": [
                {
                    "id": "8c4d2e51-1a7b-4f9e-b3d2-6e5a9c0b4d18",
                    "part_number": "BRG-6205-2RS",
                    "quantity": 2,
                    "unit_price": "24.95",
                    "line_total": "49.90",
                }
            ]
        },
    )
    count: int = Field(
        description="Total number of line items in the result set.",
        schema_extra={"example": 1},
    )


def quantize_money(value: Decimal) -> Decimal:
    """Round a monetary amount to two decimal places."""
    return value.quantize(Decimal("0.01"))
