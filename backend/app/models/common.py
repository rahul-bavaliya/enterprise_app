from typing import Generic, TypeVar

from sqlmodel import SQLModel

T = TypeVar("T")


class ResponseEnvelope(SQLModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str | None = None
