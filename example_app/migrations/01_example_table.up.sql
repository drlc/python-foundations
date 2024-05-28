BEGIN;

CREATE TABLE IF NOT EXISTS ex.example_table (
    "id"            VARCHAR(36) PRIMARY KEY,
    "created_at"    TIMESTAMP WITH TIME ZONE,
    "updated_at"    TIMESTAMP WITH TIME ZONE,
    "json_data"     JSON
);

COMMIT;
