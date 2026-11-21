"""Consistent error responses: {"error": {"code": ..., "message": ..., "details": ...}}.
Unexpected errors are logged server-side and never expose internals to the client."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

log = logging.getLogger("app.errors")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: object = None):
        self.status_code, self.code, self.message, self.details = (
            status_code,
            code,
            message,
            details,
        )


def not_found(entity: str) -> AppError:
    return AppError(404, "not_found", f"{entity} not found.")


def bad_request(message: str, code: str = "invalid_request") -> AppError:
    return AppError(400, code, message)


def conflict(message: str, code: str = "conflict") -> AppError:
    return AppError(409, code, message)


def _body(code: str, message: str, details: object = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code, content=_body(exc.code, exc.message, exc.details)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [
            {
                "field": ".".join(str(p) for p in e.get("loc", []) if p != "body"),
                "message": str(e.get("msg", "")).removeprefix("Value error, "),
            }
            for e in exc.errors()
        ]
        message = details[0]["message"] if len(details) == 1 else "Some fields are invalid."
        return JSONResponse(status_code=422, content=_body("validation_error", message, details))

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, exc: IntegrityError):
        log.warning("Integrity error: %s", exc.orig)
        return JSONResponse(
            status_code=409,
            content=_body("integrity_error", "The change conflicts with existing data."),
        )

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        log.exception("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500, content=_body("internal_error", "An unexpected error occurred.")
        )
