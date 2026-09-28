import uuid
from datetime import UTC, datetime

from pydantic import ConfigDict
from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


class CustomerBase(SQLModel):
    name: str = Field(
        index=True,
        min_length=1,
        max_length=255,
        description="Registered customer or company name.",
        schema_extra={"example": "Acme Facilities Ltd"},
    )
    contact_person: str | None = Field(
        default=None,
        max_length=255,
        description="Primary contact for the customer.",
        schema_extra={"example": "Jane Doe"},
    )
    email: str | None = Field(
        default=None,
        max_length=320,
        description="Contact email address.",
        schema_extra={"example": "jane.doe@acme.test"},
    )
    phone: str | None = Field(
        default=None,
        max_length=64,
        description="Contact phone number.",
        schema_extra={"example": "+1 555 0100"},
    )
    tax_id: str | None = Field(
        default=None,
        max_length=64,
        description="Tax or VAT registration identifier.",
        schema_extra={"example": "GB123456789"},
    )
    billing_address: str | None = Field(
        default=None,
        max_length=500,
        description="Billing address.",
        schema_extra={"example": "1 Market St, Springfield"},
    )
    service_address: str | None = Field(
        default=None,
        max_length=500,
        description="Address where field work is carried out.",
        schema_extra={"example": "22 Industrial Way, Springfield"},
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Free-form notes captured at registration.",
        schema_extra={"example": "Prefers morning site visits."},
    )
    is_active: bool = Field(
        default=True,
        description="Whether the customer can be selected on new work orders.",
        schema_extra={"example": True},
    )


class CustomerCreate(CustomerBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Facilities Ltd",
                "contact_person": "Jane Doe",
                "email": "jane.doe@acme.test",
                "phone": "+1 555 0100",
                "service_address": "22 Industrial Way, Springfield",
            }
        }
    )


class CustomerUpdate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "contact_person": "John Smith",
                "phone": "+1 555 0111",
            }
        }
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated customer name.",
        schema_extra={"example": "Acme Facilities Group"},
    )
    contact_person: str | None = Field(
        default=None,
        max_length=255,
        description="Updated primary contact.",
        schema_extra={"example": "John Smith"},
    )
    email: str | None = Field(
        default=None,
        max_length=320,
        description="Updated contact email.",
        schema_extra={"example": "john.smith@acme.test"},
    )
    phone: str | None = Field(
        default=None,
        max_length=64,
        description="Updated contact phone.",
        schema_extra={"example": "+1 555 0111"},
    )
    tax_id: str | None = Field(
        default=None,
        max_length=64,
        description="Updated tax or VAT identifier.",
        schema_extra={"example": "GB987654321"},
    )
    billing_address: str | None = Field(
        default=None,
        max_length=500,
        description="Updated billing address.",
        schema_extra={"example": "2 Market St, Springfield"},
    )
    service_address: str | None = Field(
        default=None,
        max_length=500,
        description="Updated service address.",
        schema_extra={"example": "24 Industrial Way, Springfield"},
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Updated notes.",
        schema_extra={"example": "Site access via security desk."},
    )
    is_active: bool | None = Field(
        default=None,
        description="Updated active status.",
        schema_extra={"example": False},
    )


class Customer(CustomerBase, table=True):
    __tablename__ = "customer"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="Unique identifier for the customer.",
        schema_extra={"example": "5d1b7e93-2c48-4a6f-9b31-7e0d5c2a8f14"},
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        description="Timestamp when the customer was registered.",
        schema_extra={"example": "2026-09-25T10:00:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
        description="Timestamp when the customer was last updated.",
        schema_extra={"example": "2026-09-26T10:00:00Z"},
    )


class CustomerPublic(CustomerBase):
    id: uuid.UUID = Field(
        description="Unique identifier for the customer.",
        schema_extra={"example": "5d1b7e93-2c48-4a6f-9b31-7e0d5c2a8f14"},
    )
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when the customer was registered.",
        schema_extra={"example": "2026-09-25T10:00:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the customer was last updated.",
        schema_extra={"example": "2026-09-26T10:00:00Z"},
    )


class CustomersPublic(SQLModel):
    data: list[CustomerPublic] = Field(
        description="List of customers returned by the API.",
        schema_extra={
            "example": [
                {
                    "id": "5d1b7e93-2c48-4a6f-9b31-7e0d5c2a8f14",
                    "name": "Acme Facilities Ltd",
                    "contact_person": "Jane Doe",
                }
            ]
        },
    )
    count: int = Field(
        description="Total number of customers in the result set.",
        schema_extra={"example": 1},
    )
