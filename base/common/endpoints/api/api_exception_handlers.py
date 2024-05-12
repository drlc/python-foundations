import http
from typing import Dict, List, Optional

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.authentication import AuthenticationError

from base.common.adapters.stores.common import StoreErrors
from base.common.usecases import UsecaseErrors
from base.common.utils.logger import Logger


class JsonApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[int] = Field(None, description="HTTP status code.")
    title: Optional[str] = Field(
        None,
        description="Short, human-readable summary of the problem type.",
    )
    detail: Optional[str] = Field(
        None,
        description="Human-readable explanation specific to the problem.",
    )
    code: Optional[str] = Field(None, description="Application-specific error code.")


class JsonApiErrors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    errors: List[JsonApiError]


def format_error_response(
    status: int, message: Optional[str] = None, code: Optional[str | int] = None
) -> Dict:
    error = JsonApiError(
        status=status, title=http.HTTPStatus(status).phrase, detail=message, code=str(code)
    )
    return JsonApiErrors(errors=[error]).model_dump()


async def http_exception_handler(request, exc):
    status_code = exc.status_code or 500
    error_message = exc.detail or str(exc)
    error_content = format_error_response(status=status_code, message=error_message)
    return JSONResponse(content=jsonable_encoder(error_content), status_code=status_code)


def auth_exception_handler(request, exc: AuthenticationError):
    status_code = 401
    error_message = str(exc.args[0])
    error_content = format_error_response(status=status_code, message=error_message)
    return JSONResponse(content=jsonable_encoder(error_content), status_code=status_code)


async def request_validation_exception_handler(request, exc):
    status_code = 422
    try:
        error_message = "; ".join(
            [err["msg"] + " :" + str(err["loc"])[1:-1] for err in exc.errors()]
        )
    except (AttributeError, IndexError):
        error_message = None
    error_message = error_message or "Request validation error"
    error_content = format_error_response(status=status_code, message=error_message)
    return JSONResponse(content=jsonable_encoder(error_content), status_code=status_code)


def unhandled_error_exception_handler(logger: Logger):
    async def handler(request, exc):
        logger.error(f"Unhandled exception: {exc}")
        status_code = 500
        error_content = format_error_response(status=status_code, message="Something went wrong")
        return JSONResponse(content=jsonable_encoder(error_content), status_code=status_code)

    return handler


def store_exception_handler(logger: Logger):
    async def handler(request, exc: StoreErrors.BaseError):
        status_code = 500
        if isinstance(exc, StoreErrors.ForeignKeyViolation):
            status_code = 422
        if isinstance(exc, StoreErrors.DuplicateKey):
            status_code = 409
        if isinstance(exc, StoreErrors.NotFound):
            status_code = 404
        logger.error(f"Store exception: {exc}")
        error_message = exc.detail
        error_content = format_error_response(status=status_code, message=error_message)
        return JSONResponse(content=jsonable_encoder(error_content), status_code=status_code)

    return handler


def usecase_exception_handler(logger: Logger):
    async def handler(request, exc: UsecaseErrors.BaseError):
        status_code = 400
        if isinstance(exc, UsecaseErrors.Forbidden):
            status_code = 403
        if isinstance(exc, UsecaseErrors.AlreadyExists):
            status_code = 409
        logger.error(f"Usecase exception: {exc}")
        error_message = exc.detail
        error_content = format_error_response(status=status_code, message=error_message)
        return JSONResponse(content=jsonable_encoder(error_content), status_code=status_code)

    return handler
