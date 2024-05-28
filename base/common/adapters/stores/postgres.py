import abc
import decimal
import json
from datetime import datetime
from typing import ContextManager, List, Optional, Tuple

import psycopg
from psycopg_pool import ConnectionPool
from tenacity import Retrying, stop_after_delay, wait_random_exponential
from ulid import microsecond as ulid

from base.common.adapters.stores.common import (
    Repository,
    StoreConfig,
    StoreConnection,
    StoreCursor,
    StoreErrors,
)
from base.common.settings import PostgresConnectionSettings
from base.common.utils.logger import Logger


class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)


class PgJson(psycopg.types.json.Json):
    """Dumps dictionaries to be postgres compatible, serializing also non-default types"""

    def dumps(self, obj):
        return json.dumps(obj, cls=JsonEncoder)


def cast_token(v) -> str:
    if isinstance(v, dict):
        return "::JSONB"
    elif isinstance(v, list) and all(isinstance(x, dict) for x in v):
        return "::JSONB[]"
    return ""


class PostgresCursor(StoreCursor):
    cursor: psycopg.Cursor
    schema_name: str


class PostgresConnectionConfig(StoreConfig):
    user: str
    password: str
    host: str
    port: str
    database: str
    schema_name: str
    retry_max_timeout_seconds: int
    retry_max_total_delay_seconds: int
    pool_min_size: int
    pool_max_size: int
    pool_client_timeout: int
    pool_max_lifetime: float
    pool_max_idle: int
    pool_reconnect_timeout: int


class PostgresConnection(StoreConnection[ConnectionPool, psycopg.Cursor]):
    config: PostgresConnectionConfig

    def __init__(self, config: PostgresConnectionSettings, parent_logger: Logger):
        self.config = PostgresConnectionConfig(**config.model_dump())
        self.logger = parent_logger.child("postgres")
        self.connection_kwargs = {
            "user": self.config.user,
            "password": self.config.password,
            "host": self.config.host,
            "port": self.config.port,
            "dbname": self.config.database,
            "row_factory": psycopg.rows.dict_row,
            "autocommit": False,
        }
        self.pool: ConnectionPool = ConnectionPool(
            min_size=self.config.pool_min_size,
            max_size=self.config.pool_max_size,
            timeout=self.config.pool_client_timeout,
            max_lifetime=self.config.pool_max_lifetime,
            max_idle=self.config.pool_max_idle,
            reconnect_timeout=self.config.pool_reconnect_timeout,
            kwargs=self.connection_kwargs,
            open=False,
        )
        self.connection = self.connect()

    def connect(self) -> ConnectionPool:
        self.logger.debug("PostgresConnection: connecting to database with pool")
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
                    self.pool.open(wait=True, timeout=self.config.pool_client_timeout)
                    return self.pool
        except Exception as err:
            msg = f"PostgresConnection: unable to establish connection. {str(err)}"
            raise StoreErrors.Connection(msg)

    def is_connected(self, connection: ConnectionPool) -> bool:
        self.pool.check()
        return True

    def create_session(
        self, connection: ConnectionPool, autocommit: bool
    ) -> Tuple[psycopg.Cursor, Optional[ContextManager]]:
        conn_manager = connection.connection()
        conn = conn_manager.__enter__()
        conn.autocommit = autocommit
        return conn.cursor(), conn_manager

    def rollback_session(self, session: psycopg.Cursor):
        session.connection.rollback()

    def commit_session(self, session: psycopg.Cursor):
        session.connection.commit()

    def close_session(self, session: psycopg.Cursor):
        pass

    def create_cursor(self, session: psycopg.Cursor) -> PostgresCursor:
        return PostgresCursor(
            cursor=session,
            schema_name=self.config.schema_name,
        )


class PostgresRepo(Repository, abc.ABC):
    def _create_id(self):
        return str(ulid.new())

    def _utcnow(self):
        return datetime.utcnow()

    def _insert(
        self,
        curs: PostgresCursor,
        table_name: str,
        item: dict,
    ) -> dict:
        item["id"] = self._create_id()
        item["created_at"] = item["updated_at"] = self._utcnow()
        placeholders = [psycopg.sql.SQL(f"%({k})s{cast_token(v)}") for k, v in item.items()]
        query = psycopg.sql.SQL(
            "INSERT INTO {tbl} ({cols}) VALUES ({placeholders}) RETURNING *;"
        ).format(
            tbl=psycopg.sql.Identifier(curs.schema_name, table_name),
            cols=psycopg.sql.SQL(", ").join(map(psycopg.sql.Identifier, item)),
            placeholders=psycopg.sql.SQL(", ").join(placeholders),
        )
        try:
            curs.cursor.execute(
                query=query,
                params={k: PgJson(v) if isinstance(v, dict) else v for k, v in item.items()},
            )
        except psycopg.errors.UniqueViolation as err:
            msg = f"unique violation: {err}"
            raise StoreErrors.DuplicateKey(msg)
        return curs.cursor.fetchone()

    def _update(
        self,
        curs: PostgresCursor,
        table_name: str,
        supported_attributes: List[str],
        item_id: str,
        **kwargs,
    ) -> dict:
        if not (updates := {k: kwargs[k] for k in supported_attributes if k in kwargs}):
            raise StoreErrors.BaseError("at least one field to update must be passed")

        updates["updated_at"] = self._utcnow()
        query = psycopg.sql.SQL(
            """
            UPDATE {tbl} SET {placeholders}
            WHERE id = %(id)s RETURNING *;
            """
        ).format(
            tbl=psycopg.sql.Identifier(curs.schema_name, table_name),
            placeholders=psycopg.sql.SQL(", ").join(
                psycopg.sql.SQL("{col} = {val}").format(
                    col=psycopg.sql.Identifier(k), val=psycopg.sql.Placeholder(k)
                )
                for k in updates.keys()
            ),
        )

        curs.cursor.execute(query=query, params={"id": item_id, **updates})
        if not (result := curs.cursor.fetchone()):
            msg = f"not found for id={item_id}"
            raise StoreErrors.NotFound(msg)
        return result

    def _get_by_id(
        self,
        curs: PostgresCursor,
        table_name: str,
        elem_id: str,
        for_update: bool,
        account_id_field: str,
        account_id_value: Optional[str],
    ) -> dict:
        where_filter = "id = %(id)s"
        values = {"id": elem_id}
        if account_id_value and account_id_field:
            where_filter += f" AND {account_id_field} = %(account_id)s"
            values["account_id"] = account_id_value
        query = psycopg.sql.SQL("SELECT * FROM {tbl} {where} {for_update};").format(
            tbl=psycopg.sql.Identifier(curs.schema_name, table_name),
            where=psycopg.sql.SQL(f"WHERE {where_filter}"),
            for_update=psycopg.sql.SQL("FOR UPDATE" if for_update else ""),
        )

        curs.cursor.execute(query=query, params=values)
        if not (result := curs.cursor.fetchone()):
            msg = f"element not found for id={elem_id}"
            raise StoreErrors.NotFound(msg)
        return result

    def _delete(
        self,
        curs: PostgresCursor,
        table_name: str,
        elem_id: str,
        account_id_field: str,
        account_id_value: Optional[str],
    ):
        where_filter = "id = %(id)s"
        values = {"id": elem_id}
        if account_id_value and account_id_field:
            where_filter += f" AND {account_id_field} = %(account_id)s"
            values["account_id"] = account_id_value
        query = psycopg.sql.SQL("DELETE FROM {tbl} {where};").format(
            tbl=psycopg.sql.Identifier(curs.schema_name, table_name),
            where=psycopg.sql.SQL(f"WHERE {where_filter}"),
        )

        curs.cursor.execute(query=query, params=values)
