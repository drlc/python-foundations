from pydantic import Field
from pydantic_settings import BaseSettings

from base.common.settings import (
    AppSettings,
    GeneralSettings,
    HttpGatewaySettings,
    LoggingSettings,
    PostgresConnectionSettings,
    WebAPISettings,
)


class UseCaseSettings(BaseSettings):
    account_id: str = Field(alias="ACCOUNT_ID")


class ExampleGatewaySettings(HttpGatewaySettings):
    url: str = Field(alias="EXAMPLE_GATEWAY_URL")
    correlation_id_header: str = Field(
        default="X-Flow-ID", alias="FLOW_CORRELATION_ID_INCOMING_HEADER"
    )
    retry_attempts: int = Field(default=3, alias="EXAMPLE_GATEWAY_RETRY_ATTEMPTS")
    retry_sleep_time_seconds: int = Field(
        default=3, alias="EXAMPLE_GATEWAY_RETRY_SLEEP_TIME_SECONDS"
    )


class GatewaySettings(BaseSettings):
    example: ExampleGatewaySettings = ExampleGatewaySettings()


class ServiceSettings(AppSettings):
    app: GeneralSettings = GeneralSettings()
    logging: LoggingSettings = LoggingSettings()
    store_connection: PostgresConnectionSettings = PostgresConnectionSettings()
    api: WebAPISettings = WebAPISettings()
    usecase: UseCaseSettings = UseCaseSettings()
    gateway: GatewaySettings = GatewaySettings()
