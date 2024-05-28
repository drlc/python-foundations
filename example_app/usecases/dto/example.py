from typing import Any

from base.common.usecases import BaseDTO


class ExampleDTO(BaseDTO):
    usecase_value: str
    store_value: Any
    gateway_value: str
