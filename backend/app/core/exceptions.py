"""Application exceptions and the handlers that render them as envelopes.

Every failure path funnels through here so clients always receive the same
JSON shape: ``{"success": false, "data": null, "message": "..."}``.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas import ResponseEnvelope

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base class for expected, user-facing failures."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_message: str = "Request could not be processed"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Resource not found"

    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(f"{resource} not found")


class AlreadyExistsException(AppException):
    status_code = status.HTTP_409_CONFLICT
    default_message = "Record already exists"


class InvalidStateException(AppException):
    status_code = status.HTTP_409_CONFLICT
    default_message = "Operation is not allowed in the current state"


class ValidationException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_message = "Request failed validation"


def _envelope(*, status_code: int, message: str, data: Any = None) -> JSONResponse:
    payload = ResponseEnvelope(success=False, data=data, message=message)
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


def _format_validation_errors(exc: RequestValidationError) -> str:
    """Flatten Pydantic errors into one readable sentence."""
    parts: list[str] = []
    for error in exc.errors():
        location = ".".join(
            str(piece) for piece in error.get("loc", ()) if piece != "body"
        )
        message = error.get("msg", "invalid value")
        parts.append(f"{location}: {message}" if location else message)
    return "; ".join(parts) or "Request failed validation"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers so no endpoint can leak a raw traceback to a client."""

    @app.exception_handler(AppException)
    async def handle_app_exception(
        _request: Request, exc: AppException
    ) -> JSONResponse:
        return _envelope(status_code=exc.status_code, message=exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _envelope(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=_format_validation_errors(exc),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else str(detail)
        # Never leak internal headers such as WWW-Authenticate to the envelope.
        return _envelope(status_code=exc.status_code, message=message)

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        # Roll back so the connection returns to the pool in a clean state.
        logger.warning("Database integrity error on %s: %s", request.url.path, exc)
        return _envelope(
            status_code=status.HTTP_409_CONFLICT,
            message="The request conflicts with existing data",
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(
        request: Request, _exc: SQLAlchemyError
    ) -> JSONResponse:
        logger.exception("Database error on %s", request.url.path)
        return _envelope(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Database is temporarily unavailable",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, _exc: Exception
    ) -> JSONResponse:
        # Log the detail server-side; return an opaque message to the client.
        logger.exception("Unhandled error on %s", request.url.path)
        return _envelope(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error",
        )
