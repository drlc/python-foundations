"""
Inspired from
https://github.com/dmontagu/fastapi-utils/blob/af95ff4a8195caaa9edaa3dbd5b6eeb09691d9c7/fastapi_utils/timing.py
"""

import resource
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class TimingStats:
    def __post_init__(self):
        self.start_time: float = 0
        self.start_cpu_time: float = 0
        self.end_cpu_time: float = 0
        self.end_time: float = 0
        self._result: dict = None

    def start(self) -> None:
        self.start_time = time.time()
        self.start_cpu_time = _get_cpu_time()

    def take_split(self) -> None:
        self.end_time = time.time()
        self.end_cpu_time = _get_cpu_time()

    @property
    def time(self) -> float:
        return self.end_time - self.start_time

    @property
    def cpu_time(self) -> float:
        return self.end_cpu_time - self.start_cpu_time

    def __enter__(self) -> "TimingStats":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.take_split()
        self._result = {
            "wall_ms": round(1000 * self.time, 2),
            "cpu_ms": round(1000 * self.cpu_time, 2),
        }

    def get_results(self):
        return self._result


def _get_cpu_time() -> float:
    resources = resource.getrusage(resource.RUSAGE_SELF)
    # add up user time (ru_utime) and system time (ru_stime)
    return resources[0] + resources[1]
