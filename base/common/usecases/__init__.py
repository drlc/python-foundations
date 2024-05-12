import abc
import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Type

from pydantic import BaseModel, ConfigDict

from base.common.adapters.stores.common import StoreConnection
from base.common.endpoints.security import ADMIN_GROUP
from base.common.utils.context import CallContext
from base.common.utils.logger import Logger


class BaseDTO(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UsecaseErrors:
    @dataclass
    class BaseError(Exception):
        detail: str

    class Forbidden(BaseError):
        pass

    class AlreadyExists(BaseError):
        pass

    class NotValidRequest(BaseError):
        pass


class WithStoreConnection(abc.ABC):
    conn: StoreConnection
    logger: Logger

    @staticmethod
    def is_admin() -> bool:
        return ADMIN_GROUP in CallContext.get_authenticated_user().groups

    @staticmethod
    def with_cursor(func):
        def inner(*args, **kwargs):
            self: WithStoreConnection = args[0]
            self.logger.info("starting usecase", req=kwargs.get("req"))
            if kwargs.get("curs"):
                res = func(*args, **kwargs)
            with self.conn.cursor() as curs:
                res = func(*args, **kwargs, curs=curs)
            self.logger.info("usecase finished")
            return res

        return inner


UsecaseResult = Any
PaginationCursor = str


class UsecaseReq(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class UsecaseListReq(UsecaseReq):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    iden_lt: Optional[str] = None
    iden_gt: Optional[str] = None
    cursor: Optional[PaginationCursor] = None


class Usecase(WithStoreConnection):
    """Base skeleton for use cases."""

    def __init__(self, parent_logger: Logger, conn: Optional[StoreConnection]):
        self.logger = parent_logger.child(f"usecase.{self.__module__.split('.')[-1]}")
        self.conn = conn

    def execute(self, req: UsecaseReq, **kwargs) -> UsecaseResult:
        raise NotImplementedError("execute not implemented by usecase class")  # pragma: no cover


class Pagination(BaseModel):
    after_cursor: Optional[PaginationCursor] = None
    has_more: bool = False

    @staticmethod
    def create_cursor(obj: UsecaseListReq) -> PaginationCursor:
        return base64.b64encode(
            json.dumps(obj.json(exclude_none=True, exclude={"cursor"})).encode("utf-8")
        ).decode("utf-8")

    @staticmethod
    def parse_cursor(cur: PaginationCursor, model: Type[UsecaseListReq]) -> BaseModel:
        string_bytes = base64.b64decode(cur.encode("utf-8"))
        return model.parse_raw(json.loads(string_bytes.decode("utf-8")))
