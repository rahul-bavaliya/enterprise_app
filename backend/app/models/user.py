from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    pass


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(
        unique=True,
        index=True,
        max_length=255,
        description="Unique email address used for sign-in and account recovery.",
        schema_extra={"example": "john.doe@example.com"},
    )
    is_active: bool = Field(
        default=True,
        description="Whether this user account is currently active.",
        schema_extra={"example": True},
    )
    is_superuser: bool = Field(
        default=False,
        description="Whether this user has administrator privileges.",
        schema_extra={"example": False},
    )
    full_name: str | None = Field(
        default=None,
        max_length=255,
        description="Display name of the user.",
        schema_extra={"example": "John Doe"},
    )


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Plain-text password for the account. It will be hashed before storage.",
        schema_extra={"example": "StrongPass!123"},
    )


class UserRegister(SQLModel):
    email: EmailStr = Field(
        max_length=255,
        description="User email to register with.",
        schema_extra={"example": "new.user@example.com"},
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password used to create the account.",
        schema_extra={"example": "SecureP@ss456"},
    )
    full_name: str | None = Field(
        default=None,
        max_length=255,
        description="Optional display name for the new account.",
        schema_extra={"example": "New User"},
    )


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(
        default=None,
        max_length=255,
        description="Updated email address for the user.",
        schema_extra={"example": "updated.email@example.com"},
    )
    is_active: bool | None = Field(
        default=None,
        description="Set whether the account should be active.",
        schema_extra={"example": True},
    )
    is_superuser: bool | None = Field(
        default=None,
        description="Toggle administrator permissions for the user.",
        schema_extra={"example": False},
    )
    full_name: str | None = Field(
        default=None,
        max_length=255,
        description="Updated display name for the user.",
        schema_extra={"example": "Jane Doe"},
    )
    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="New password to set for the user.",
        schema_extra={"example": "AnotherStrongPass!456"},
    )


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(
        default=None,
        max_length=255,
        description="Updated profile name for the authenticated user.",
        schema_extra={"example": "Jane Smith"},
    )
    email: EmailStr | None = Field(
        default=None,
        max_length=255,
        description="Updated account email for the authenticated user.",
        schema_extra={"example": "jane.smith@example.com"},
    )


class UpdatePassword(SQLModel):
    current_password: str = Field(
        min_length=8,
        max_length=128,
        description="Current password to verify the user identity.",
        schema_extra={"example": "OldPass!123"},
    )
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="New password to store for the user.",
        schema_extra={"example": "NewStrongPass!456"},
    )


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="Unique identifier for the user.",
        schema_extra={"example": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a"},
    )
    hashed_password: str = Field(
        description="Hashed password stored in the database.",
        schema_extra={"example": "$argon2id$..."},
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        description="Timestamp when the user record was created.",
        schema_extra={"example": "2026-09-22T10:00:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
        description="Timestamp when the user record was last updated. Empty until first update.",
        schema_extra={"example": "2026-09-23T10:00:00Z"},
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID = Field(
        description="Unique identifier for the user.",
        schema_extra={"example": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a"},
    )
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when the user record was created.",
        schema_extra={"example": "2026-09-22T10:00:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the user record was last updated.",
        schema_extra={"example": "2026-09-23T10:00:00Z"},
    )


class UsersPublic(SQLModel):
    data: list[UserPublic] = Field(
        description="List of users returned by the API.",
        schema_extra={
            "example": [
                {
                    "id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a",
                    "email": "john.doe@example.com",
                    "full_name": "John Doe",
                    "is_active": True,
                    "is_superuser": False,
                }
            ]
        },
    )
    count: int = Field(
        description="Total number of users in the result set.",
        schema_extra={"example": 1},
    )
