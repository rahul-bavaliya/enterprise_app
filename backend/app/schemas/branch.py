import uuid
from datetime import datetime

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class BranchBase(SQLModel):
    name: str = Field(
        index=True,
        min_length=1,
        max_length=255,
        description="Branch name or office label.",
        schema_extra={"example": "Main Branch"},
    )
    location: str | None = Field(
        default=None,
        max_length=255,
        description="Physical location or address of the branch.",
        schema_extra={"example": "New York, NY"},
    )
    is_active: bool = Field(
        default=True,
        description="Whether the branch is currently active and available.",
        schema_extra={"example": True},
    )


class BranchCreate(BranchBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Main Branch",
                "location": "New York, NY",
                "is_active": True,
            }
        }
    )


class BranchUpdate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Downtown Branch",
                "location": "Los Angeles, CA",
                "is_active": False,
            }
        }
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated branch name.",
        schema_extra={"example": "Downtown Branch"},
    )
    location: str | None = Field(
        default=None,
        max_length=255,
        description="Updated branch location.",
        schema_extra={"example": "Los Angeles, CA"},
    )
    is_active: bool | None = Field(
        default=None,
        description="Updated active status for the branch.",
        schema_extra={"example": False},
    )


class BranchPublic(BranchBase):
    id: uuid.UUID = Field(
        description="Unique identifier for the branch.",
        schema_extra={"example": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d"},
    )
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when the branch record was created.",
        schema_extra={"example": "2026-09-22T10:00:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the branch record was last updated.",
        schema_extra={"example": "2026-09-23T10:00:00Z"},
    )


class BranchesPublic(SQLModel):
    data: list[BranchPublic] = Field(
        description="List of branches returned by the API.",
        schema_extra={
            "example": [
                {
                    "id": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d",
                    "name": "Main Branch",
                    "location": "New York, NY",
                    "is_active": True,
                }
            ]
        },
    )
    count: int = Field(
        description="Total number of branches in the result set.",
        schema_extra={"example": 1},
    )
