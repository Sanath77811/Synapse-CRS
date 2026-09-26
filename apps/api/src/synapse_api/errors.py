"""Structured HTTP errors. Responses omit exception text and credentials."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("synapse.api")


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def _validation_details(exc: RequestValidationError) -> dict[str, Any]:
    cleaned: list[dict[str, Any]] = []
    for item in exc.errors():
        loc = item.get("loc", [])
        loc_text = [str(part).lower() for part in loc]
        if "authorization" in loc_text:
            continue
        cleaned.append(
            {
                "loc": [str(part) for part in loc],
                "msg": str(item.get("msg", "invalid")),
                "type": str(item.get("type", "value_error")),
            }
        )
    return {"errors": cleaned}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(
                "invalid_request",
                "Request failed validation.",
                _validation_details(exc),
            ),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body("http_error", message),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("request failed error_type=%s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "The request could not be completed."),
        )
