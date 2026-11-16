from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_JSON = "application/problem+json"

# Which spec code goes with each status the service can return.
CODE_BY_STATUS = {
    400: "VALIDATION",
    404: "NOT_FOUND",
    405: "VALIDATION",
    422: "VALIDATION",
    503: "UNAVAILABLE",
}


def problem_response(
    status: int, detail: str, code: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": HTTPStatus(status).phrase,
        "status": status,
        "detail": detail,
        "code": code,
    }
    return JSONResponse(body, status_code=status, headers=headers, media_type=PROBLEM_JSON)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = CODE_BY_STATUS.get(exc.status_code)
    if code is None:
        # Not a status the spec uses. FastAPI's default response applies.
        from fastapi.exception_handlers import http_exception_handler as default_handler

        return await default_handler(request, exc)
    return problem_response(exc.status_code, str(exc.detail), code, exc.headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0]
    field = ".".join(str(part) for part in first["loc"])
    return problem_response(422, f"{field}: {first['msg']}", "VALIDATION")


def add_error_handlers(app: FastAPI) -> None:
    # FastAPI's HTTPException subclasses Starlette's, so one handler covers both.
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
