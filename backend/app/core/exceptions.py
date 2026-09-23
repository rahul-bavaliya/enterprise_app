from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.response import ResponseEnvelope


class AppException(Exception):
    def __init__(
        self, message: str, status_code: int = 400, error_code: str = "BAD_REQUEST"
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
        )


class ExistingRecordException(AppException):
    def __init__(self, message: str = "Record already exists"):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="EXISTING_RECORD",
        )


class NotActiveException(AppException):
    def __init__(self, message: str = "Resource is not active"):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="NOT_ACTIVE",
        )


class DatabaseException(AppException):
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DB_ERROR",
        )


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ResponseEnvelope.fail(
                message=exc.message, error={"code": exc.error_code}
            ).model_dump(),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        # Log the error for internal debugging (optional)
        # Here we return a generic database error to avoid leaking details
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseEnvelope.fail(
                message="Database operation failed",
                error={"code": "DB_ERROR", "details": str(exc)},
            ).model_dump(),
        )
