from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    DB_ERROR = "DB_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetail(BaseModel):
    code: ErrorCode | str = Field(
        ...,
        description="Machine-readable error code",
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    details: Any | None = Field(
        default=None,
        description="Additional error information",
    )


class ResponseEnvelope(BaseModel, Generic[T]):
    success: bool = Field(...)
    message: str = Field(...)
    data: T | None = Field(default=None)
    error: ErrorDetail | None = Field(default=None)

    @classmethod
    def ok(
        cls,
        data: T,
        message: str = "Success",
    ) -> ResponseEnvelope[T]:
        """Create a successful response envelope."""
        return cls(
            success=True,
            message=message,
            data=data,
            error=None,
        )

    @classmethod
    def fail(
        cls,
        message: str,
        code: ErrorCode | str = ErrorCode.INTERNAL_ERROR,
        details: Any | None = None,
        error: ErrorDetail | dict | Any | None = None,
    ) -> ResponseEnvelope[None]:
        """
        Create a failure response envelope.
        Flexibly accepts either individual `code`/`details` arguments
        or an explicit `error` dictionary/object to prevent TypeErrors.
        """
        if error is not None:
            if isinstance(error, ErrorDetail):
                err_obj = error
            elif isinstance(error, dict):
                err_obj = ErrorDetail(
                    code=error.get("code", code),
                    message=error.get("message", message),
                    details=error.get("details", details),
                )
            else:
                err_obj = ErrorDetail(
                    code=code,
                    message=message,
                    details=str(error),
                )
        else:
            err_obj = ErrorDetail(
                code=code,
                message=message,
                details=details,
            )

        return cls(
            success=False,
            message=message,
            data=None,
            error=err_obj,
        )
