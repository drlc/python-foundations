from datetime import date, datetime, time
from typing import List, Optional

from pydantic.dataclasses import dataclass
from pymongo import MongoClient, ReadPreference, WriteConcern
from pymongo.client_session import ClientSession as PyMongoClientSession
from pymongo.database import Database as MnCursor
from pymongo.read_concern import ReadConcern
from tenacity import Retrying, stop_after_delay, wait_random_exponential
from ulid import microsecond as ulid

from base.common.adapters.stores import Repository, StoreConnection, StoreCursor, StoreErrors
from base.common.adapters.stores.common import StoreConfig
from base.common.settings import MongoConnectionSettings
from base.common.utils.logger import Logger


def mn_json(v):
    if isinstance(v, time):
        return datetime.combine(datetime.min, v)
    if isinstance(v, date) and not isinstance(v, datetime):
        return datetime.combine(v, time.min)
    elif isinstance(v, dict):
        return {k: mn_json(v) for k, v in v.items()}
    elif isinstance(v, List):
        return [mn_json(v) for v in v]
    return v


class MongoCursor(StoreCursor):
    cursor: MnCursor


@dataclass
class MongoConnectionConfig(StoreConfig):
    uri_strings: str
    database: str
    retry_max_timeout_seconds: int
    retry_max_total_delay_seconds: int


class MongoConnection(StoreConnection[MongoClient, PyMongoClientSession]):
    config: MongoConnectionConfig

    def __init__(self, config: MongoConnectionSettings, parent_logger: Logger):
        self.config = MongoConnectionConfig(**config)
        self.logger = parent_logger.child("mongo")

    def connect(self):
        retry_strat = {
            "wait": wait_random_exponential(
                multiplier=0.5, min=0.5, max=self.config.retry_max_total_delay_seconds
            ),
            "stop": stop_after_delay(max_delay=self.config.retry_max_timeout_seconds),
            "reraise": True,
        }
        try:
            for att in Retrying(**retry_strat):
                with att:
                    return MongoClient(self.config.uri_strings)
        except Exception as err:
            msg = f"MongoConnection: unable to establish connection. {str(err)}"
            raise StoreErrors.Connection(msg)

    def is_connected(self, connection: MongoClient) -> bool:
        if connection is None:
            return False
        try:
            connection.server_info()
        except Exception:
            return False
        return True

    def create_session(self, connection: MongoClient) -> PyMongoClientSession:
        session = connection.start_session()
        session.start_transaction(
            read_concern=ReadConcern("snapshot"),
            write_concern=WriteConcern(w="majority"),
            read_preference=ReadPreference.PRIMARY,
        )
        return session

    def rollback_session(self, session: PyMongoClientSession):
        session.abort_transaction()

    def commit_session(self, session: PyMongoClientSession):
        session.commit_transaction()

    def close_session(self, session: PyMongoClientSession):
        session.end_session()

    def create_cursor(self, session: PyMongoClientSession) -> MongoCursor:
        return MongoCursor(cursor=session.client.get_database(self.config.database))


class MongoRepo(Repository):
    def _create_id(self):
        return str(ulid.new())

    def _utcnow(self):
        return datetime.utcnow()

    def _insert(
        self, curs: MongoCursor, collection_name: str, item: dict, new_id: Optional[str] = None
    ) -> dict:
        ser = {k: mn_json(v) for k, v in item.items() if k not in ["id"]}
        ser["_id"] = new_id or self._create_id()
        ser["created_at"] = ser["updated_at"] = self._utcnow()
        curs.cursor[collection_name].insert_one(ser)
        ser["id"] = ser["_id"]
        return ser

    def _find_one(
        self,
        curs: MongoCursor,
        collection_name: str,
        query: dict,
        sort: list = None,
    ) -> dict:
        if sort is None:
            sort = []
        res = curs.cursor[collection_name].find_one(query, sort=sort)
        if not res:
            msg = f"element not found for query={query}"
            raise StoreErrors.NotFound(msg)

        res["id"] = res["_id"]
        return res

    def _update_one(
        self,
        curs: MongoCursor,
        collection_name: str,
        supported_attributes: List[str],
        query: dict,
        **kwargs,
    ):
        if not (updates := {k: kwargs[k] for k in supported_attributes if k in kwargs}):
            raise StoreErrors.BaseError("at least one field to update must be passed")
        updates["updated_at"] = self._utcnow()
        ser = {k: mn_json(v) for k, v in updates.items()}
        res = curs.cursor[collection_name].update_one(filter=query, update={"$set": ser})
        if not res or res.matched_count != 1:
            msg = f"element not found for query={query}"
            raise StoreErrors.NotFound(msg)
        return updates

    def _update_one_list(
        self,
        curs: MongoCursor,
        collection_name: str,
        supported_attributes: List[str],
        query: dict,
        **kwargs,
    ):
        if not (updates := {k: kwargs[k] for k in supported_attributes if k in kwargs}):
            raise StoreErrors.BaseError("at least one field to update must be passed")
        update_date = self._utcnow()
        further_updates = {"updated_at": update_date}
        ser = {k: mn_json(v) for k, v in updates.items()}
        res = curs.cursor[collection_name].update_one(
            filter=query, update={"$set": further_updates, **ser}
        )
        if not res or res.matched_count != 1:
            msg = f"element not found for query={query}"
            raise StoreErrors.NotFound(msg)
        return update_date
