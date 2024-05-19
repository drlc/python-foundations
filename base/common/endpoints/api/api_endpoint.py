import abc
from typing import Generic, List, Optional, TypeVar

from fastapi.routing import APIRoute
from pydantic import BaseModel

from base.common.endpoints import get_all_by_class
from base.common.usecases import Pagination

D = TypeVar("D")


def get_all_endpoints(module):
    return get_all_by_class(module, "APIEndpoint")


class HTTPResponseWrapper(BaseModel, Generic[D]):
    data: Optional[D]
    pagination: Optional[Pagination] = None


class APIEndpoint(abc.ABC):
    def get_endpoints(self) -> List[APIRoute]:
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
