import logging

from fastapi.responses import JSONResponse

from .exceptions import APIError

logger = logging.getLogger("pii_washer")


def _error_body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def key_error_response(exc: KeyError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=_error_body("NOT_FOUND", str(exc).strip("'")),
    )


def value_error_response(exc: ValueError) -> JSONResponse:
    # APIError subclasses carry their own status + code. Any other ValueError
    # is a plain validation failure (422 VALIDATION_ERROR).
    if isinstance(exc, APIError):
        return JSONResponse(
            status_code=exc.http_status,
            content=_error_body(exc.error_code, str(exc)),
        )
    return JSONResponse(
        status_code=422,
        content=_error_body("VALIDATION_ERROR", str(exc)),
    )


def runtime_error_response(exc: RuntimeError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=_error_body("ENGINE_UNAVAILABLE", str(exc)),
    )


def server_error_response(exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=_error_body("SERVER_ERROR", "An unexpected error occurred"),
    )
