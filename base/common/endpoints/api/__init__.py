from typing import Callable, Dict, Type

from fastapi import FastAPI
from pydantic import BaseModel


class MiddlewareConfig(BaseModel):
    middleware: Type
    configs: Dict


class ExceptionHandler(BaseModel):
    exception: Type[Exception]
    handler: Callable


def add_healthcheck_api(app: FastAPI, further_prefix: str, version):
    class HealthResponse(BaseModel):
        version: str

    def handler():
        return {"version": version}

    app.add_api_route(
        path=further_prefix + "/health",
        endpoint=handler,
        summary="Health check",
        response_model=HealthResponse,
    )
