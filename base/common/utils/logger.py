import json
from dataclasses import dataclass
from typing import Any, Mapping, Tuple

import structlog
from pydantic import BaseModel


class Logger:
    def child(self, suffix: str, **values) -> "Logger": ...
    def bind(self, **values) -> "Logger": ...
    def debug(self, msg: str, *args, **kwargs): ...
    def info(self, msg: str, *args, **kwargs): ...
    def warning(self, msg: str, *args, **kwargs): ...
    def error(self, msg: str, *args, **kwargs): ...


@dataclass
class BasicLogger(Logger):
    name: str
    values: Mapping[str, Any] = None
    _logger = None

    def __post_init__(self):
        self._logger = structlog.get_logger(self.name, **(self.values or {}))

    def child(self, suffix: str, **values) -> "Logger":
        data = {**self._logger._context, **values}
        return BasicLogger(name=".".join([self.name, suffix]), values=data)

    def bind(self, **values) -> "Logger":
        _log = self._logger.bind(**values)
        return BasicLogger(name=self.name, values=_log._context)

    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._logger.exception(msg, *args, **kwargs)

    def _args_to_string(self, map: Tuple[Any]) -> Tuple[str]:
        return tuple(self._serialize_element(v) for v in map)

    def _kwargs_to_string(self, map: Mapping[str, Any]) -> Mapping[str, str]:
        return {k: self._serialize_element(v) for k, v in map.items()}

    def _serialize_element(self, element: Any) -> str:
        if isinstance(element, str):
            return element
        if isinstance(element, BaseModel):
            return element.model_dump()
        return json.dumps(element)
