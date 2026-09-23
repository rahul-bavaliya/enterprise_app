# app/api/v1/schemas/branch.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BranchBase(BaseModel):
    name: str = Field(
        ...,
        max_length=255,
        description="Official registered name of the branch office.",
        examples=["Regina Central Hub"],
    )
    number: int | None = Field(
        None,
        description="Unique sequential branch identification number (auto-generated if omitted).",
        examples=[10001],
    )
    join_key: int = Field(
        ...,
        description="Unique legacy or relational join key used to map external ERP or CSV data.",
        examples=[501],
    )

    # Address Details
    address1: str | None = Field(
        None,
        max_length=500,
        description="Primary street address line of the branch location.",
        examples=["7 Cochran Dr"],
    )
    address2: str | None = Field(
        None,
        max_length=500,
        description="Secondary street address line (e.g., suite, unit, or floor number).",
        examples=["Second Floor, Suite 200"],
    )
    city: str = Field(
        ...,
        max_length=500,
        description="City where the branch is physically located.",
        examples=["Regina"],
    )
    postal_code: str = Field(
        ...,
        max_length=20,
        description="Postal code or ZIP code of the branch location.",
        examples=["S4N 0T9"],
    )
    province: str = Field(
        ...,
        max_length=255,
        description="Province, state, or territory where the branch is located.",
        examples=["Saskatchewan"],
    )
    country: str = Field(
        ...,
        max_length=255,
        description="Country where the branch operates.",
        examples=["Canada"],
    )

    # Geographic Coordinates
    latitude: float | None = Field(
        None,
        description="Geographic coordinate latitude for mapping and spatial queries.",
        examples=[50.445210],
    )
    longitude: float | None = Field(
        None,
        description="Geographic coordinate longitude for mapping and spatial queries.",
        examples=[-104.618894],
    )
    region: str | None = Field(
        None,
        max_length=255,
        description="Broader operational or administrative region name.",
        examples=["Western Region"],
    )

    # Contact Details
    phone: str | None = Field(
        None,
        max_length=15,
        description="Primary contact telephone number for the branch office.",
        examples=["+13065550199"],
    )
    email: EmailStr | None = Field(
        None,
        description="Official communication email address for the branch.",
        examples=["regina.central@example.com"],
    )
    website_url: str | None = Field(
        None,
        max_length=500,
        description="Web URL specific to this branch location.",
        examples=["https://branches.example.com/regina"],
    )
    contact_person: str | None = Field(
        None,
        max_length=255,
        description="Full name of the designated manager or primary contact person.",
        examples=["Jane Doe"],
    )

    # Division & Line of Business
    division_name: str | None = Field(
        None,
        max_length=255,
        description="Corporate division or business unit assigned to this branch.",
        examples=["Commercial Services Division"],
    )
    lob_name: str | None = Field(
        None,
        max_length=255,
        description="Associated Line of Business name.",
        examples=["Field Operations"],
    )

    is_active: bool = Field(
        True,
        description="Operational status flag indicating whether the branch is currently active.",
        examples=[True],
    )


class BranchCreate(BranchBase):
    """Schema for creating a new branch record."""

    pass


class BranchUpdate(BaseModel):
    """Schema for updating an existing branch record (all fields optional)."""

    name: str | None = Field(
        None,
        max_length=255,
        description="Updated branch name.",
        examples=["Regina North Hub"],
    )
    number: int | None = Field(
        None, description="Updated branch number.", examples=[10002]
    )
    join_key: int | None = Field(None, description="Updated join key.", examples=[502])
    address1: str | None = Field(
        None, max_length=500, description="Updated street address."
    )
    address2: str | None = Field(
        None, max_length=500, description="Updated suite/unit details."
    )
    city: str | None = Field(None, max_length=255, description="Updated city.")
    postal_code: str | None = Field(
        None, max_length=20, description="Updated postal code."
    )
    province: str | None = Field(
        None, max_length=255, description="Updated province/state."
    )
    country: str | None = Field(None, max_length=255, description="Updated country.")
    latitude: float | None = Field(None, description="Updated latitude.")
    longitude: float | None = Field(None, description="Updated longitude.")
    region: str | None = Field(None, max_length=255, description="Updated region.")
    phone: str | None = Field(None, max_length=15, description="Updated phone number.")
    email: EmailStr | None = Field(None, description="Updated email address.")
    website_url: str | None = Field(
        None, max_length=500, description="Updated website URL."
    )
    contact_person: str | None = Field(
        None, max_length=255, description="Updated contact person."
    )
    division_name: str | None = Field(
        None, max_length=255, description="Updated division name."
    )
    lob_name: str | None = Field(
        None, max_length=255, description="Updated line of business name."
    )
    is_active: bool | None = Field(None, description="Updated active status flag.")


class BranchResponse(BranchBase):
    """Schema for returning branch data with database identifiers and audit timestamps."""

    id: UUID = Field(
        ...,
        description="Unique database primary key (UUID v4).",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the branch record was created."
    )
    updated_at: datetime = Field(
        ..., description="Timestamp when the branch record was last updated."
    )

    model_config = ConfigDict(from_attributes=True)
