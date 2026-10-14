from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, *, headers: Optional[dict[str, str]] = None):
        super().__init__(message)
        self.message = message
        self.headers = headers


class ResourceNotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class DuplicateResourceError(AppError):
    status_code = 409
    code = "CONFLICT"


class InvalidFileError(AppError):
    status_code = 400
    code = "INVALID_FILE"


class FileTooLargeError(AppError):
    status_code = 413
    code = "FILE_TOO_LARGE"


class AiServiceError(AppError):
    status_code = 503
    code = "AI_SERVICE_UNAVAILABLE"


class RateLimitedError(AppError):
    status_code = 429
    code = "TOO_MANY_REQUESTS"


class OidcError(AppError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.oidc_code = code
        self.code = code.upper()
        self.status_code = 401 if code == "signup_expired" else 400


_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    413: "FILE_TOO_LARGE",
}


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    headers: Optional[dict[str, str]] = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": code,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "path": request.url.path,
        },
        headers=headers,
    )


def _validation_message(exc: RequestValidationError) -> str:
    parts: list[str] = []
    for error in exc.errors():
        location = [str(item) for item in error.get("loc", ()) if item not in ("body", "query", "path")]
        message = str(error.get("msg", "Invalid value")).removeprefix("Value error, ")
        parts.append(f"{'.'.join(location)}: {message}" if location else message)
    return "; ".join(parts) or "Invalid request"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if isinstance(exc, AiServiceError):
            logger.error("AI service error: %s", exc.message)
        elif isinstance(exc, OidcError):
            logger.warning("OIDC error [%s]: %s", exc.oidc_code, exc.message)
        return error_response(request, exc.status_code, exc.code, exc.message, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(request, 400, "VALIDATION_ERROR", _validation_message(exc))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(exc.status_code, "ERROR")
        return error_response(request, exc.status_code, code, str(exc.detail), getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception at %s", request.url.path, exc_info=exc)
        return error_response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred")
