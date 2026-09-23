import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Identity,
    Index,
    Integer,
    Numeric,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, SQLModel


class Branch(SQLModel, table=True):
    __tablename__ = "branch"

    # Primary Key
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, index=True),
    )

    # Branch Details
    name: str = Field(default=..., max_length=255, nullable=False, index=True)
    number: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            Identity(start=10001, always=False),
            unique=True,
            nullable=False,
        ),
    )

    # Branch Location Details
    address1: str | None = Field(default=None, max_length=500)
    address2: str | None = Field(default=None, max_length=500)
    city: str = Field(default=..., max_length=255, nullable=False, index=True)
    postal_code: str = Field(default=..., max_length=20, nullable=False)
    province: str = Field(default=..., max_length=255, nullable=False, index=True)
    country: str = Field(default=..., max_length=255, nullable=False, index=True)
    region: str | None = Field(default=None, max_length=255)

    latitude: float | None = Field(
        default=None,
        sa_column=Column(Numeric(precision=9, scale=6), nullable=True),
    )
    longitude: float | None = Field(
        default=None,
        sa_column=Column(Numeric(precision=9, scale=6), nullable=True),
    )

    join_key: int = Field(default=..., nullable=False, unique=True, index=True)

    # Branch Contact Details
    phone: str | None = Field(default=None, max_length=15)
    email: str | None = Field(default=None, max_length=255)
    website_url: str | None = Field(default=None, max_length=500)
    contact_person: str | None = Field(default=None, max_length=255)

    # Division & Line of Business Details
    division_name: str | None = Field(default=None, max_length=255)
    lob_name: str | None = Field(default=None, max_length=255)

    # Active Status
    is_active: bool = Field(default=True, nullable=False, index=True)

    # Audit Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Advanced Composite Indexes for Multi-tenant/Location Filtering
    __table_args__: tuple[Index, Index] = (
        Index("ix_branches_location_composite", "country", "province", "city"),
        Index("ix_branches_business_div", "lob_name", "division_name"),
    )

    def __repr__(self) -> str:
        return f"<Branch(id={self.id}, name={self.name!r}, number={self.number})>"
