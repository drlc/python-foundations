from fastapi import Depends, Path
from fastapi.routing import APIRoute
from starlette.requests import Request

from base.common.endpoints.api.api_endpoint import APIEndpoint as BaseAPIEndpoint
from base.common.endpoints.api.api_endpoint import HTTPResponseWrapper
from base.common.endpoints.api.api_exception_handlers import JsonApiErrors
from example_app.usecases import get_example
from example_app.usecases.dto.example import ExampleDTO


class APIEndpoint(BaseAPIEndpoint):

    def route_get_example(self):
        """Retrieves a specific example."""

        def endpoint(
            request: Request,
            example_id: str = Path(..., description="The id."),
            usecase: get_example.Usecase = Depends(get_example.Usecase),
        ):
            req = get_example.UsecaseReq(
                example_id=example_id,
            )
            res = usecase.execute(req=req)
            return HTTPResponseWrapper[ExampleDTO](data=res)

        return APIRoute(
            path="/example/{example_id}",
            endpoint=endpoint,
            status_code=200,
            response_model=HTTPResponseWrapper[ExampleDTO],
            response_description="The example data",
            methods=["GET"],
            summary="Retrieve an example",
            tags=["Example"],
            responses={
                403: {
                    "model": JsonApiErrors,
                    "description": "Resources not available for the user.",
                },
                404: {"model": JsonApiErrors, "description": "Resources does not exists."},
                500: {"model": JsonApiErrors, "description": "Internal server error."},
            },
        )
