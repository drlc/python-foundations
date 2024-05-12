import abc
import inspect
from dataclasses import dataclass
from typing import Callable, List, Optional

from pydantic import BaseModel

from base.common.endpoints.direct.security.common import PassedAuthenticationBackend
from base.common.utils.logger import Logger


class DirectEndpointErrors:
    @dataclass
    class BaseError(Exception):
        detail: str

    class InvalidAccountIds(BaseError):
        pass


class GenericAdminEvent(BaseModel):
    payload: dict
    account_id: str


def get_all_endpoints(module, logger):
    endpoints = []

    for _, sub_module in inspect.getmembers(module):
        if inspect.ismodule(sub_module):
            members = dict(inspect.getmembers(sub_module))
            if "DirectEndpoint" in members:
                endpoints.append(
                    members["DirectEndpoint"](logger=logger.child(sub_module.__name__))
                )

    return endpoints


class DirectEndpoint(abc.ABC):
    logger: Logger

    def get_endpoints(self) -> List[Callable]:
        class_type = self.__class__
        method_list = [
            attribute
            for attribute in dir(class_type)
            if callable(getattr(class_type, attribute)) and attribute.startswith("__") is False
        ]
        all_routes = []
        for method_name in method_list:
            method = getattr(self, method_name)
            if method_name.startswith("route_") is True:
                all_routes.append(method())
        return all_routes


class DirectEndpointApp(abc.ABC):
    logger: Logger

    @classmethod
    def add_endpoints(
        cls, auth: Optional[PassedAuthenticationBackend], endpoints: List[DirectEndpoint]
    ):
        raise NotImplementedError()
