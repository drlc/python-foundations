from types import SimpleNamespace

from base.common.containers import CtnrApplication
from base.common.endpoints.api.api_endpoint import get_all_endpoints
from base.common.endpoints.api.create import create_app
from base.common.endpoints.api.utils.logging import LoggingMiddleware
from base.common.utils.logger import BasicLogger, Logger
from example_app.endpoints import api as api_module
from example_app.settings import ServiceSettings


def microservice_base():

    ctnr_application: CtnrApplication = CtnrApplication()
    ctnr_application.init(BasicLogger("root"), ServiceSettings())

    logger = ctnr_application.get(Logger)
    api = create_app(ctnr_application, get_all_endpoints(api_module), None, logger.child("web-api"))
    api.add_middleware(LoggingMiddleware, logger=logger.child("web-api"))
    return SimpleNamespace(api=api)


handlers = microservice_base()

asgi_app = handlers.api
