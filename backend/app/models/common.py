from typing import Generic, TypeVar

from sqlmodel import Field, SQLModel

T = TypeVar("T")


class ResponseEnvelope(SQLModel, Generic[T]):
    success: bool = Field(
        default=True,
        description="Whether the request completed successfully.",
        schema_extra={"example": True},
    )
    data: T | None = Field(
        default=None,
        description="Payload returned by the endpoint when the request succeeds.",
        schema_extra={"example": {"id": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a"}},
    )
    message: str | None = Field(
        default=None,
        description="Optional human-readable status message associated with the response.",
        schema_extra={"example": "Branch created successfully"},
    )
