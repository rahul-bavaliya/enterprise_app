from typing import Generic, TypeVar

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel

T = TypeVar("T")


class ResponseEnvelope(SQLModel, Generic[T]):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {
                    "id": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d",
                    "name": "Main Branch",
                    "location": "New York, NY",
                    "is_active": True,
                },
                "message": "Branch created successfully",
            }
        }
    )

    success: bool = Field(
        default=True,
        description="Whether the request completed successfully.",
        schema_extra={"example": True},
    )
    data: T | None = Field(
        default=None,
        description="Payload returned by the endpoint when the request succeeds.",
        schema_extra={
            "example": {
                "id": "f24bf9d7-c4a1-4448-b895-3ad5f9d3bb4d",
                "name": "Main Branch",
                "location": "New York, NY",
                "is_active": True,
            }
        },
    )
    message: str | None = Field(
        default=None,
        description="Optional human-readable status message associated with the response.",
        schema_extra={"example": "Branch created successfully"},
    )
