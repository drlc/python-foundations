from collections import Counter
from enum import Enum
from typing import List


class SortingOrder(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class Sorting:
    field: str
    order: SortingOrder

    def __init__(self, sorting: str):
        self.field = sorting.split(":")[0].lower()
        self.order = SortingOrder(sorting.split(":")[1].upper())


class SortingSequence(List[Sorting]):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        # cannot use the same sorting field more than once
        if v and (duplicates := [k for k, v in Counter([x.field for x in v]).items() if v > 1]):
            raise TypeError(f"found duplicate sort fields: {', '.join(duplicates)}")
        return v
