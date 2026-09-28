from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


class UserRole(StrEnum):
    """Operational role a user holds, which decides what they may do.

    ``ADMIN`` is the branch-wide manager, ``DISPATCHER`` raises and schedules
    work, and ``TECHNICIAN`` carries out and records work on the jobs assigned
    to them. Superusers bypass every role check.
    """

    ADMIN = "admin"
    DISPATCHER = "dispatcher"
    TECHNICIAN = "technician"


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
    role: UserRole = Field(
        default=UserRole.TECHNICIAN,
        sa_type=SAEnum(  # type: ignore
            UserRole,
            name="userrole",
            values_callable=lambda e: [m.value for m in e],
        ),
        description=(
            "Operational role. Admins manage their branch, dispatchers raise "
            "and schedule work, technicians carry out assigned work."
        ),
        schema_extra={"example": UserRole.TECHNICIAN},
    )
    branch_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="branch.id",
        index=True,
        nullable=True,
        ondelete="SET NULL",
        description=(
            "Branch the user belongs to. Admins and dispatchers may only act "
            "on work orders raised at this branch."
        ),
        schema_extra={"example": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d"},
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
    role: UserRole | None = Field(
        default=None,
        description="Updated operational role of the user.",
        schema_extra={"example": UserRole.DISPATCHER},
    )
    branch_id: uuid.UUID | None = Field(
        default=None,
        description="Updated branch the user belongs to.",
        schema_extra={"example": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d"},
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
