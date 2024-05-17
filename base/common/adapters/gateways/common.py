import abc
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import requests
import tenacity
from pydantic import AnyHttpUrl, BaseModel, ConfigDict
from tenacity import Retrying

from base.common.endpoints.api.api_exception_handlers import JsonApiErrors
from base.common.settings import HttpGatewaySettings
from base.common.utils.context import CallContext
from base.common.utils.logger import Logger


class GatewayErrors:
    @dataclass
    class BaseError(Exception):
        detail: str

    class NotValid(BaseError):
        pass

    class NotFound(BaseError):
        pass


class Gateway(abc.ABC):
    pass


class HttpGatewayConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: AnyHttpUrl
    correlation_id_header: str
    retry_attempts: int
    retry_sleep_time_seconds: float


class HttpGateway(abc.ABC):

    config: HttpGatewayConfig

    def __init__(self, config: HttpGatewaySettings, parent_logger: Logger):
        self.config = HttpGatewayConfig(**config.model_dump())
        self._retry_strategy = {
            "stop": tenacity.stop_after_attempt(self.config.retry_attempts),
            "wait": tenacity.wait_fixed(self.config.retry_sleep_time_seconds),
            "retry": tenacity.retry_if_exception_type(Exception),
            "reraise": True,
        }
        self.logger = parent_logger.child(self.__class__.__name__)

    def _call_api(
        self,
        method: Callable,
        url,
        auth_header: Dict = {},
        params=None,
        json=None,
        returned_raw=False,
    ):
        try:
            headers = auth_header.copy()
            headers.update(
                {self.config.correlation_id_header: CallContext.get_flow_correlation_id()}
            )
            response = self._retry_request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
            )
            response.raise_for_status()
            if returned_raw:
                return response
            return response.json()
        except requests.exceptions.HTTPError as err:
            resp_err = err.response.json()
            if set(resp_err.keys()) != {"errors"}:
                msg = f"unexpected error format: {resp_err}"
                raise GatewayErrors.BaseError(msg)
            msg = "; ".join(x.detail for x in JsonApiErrors(**err.response.json()).errors)
            if err.response.status_code == 404:
                raise GatewayErrors.NotFound(msg)
            if err.response.status_code == 422:
                raise GatewayErrors.NotValid(msg)
            raise GatewayErrors.BaseError(msg)
        except Exception as err:
            raise GatewayErrors.BaseError(f"Unknown error: {err}")

    def _retry(
        self,
        method: Callable,
        retry_if_result: Optional[Callable] = None,
        **kwargs,
    ):
        """Generic retry function that calls the given method with the given kwargs,
        and triggers a retry based on the following possibilities:
        - one of the exception conditions inside `retry_strategy` is met
        - the optional `retry_if_result` is injected as a function that accepts the method result
        and can raise error if some condition in the result is met"""

        for att in Retrying(**self._retry_strategy):
            with att:
                res = method(**kwargs)
                if retry_if_result:
                    retry_if_result(res)
                return res

    def _retry_request(self, method: Callable, url: str, json: Dict, **kwargs):
        def inner(res):
            if res.status_code >= 500:
                res.raise_for_status()

        return self._retry(
            method=method,
            retry_if_result=inner,
            url=url,
            json=json,
            **kwargs,
        )
