import datetime
from typing import Annotated

import ulid
from fastapi import Depends

from base.common import usecases as common
from base.common.adapters.stores.common import StoreConnection, StoreCursor
from base.common.containers import CtnrApplication
from base.common.usecases import WithStoreConnection
from base.common.utils.logger import Logger
from example_app.adapters.gateways.g_entity import ExampleHttpGateway
from example_app.adapters.stores.s_entity import ExamplePostgresRepo
from example_app.settings import UseCaseSettings
from example_app.usecases.dto.example import ExampleDTO


class UsecaseReq(common.UsecaseReq):
    example_id: str


class Usecase(common.Usecase):
    def __init__(
        self,
        parent_logger: Annotated[Logger, Depends(CtnrApplication().provider(Logger))],
        conn: Annotated[StoreConnection, Depends(CtnrApplication().provider(StoreConnection))],
        example_repo: Annotated[ExamplePostgresRepo, Depends()],
        example_gateway: Annotated[ExampleHttpGateway, Depends()],
    ):
        super().__init__(parent_logger, conn)
        self.usecase_settings = UseCaseSettings()
        self.example_repo = example_repo
        self.example_gateway = example_gateway

    @WithStoreConnection.with_cursor()
    def execute(self, req: UsecaseReq, curs: StoreCursor) -> ExampleDTO:
        res = self.example_repo.save(
            curs=curs,
            example={
                "id": str(ulid.new()),
                "created_at": datetime.datetime.now(tz=datetime.timezone.utc),
                "updated_at": datetime.datetime.now(tz=datetime.timezone.utc),
                "json_data": {"example_id": req.example_id},
            },
        )
        return ExampleDTO(
            usecase_value=self.usecase_settings.account_id,
            store_value=self.example_repo.get(curs=curs, example_id=res["id"]),
            gateway_value=self.example_gateway.get_example(req.example_id),
        )
