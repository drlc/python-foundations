import abc
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict


class TableUtils(BaseModel, abc.ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    cursor: Any
    schema_name: str
    table_name: str

    def fetchall(self):
        raise NotImplementedError()

    def insertmany(self, items: List[Dict[str, Any]]):
        raise NotImplementedError()


def check_expected_data(result: List[dict], expected: List[dict]):
    """Check if result contains expected data"""
    assert len(result) == len(expected)
    for result_item, expected_item in zip(result, expected):
        for key, value in expected_item.items():
            if value is None:
                assert result_item.get(key, None) is None, f"key={key} {result_item[key]}!={value}"
            elif hasattr(value, "isoformat") and not hasattr(
                result_item[key], "isoformat"
            ):  # is datetime
                assert (
                    result_item[key] == value.isoformat()
                ), f"key={key} {result_item[key]}!={value.isoformat()}"
            elif hasattr(result_item[key], "isoformat") and not hasattr(
                value, "isoformat"
            ):  # is datetime
                assert (
                    result_item[key].isoformat() == value
                ), f"key={key} {result_item[key].isoformat()}!={value}"
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                check_expected_data(result_item[key], value)
            elif isinstance(value, dict):
                check_expected_data([result_item[key]], [value])
            else:
                assert result_item[key] == value, f"key={key} {result_item[key]}!={value}"


def check_expected_db_data(
    table: TableUtils, expected: list, sorted_by: callable = lambda x: x["id"]
):
    """Check if result contains expected data"""
    if sorted_by:
        check_expected_data(
            sorted(table.fetchall(), key=sorted_by), sorted(expected, key=sorted_by)
        )
    else:
        check_expected_data(table.fetchall(), expected)
