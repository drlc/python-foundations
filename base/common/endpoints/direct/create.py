from typing import Any, List, Optional, Type

from base.common.containers import CtnrApplication
from base.common.endpoints.direct.direct_endpoint import DirectEndpoint, DirectEndpointApp
from base.common.endpoints.direct.security.common import PassedAuthenticationBackend
from base.common.utils.logger import Logger


def create_app(
    app_type: Type[DirectEndpointApp],
    container: CtnrApplication,
    endpoint_module: Any,
    endpoints: List[DirectEndpoint],
    auth: Optional[PassedAuthenticationBackend],
    logger: Logger,
):

    app_type.add_endpoints(endpoints=endpoints, auth=auth)
    app = app_type(logger=logger)
    container.wire(modules=[endpoint_module])
    return app
