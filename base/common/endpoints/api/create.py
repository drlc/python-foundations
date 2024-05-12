from typing import List, Optional

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware

import base.common.endpoints.api.api_exception_handlers as api_ex_handlers
from base.common.adapters.stores.common import StoreErrors
from base.common.containers import CtnrApplication
from base.common.endpoints.api import add_healthcheck_api
from base.common.endpoints.api.api_endpoint import APIEndpoint
from base.common.endpoints.api.security import BearerAuthenticationBackend

# from base.src.endpoints.api.utils.logging import LoggingMiddleware
from base.common.settings import AppSettings
from base.common.usecases import UsecaseErrors
from base.common.utils.logger import Logger


def router(controllers: List[APIEndpoint]):
    routes = []
    for controller in controllers:
        routes.extend(controller.get_endpoints())
    return APIRouter(routes=routes)


def create_app(
    container: CtnrApplication,
    endpoints: List[APIEndpoint],
    auth: Optional[BearerAuthenticationBackend],
    logger: Logger,
):
    config: AppSettings = container.get(AppSettings)
    further_prefix = config.api.further_prefix or ""
    app = FastAPI(
        version=config.app.version,
        title=config.app.name,
        root_path=config.api.root_path or "",
        docs_url=further_prefix + "/docs",
        redoc_url=further_prefix + "/redoc",
        openapi_url=further_prefix + "/openapi.json",
    )
    # middleware registration order is important, the last one added is the first one evaluated
    if auth is not None:
        app.add_middleware(
            AuthenticationMiddleware,
            backend=auth,
            on_error=api_ex_handlers.auth_exception_handler,
        )
    # app.add_middleware(LoggingMiddleware, logger=config.logger)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=config.api.cors_allow_origin_regex,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_version_prefix = further_prefix + "/api/v" + config.api.version
    add_healthcheck_api(app, further_prefix, config.app.version)
    app.include_router(router(controllers=endpoints), prefix=api_version_prefix)

    app.add_exception_handler(
        UsecaseErrors.BaseError, api_ex_handlers.usecase_exception_handler(logger)
    )
    app.add_exception_handler(
        StoreErrors.BaseError, api_ex_handlers.store_exception_handler(logger)
    )
    app.add_exception_handler(StarletteHTTPException, api_ex_handlers.http_exception_handler)
    app.add_exception_handler(
        RequestValidationError, api_ex_handlers.request_validation_exception_handler
    )
    app.add_exception_handler(Exception, api_ex_handlers.unhandled_error_exception_handler(logger))

    return app
