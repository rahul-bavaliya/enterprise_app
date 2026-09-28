import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class FleetBase(SQLModel):
    asset_tag: str = Field(
        index=True,
        min_length=1,
        max_length=64,
        description="Unique asset tag identifying the machine within the fleet.",
        schema_extra={"example": "ACME-PMP-001"},
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Description of the machine or vehicle.",
        schema_extra={"example": "Centrifugal pump, 22kW"},
    )
    make: str | None = Field(
        default=None,
        max_length=128,
        description="Manufacturer of the machine.",
        schema_extra={"example": "Grundfos"},
    )
    model: str | None = Field(
        default=None,
        max_length=128,
        description="Model designation.",
        schema_extra={"example": "NB 65-200"},
    )
    serial_number: str | None = Field(
        default=None,
        max_length=128,
        description="Manufacturer serial number.",
        schema_extra={"example": "GRU9928374"},
    )
    year_manufactured: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Year the machine was manufactured.",
        schema_extra={"example": 2019},
    )
    meter_reading: Decimal | None = Field(
        default=None,
        max_digits=14,
        decimal_places=2,
        ge=0,
        description=(
            "Latest meter or hour reading. Stored as money-grade numeric so "
            "large readings never lose precision."
        ),
        schema_extra={"example": "14250.00"},
    )
    location: str | None = Field(
        default=None,
        max_length=255,
        description="Where the machine is installed on site.",
        schema_extra={"example": "Pump house B"},
    )
    is_active: bool = Field(
        default=True,
        description="Whether the machine can be selected on new work orders.",
        schema_extra={"example": True},
    )


class FleetCreate(FleetBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "asset_tag": "ACME-PMP-001",
                "description": "Centrifugal pump, 22kW",
                "make": "Grundfos",
                "model": "NB 65-200",
                "serial_number": "GRU9928374",
                "year_manufactured": 2019,
                "meter_reading": "14250.00",
                "location": "Pump house B",
            }
        }
    )
    customer_id: uuid.UUID = Field(
        description="Customer this machine belongs to.",
        schema_extra={"example": "5d1b7e93-2c48-4a6f-9b31-7e0d5c2a8f14"},
    )


class FleetUpdate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"meter_reading": "14890.50", "location": "Pump house C"}
        }
    )

    asset_tag: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Updated asset tag.",
        schema_extra={"example": "ACME-PMP-002"},
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Updated description.",
        schema_extra={"example": "Centrifugal pump, 30kW"},
    )
    make: str | None = Field(
        default=None,
        max_length=128,
        description="Updated manufacturer.",
        schema_extra={"example": "Wilo"},
    )
    model: str | None = Field(
        default=None,
        max_length=128,
        description="Updated model designation.",
        schema_extra={"example": "Afero 3"},
    )
    serial_number: str | None = Field(
        default=None,
        max_length=128,
        description="Updated serial number.",
        schema_extra={"example": "WIL5512093"},
    )
    year_manufactured: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Updated manufacturing year.",
        schema_extra={"example": 2021},
    )
    meter_reading: Decimal | None = Field(
        default=None,
        max_digits=14,
        decimal_places=2,
        ge=0,
        description="Updated meter or hour reading.",
        schema_extra={"example": "14890.50"},
    )
    location: str | None = Field(
        default=None,
        max_length=255,
        description="Updated installation location.",
        schema_extra={"example": "Pump house C"},
    )
    is_active: bool | None = Field(
        default=None,
        description="Updated active status.",
        schema_extra={"example": False},
    )


class FleetPublic(FleetBase):
    id: uuid.UUID = Field(
        description="Unique identifier for the fleet asset.",
        schema_extra={"example": "9a3d6c18-77b2-4e05-8c41-2d9f0b7a6e53"},
    )
    customer_id: uuid.UUID = Field(
        description="Customer that owns this machine.",
        schema_extra={"example": "5d1b7e93-2c48-4a6f-9b31-7e0d5c2a8f14"},
    )
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when the machine was registered.",
        schema_extra={"example": "2026-09-25T10:05:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the machine was last updated.",
        schema_extra={"example": "2026-09-26T09:00:00Z"},
    )


class FleetsPublic(SQLModel):
    data: list[FleetPublic] = Field(
        description="List of fleet assets returned by the API.",
        schema_extra={
            "example": [
                {
                    "id": "9a3d6c18-77b2-4e05-8c41-2d9f0b7a6e53",
                    "asset_tag": "ACME-PMP-001",
                    "make": "Grundfos",
                }
            ]
        },
    )
    count: int = Field(
        description="Total number of fleet assets in the result set.",
        schema_extra={"example": 1},
    )
