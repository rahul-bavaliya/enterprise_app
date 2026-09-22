import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class BranchBase(SQLModel):
    name: str = Field(index=True, min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class BranchCreate(BranchBase):
    pass


class BranchUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class Branch(BranchBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=lambda: datetime.now(),
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class BranchPublic(BranchBase):
    id: uuid.UUID
    created_at: datetime | None = None


class BranchesPublic(SQLModel):
    data: list[BranchPublic]
    count: int
