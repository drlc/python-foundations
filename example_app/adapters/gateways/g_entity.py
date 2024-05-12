from typing import Annotated

from fastapi import Depends

from base.common.adapters.gateways.common import HttpGateway
from base.common.containers import CtnrApplication
from base.common.utils.logger import Logger
from example_app.settings import ExampleGatewaySettings


class ExampleHttpGateway(HttpGateway):
    example_table: str = "example"

    def __init__(
        self, parent_logger: Annotated[Logger, Depends(CtnrApplication().provider(Logger))]
    ) -> None:
        super().__init__(ExampleGatewaySettings(), parent_logger)

    def get_example(self, example_id: int):
        return f"example_gateway {example_id}"
