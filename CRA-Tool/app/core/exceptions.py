"""
Application exceptions and centralized handlers.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.responses import ErrorDetail, ErrorResponse
from app.utils.logger import logger


class AppException(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "APP_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details
        super().__init__(message)


class TenantAccessException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    code = "TENANT_ACCESS_DENIED"


class AuthException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "AUTH_ERROR"


class BusinessLogicException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "BUSINESS_RULE_FAILED"


class DeploymentValidationError(BusinessLogicException):
    code = "DEPLOYMENT_VALIDATION_ERROR"


class DatabaseException(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "DATABASE_ERROR"


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | list[Any] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details),
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning("Application exception: %s request_id=%s", exc.code, _request_id(request))
    return _error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return _error_response(
        request=request,
        status_code=exc.status_code,
        code="HTTP_ERROR",
        message=str(exc.detail),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=exc.errors(),
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database exception request_id=%s", _request_id(request))
    return _error_response(
        request=request,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="DATABASE_ERROR",
        message="Database operation failed",
        details={"sqlalchemy_error": exc.__class__.__name__},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception request_id=%s", _request_id(request))
    return _error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="Internal server error",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
