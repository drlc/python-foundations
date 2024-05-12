from typing import Any, Dict, List

from psycopg2 import extras, sql

from base.common.adapters.stores.postgres import PgJson, cast_token
from base.tests.utils import TableUtils


class PgTableUtils(TableUtils):
    cursor: Any
    schema_name: str
    table_name: str

    class Config:
        arbitrary_types_allowed = True

    def fetchall(self):
        query = sql.SQL("SELECT * FROM {tbl};").format(
            tbl=sql.Identifier(self.schema_name, self.table_name),
        )
        self.cursor.execute(query)
        return [row for row in self.cursor.fetchall()]

    def insertmany(self, items: List[Dict[str, Any]]):
        if not items:
            return []

        cols = set(k for row in items for k in row.keys())
        sample_key_value = {
            k: next((x[k] for x in items if x.get(k) is not None), None) for k in cols
        }

        template = ", ".join(f"%({k})s{cast_token(v)}" for k, v in sample_key_value.items())
        query = sql.SQL("INSERT INTO {tbl} ({cols}) VALUES %s RETURNING *;").format(
            tbl=sql.Identifier(self.schema_name, self.table_name),
            cols=sql.SQL(", ").join(map(sql.Identifier, sample_key_value)),
        )
        result = extras.execute_values(
            cur=self.cursor,
            sql=query.as_string(self.cursor),
            argslist=[
                {
                    k: PgJson(row.get(k)) if isinstance(row.get(k), dict) else row.get(k)
                    for k in cols
                }
                for row in items
            ],
            template=f"({template})",
            fetch=True,
        )
        self.cursor.connection.commit()
        return [row for row in result]
