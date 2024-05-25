import abc
import sys
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

from base.common.settings import StoreConnectionSettings
from base.common.utils.logger import Logger

SORT_DIRECTION = Literal["ASC", "DESC"]


class StoreErrors:
    @dataclass
    class BaseError(Exception):
        detail: str

    class DuplicateKey(BaseError):
        pass

    class Connection(BaseError):
        pass

    class NotFound(BaseError):
        pass

    class ForeignKeyViolation(BaseError):
        pass


C = TypeVar("C")
S = TypeVar("S")


class StoreCursor(BaseModel, abc.ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    cursor: Any


class StoreConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    class_name: str


class StoreConnection(Generic[C, S]):
    logger: Logger
    config: StoreConfig
    connection: Optional[C] = None

    @abc.abstractmethod
    def connect(self) -> C:
        raise NotImplementedError()  # pragma: no cover

    @abc.abstractmethod
    def is_connected(self, connection: C) -> bool:
        raise NotImplementedError()  # pragma: no cover

    @abc.abstractmethod
    def create_session(self, connection: C, autocommit: bool) -> S:
        raise NotImplementedError()  # pragma: no cover

    @abc.abstractmethod
    def rollback_session(self, session: S):
        raise NotImplementedError()  # pragma: no cover

    @abc.abstractmethod
    def commit_session(self, session: S):
        raise NotImplementedError()  # pragma: no cover

    @abc.abstractmethod
    def close_session(self, session: S):
        raise NotImplementedError()  # pragma: no cover

    @abc.abstractmethod
    def create_cursor(self, session: S) -> StoreCursor:
        raise NotImplementedError()  # pragma: no cover

    @contextmanager
    def cursor(
        self, autocommit: bool = False
    ) -> Callable[..., AbstractContextManager[StoreCursor]]:
        active_connection = self.connection
        if not self.is_connected(active_connection):
            active_connection = self.connect()
            self.connection = active_connection
        session = None
        try:
            session = self.create_session(active_connection, autocommit)
            yield self.create_cursor(session)
        except Exception as err:
            self.logger.error(f"StoreConnection: {str(err)}")
            self.rollback_session(session) if not autocommit else None
            raise err
        else:
            self.commit_session(session) if not autocommit else None
        finally:
            if session:
                self.close_session(session)


class Repository(abc.ABC):
    pass


def get_db_instance(config: StoreConnectionSettings, parent_logger: Logger):
    settings_class_name = config.class_name_settings.split(".")[-1]
    settings_class_name_module = ".".join(config.class_name_settings.split(".")[:-1])
    settings_clz = getattr(sys.modules[settings_class_name_module], settings_class_name)
    settings = settings_clz()

    class_name = config.class_name.split(".")[-1]
    class_name_module = ".".join(config.class_name.split(".")[:-1])
    clz = getattr(sys.modules[class_name_module], class_name)

    return clz(config=settings, parent_logger=parent_logger)
