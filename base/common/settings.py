import abc
from typing import Optional

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings


class GeneralSettings(BaseSettings):
    name: str = Field(..., alias="SERVICE_NAME")
    env: str = Field(..., alias="ENV")
    version: str = Field(..., alias="SERVICE_VERSION")
    admin_aut_id: str = Field(alias="ADMIN_AUTH_ID")


class LoggingSettings(BaseSettings):
    level: str = Field(default="DEBUG", alias="LOG_LEVEL")


class StoreConnectionSettings(BaseSettings):
    class_name: str = Field(..., alias="STORE_CONNECTION_CLASS_NAME")
    class_name_settings: str = Field(..., alias="STORE_CONNECTION_CLASS_NAME_SETTINGS")


class HttpGatewaySettings(BaseSettings, abc.ABC):
    url: AnyHttpUrl
    correlation_id_header: str
    retry_attempts: int
    retry_sleep_time_seconds: float


class PostgresConnectionSettings(StoreConnectionSettings):
    user: str = Field(..., alias="POSTGRES_USER")
    password: str = Field(..., alias="POSTGRES_PASSWORD")
    host: str = Field(..., alias="POSTGRES_HOST")
    port: str = Field(..., alias="POSTGRES_PORT")
    database: str = Field(..., alias="POSTGRES_DB")
    schema_name: str = Field(..., alias="POSTGRES_SCHEMA")
    retry_max_timeout_seconds: int = Field(
        default=10, alias="POSTGRES_CONNECTION_RETRY_MAX_TIMEOUT_SECONDS"
    )
    retry_max_total_delay_seconds: int = Field(
        default=1, alias="POSTGRES_CONNECTION_RETRY_MAX_TOTAL_DELAY_SECONDS"
    )
    pool_min_size: int = Field(default=4, alias="POSTGRES_POOL_MIN_SIZE")
    pool_max_size: int = Field(default=20, alias="POSTGRES_POOL_MAX_SIZE")
    pool_client_timeout: int = Field(default=60, alias="POSTGRES_POOL_CLIENT_TIMEOUT")
    pool_max_lifetime: float = Field(default=3600.0, alias="POSTGRES_POOL_MAX_LIFETIME")
    pool_max_idle: int = Field(default=600, alias="POSTGRES_POOL_MAX_IDLE")
    pool_reconnect_timeout: int = Field(default=180, alias="POSTGRES_POOL_RECONNECT_TIMEOUT")


class MongoConnectionSettings(StoreConnectionSettings):
    uri_strings: str = Field(..., alias="MONGO_URI_STRINGS")
    database: str = Field(..., alias="MONGO_DB")
    retry_max_timeout_seconds: int = Field(
        default=10, alias="MONGO_CONNECTION_RETRY_MAX_TIMEOUT_SECONDS"
    )
    retry_max_total_delay_seconds: int = Field(
        default=1, alias="MONGO_CONNECTION_RETRY_MAX_TOTAL_DELAY_SECONDS"
    )


class DynamoDbConnectionSettings(StoreConnectionSettings):
    region: str = Field(..., alias="NAWS_REGION")
    one_table_name: str = Field(..., alias="DYNAMO_ONE_TABLE_NAME")
    retry_max_timeout_seconds: int = Field(default=10, alias="DYNAMO_RETRY_MAX_TIMEOUT_SECONDS")
    retry_max_total_delay_seconds: int = Field(
        default=1, alias="DYNAMO_RETRY_MAX_TOTAL_DELAY_SECONDS"
    )


class WebAPISettings(BaseSettings):
    title: str = Field(..., alias="WEBAPP_TITLE")
    root_path: Optional[str] = Field(default=None, alias="WEBAPP_ROOT_PATH")
    flow_correlation_id_incoming_header: str = Field(
        default="X-Flow-ID", alias="FLOW_CORRELATION_ID_INCOMING_HEADER"
    )
    correlation_id_outgoing_header: str = Field(
        default="X-Flow-ID", alias="FLOW_CORRELATION_ID_OUTGOING_HEADER"
    )
    cors_allow_origin_regex: str = Field(
        default="^https:\\/\\/(.*\\.|)project.io[\\/]?$", alias="CORS_ALLOW_ORIGIN_REGEX"  # noqa
    )
    further_prefix: Optional[str] = Field(default=None, alias="WEBAPP_FURTHER_PREFIX")
    version: str = Field(default="0", alias="WEBAPP_VERSION")


class AppSettings(BaseSettings):
    app: GeneralSettings = GeneralSettings()
    logging: LoggingSettings = LoggingSettings()
    store_connection: StoreConnectionSettings = StoreConnectionSettings()
    api: WebAPISettings = WebAPISettings()
