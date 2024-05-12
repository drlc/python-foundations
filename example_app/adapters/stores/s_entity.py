from base.common.adapters.stores.postgres import PostgresRepo


class ExamplePostgresRepo(PostgresRepo):
    example_table: str = "example"

    def get_example(self, example_id: int):
        return f"example_entity {example_id}"
