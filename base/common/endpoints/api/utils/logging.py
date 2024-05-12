from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from base.common.endpoints.api.utils.timer import TimingStats


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        with TimingStats() as timer:
            response = await call_next(request)

        req = {
            "method": request.method,
            "url": str(request.url),
            "client": f"{request.client.host}:{request.client.port}",
        }
        resp = {"status_code": response.status_code}

        self.logger.info(
            "Request & Response", request=req, response=resp, timing=timer.get_results()
        )
        return response
