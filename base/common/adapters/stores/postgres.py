import abc
import decimal
import json
from datetime import datetime
from typing import List, Optional

import psycopg2
from psycopg2 import extensions, extras, sql
from psycopg2._psycopg import connection as PgConnection
from psycopg2._psycopg import cursor as PgCursor
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


class PgJson(extras.Json):
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
    cursor: PgCursor
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


class PostgresConnection(StoreConnection[PgConnection, PgConnection]):
    config: PostgresConnectionConfig

    def __init__(self, config: PostgresConnectionSettings, parent_logger: Logger):
        self.config = PostgresConnectionConfig(**config.model_dump())
        self.logger = parent_logger.child("postgres")

    def connect(self) -> PgConnection:
        extensions.register_adapter(dict, extras.Json)
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
                    connection = psycopg2.connect(
                        user=self.config.user,
                        password=self.config.password,
                        host=self.config.host,
                        port=self.config.port,
                        database=self.config.database,
                    )
                    connection.autocommit = True
                    return connection
        except Exception as err:
            msg = f"PostgresConnection: unable to establish connection. {str(err)}"
            raise StoreErrors.Connection(msg)

    def is_connected(self, connection: PgConnection) -> bool:
        return False

    def create_session(self, connection: PgConnection) -> PgConnection:
        return connection

    def rollback_session(self, session: PgConnection):
        session.rollback()

    def commit_session(self, session: PgConnection):
        session.commit()

    def close_session(self, session: PgConnection):
        session.close()

    def create_cursor(self, session: PgConnection) -> PostgresCursor:
        return PostgresCursor(
            cursor=session.cursor(cursor_factory=extras.RealDictCursor),
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
        placeholders = [sql.SQL(f"%({k})s{cast_token(v)}") for k, v in item.items()]
        query = sql.SQL("INSERT INTO {tbl} ({cols}) VALUES ({placeholders}) RETURNING *;").format(
            tbl=sql.Identifier(curs.schema_name, table_name),
            cols=sql.SQL(", ").join(map(sql.Identifier, item)),
            placeholders=sql.SQL(", ").join(placeholders),
        )
        try:
            curs.cursor.execute(
                query=query,
                vars={k: PgJson(v) if isinstance(v, dict) else v for k, v in item.items()},
            )
        except psycopg2.errors.UniqueViolation as err:
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
        query = sql.SQL(
            """
            UPDATE {tbl} SET {placeholders}
            WHERE id = %(id)s RETURNING *;
            """
        ).format(
            tbl=sql.Identifier(curs.schema_name, table_name),
            placeholders=sql.SQL(", ").join(
                sql.SQL("{col} = {val}").format(col=sql.Identifier(k), val=sql.Placeholder(k))
                for k in updates.keys()
            ),
        )

        curs.cursor.execute(query=query, vars={"id": item_id, **updates})
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
        query = sql.SQL("SELECT * FROM {tbl} {where} {for_update};").format(
            tbl=sql.Identifier(curs.schema_name, table_name),
            where=sql.SQL(f"WHERE {where_filter}"),
            for_update=sql.SQL("FOR UPDATE" if for_update else ""),
        )

        curs.cursor.execute(query=query, vars=values)
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
        query = sql.SQL("DELETE FROM {tbl} {where};").format(
            tbl=sql.Identifier(curs.schema_name, table_name), where=sql.SQL(f"WHERE {where_filter}")
        )

        curs.cursor.execute(query=query, vars=values)
