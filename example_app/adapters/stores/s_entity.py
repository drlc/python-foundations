from psycopg import Cursor as PgCursor

from base.common.adapters.stores.postgres import PostgresRepo


class ExamplePostgresRepo(PostgresRepo):
    example_table: str = "example_table"

    def save(self, curs: PgCursor, example: dict):
        result = self._insert(curs=curs, table_name=self.example_table, item=example)
        return result

    def get(self, curs: PgCursor, example_id: int):
        result = self._get_by_id(
            curs=curs,
            table_name=self.example_table,
            elem_id=example_id,
            for_update=False,
            account_id_field="example_id",
            account_id_value=None,
        )
        return result
