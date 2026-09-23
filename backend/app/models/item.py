from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    pass


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(
        min_length=1,
        max_length=255,
        description="Name/title of the item.",
        schema_extra={"example": "Laptop"},
    )
    description: str | None = Field(
        default=None,
        max_length=255,
        description="Optional item description.",
        schema_extra={"example": "14-inch laptop with 16GB RAM"},
    )


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(SQLModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated item title.",
        schema_extra={"example": "Gaming Laptop"},
    )
    description: str | None = Field(
        default=None,
        max_length=255,
        description="Updated item description.",
        schema_extra={"example": "Updated specs for the new model"},
    )


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="Unique identifier for the item.",
        schema_extra={"example": "d95ea23b-34eb-44d8-bf7a-98f8d9fb7b33"},
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        description="Timestamp when the item was created.",
        schema_extra={"example": "2026-09-22T10:00:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
        description="Timestamp when the item was last updated. Empty until first update.",
        schema_extra={"example": "2026-09-23T10:00:00Z"},
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        ondelete="CASCADE",
        description="Identifier of the user who owns the item.",
        schema_extra={"example": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a"},
    )


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID = Field(
        description="Unique identifier for the item.",
        schema_extra={"example": "d95ea23b-34eb-44d8-bf7a-98f8d9fb7b33"},
    )
    owner_id: uuid.UUID = Field(
        description="Identifier of the user who owns the item.",
        schema_extra={"example": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a"},
    )
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when the item was created.",
        schema_extra={"example": "2026-09-22T10:00:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the item was last updated.",
        schema_extra={"example": "2026-09-23T10:00:00Z"},
    )


class ItemsPublic(SQLModel):
    data: list[ItemPublic] = Field(
        description="List of items returned by the API.",
        schema_extra={
            "example": [
                {
                    "id": "d95ea23b-34eb-44d8-bf7a-98f8d9fb7b33",
                    "title": "Laptop",
                    "description": "14-inch laptop with 16GB RAM",
                    "owner_id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                }
            ]
        },
    )
    count: int = Field(
        description="Total number of items in the result set.",
        schema_extra={"example": 1},
    )
