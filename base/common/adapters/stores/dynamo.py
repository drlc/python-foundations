import abc
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from functools import partial
from typing import Any, Dict, List, Optional, Tuple, Type

import boto3
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.conditions import ConditionBase as DynamoConditionBase
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.config import Config
from botocore.exceptions import ClientError
from mypy_boto3_dynamodb.service_resource import Table as DynamoTable
from ulid import microsecond as ulid

from base.common.adapters.stores.common import (
    Repository,
    StoreConfig,
    StoreConnection,
    StoreCursor,
    StoreErrors,
)
from base.common.entities import BaseEntity
from base.common.settings import DynamoDbConnectionSettings
from base.common.utils.logger import Logger

BOTO3_CONFIG = Config(retries={"max_attempts": 10, "mode": "adaptive"})
botodynamodeser = partial(TypeDeserializer().deserialize)
botodynamoser = partial(TypeSerializer().serialize)


def dynamo_direct_deserializer(o: Dict) -> Dict:
    def _des(d):
        if isinstance(d, dict):
            if "datetime" in d:
                return datetime.fromisoformat(d["datetime"])
            elif "date" in d:
                return date.fromisoformat(d["date"])
            elif "time" in d:
                return time.fromisoformat(d["time"])
            elif "float" in d:
                return float(d["float"])
            else:
                return d
        else:
            return d

    return {k: _des(v) for k, v in o.items()}


def dynamo_direct_serializer(o: Dict) -> Dict:
    def _ser(d):
        if isinstance(d, datetime):
            return {"datetime": d.isoformat()}
        elif isinstance(d, date):
            return {"date": d.isoformat()}
        elif isinstance(d, time):
            return {"time": d.isoformat()}
        elif isinstance(d, float):
            return {"float": Decimal(str(d))}
        else:
            return d

    return {k: _ser(v) for k, v in o.items()}


Boto3Session = boto3.session.Session
DynamoDbResource = boto3.session.Session.resource


@dataclass
class DynamoDbCursor(StoreCursor):
    cursor: DynamoDbResource
    one_table_name: str


@dataclass
class DynamoDbConnectionConfig(StoreConfig):
    region: str
    one_table_name: str
    retry_max_timeout_seconds: int
    retry_max_total_delay_seconds: int


class DynamoDbConnection(StoreConnection[None, Boto3Session]):
    config: DynamoDbConnectionConfig

    def __init__(self, config: DynamoDbConnectionSettings, parent_logger: Logger):
        self.config = DynamoDbConnectionConfig(**config)
        self.opts = {
            "config": BOTO3_CONFIG,
            "region_name": self.config.region,
        }
        self.logger = parent_logger.child("dynamo")

    def connect(self) -> None:
        return None

    def is_connected(self, connection: None) -> bool:
        # Resource are not thread safe, so in this way
        # everytime the client requests a cursor, it creates a new one
        return False

    def create_session(self, connection: None, autocommit: bool) -> Tuple[Boto3Session, None]:
        return boto3.session.Session(region_name=self.opts["region_name"]), None

    def rollback_session(self, session: Boto3Session):
        return

    def commit_session(self, session: Boto3Session):
        return

    def close_session(self, session: Boto3Session):
        return

    def create_cursor(self, session: Boto3Session) -> DynamoDbCursor:
        return DynamoDbCursor(
            cursor=session.resource("dynamodb", **self.opts),
            one_table_name=self.config.one_table_name,
        )


class DynamoDbRepo(Repository, abc.ABC):
    def _create_id(self):
        return str(ulid.new())

    def _utcnow(self):
        return datetime.utcnow()

    ###
    # adds the primary key to the passed value and
    # returns a dict of <name attribute: value> of the key
    ###
    def _insert_primary_key(self, item: dict) -> dict:
        raise NotImplementedError()

    def _get_key_names(self) -> List[str]:
        raise NotImplementedError()

    def _projected_attributes(self, cls: Type[BaseEntity]) -> str:
        return list(cls.__fields__.keys()) + self._get_key_names()

    def _add_further_condition(
        self, condition: DynamoConditionBase, otheCondition: DynamoConditionBase
    ) -> DynamoConditionBase:
        if condition:
            return condition & otheCondition
        else:
            return otheCondition

    ###
    # transforms a dict into a condition, returning
    # a string for the conditions and a dict of values
    ###
    def _transform_in_condition_expression(self, el: dict) -> DynamoConditionBase:
        condition = None
        for k, v in el.items():
            if not condition:
                condition = Attr(k).not_exists()
            else:
                condition = condition & Attr(k).not_exists()
        return condition

    def _insert(
        self,
        dynamo_table: Any,
        item: dict,
        with_dates: bool = True,
    ) -> dict:
        keys = self._insert_primary_key(item)
        if with_dates:
            item["created_at"] = item["updated_at"] = self._utcnow()
        args = {"Item": dynamo_direct_serializer(item)}
        if isinstance(dynamo_table, DynamoTable):
            condition = self._transform_in_condition_expression(keys)
            args["ConditionExpression"] = condition
            args["ReturnValues"] = "NONE"
        try:
            dynamo_table.put_item(**args)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise StoreErrors.DuplicateKey("element already exists: " + str(keys))
            raise StoreErrors.BaseError(str(e))
        return item

    def _find_one(
        self,
        dynamo_table: Any,
        key_condition: DynamoConditionBase,
        proj_class: Optional[Type[BaseEntity]] = None,
        key_name: Optional[str] = None,
        further_condition: Optional[DynamoConditionBase] = None,
        ascending: bool = True,
    ) -> dict:
        items = []
        res = None
        projection = self._projected_attributes(proj_class) if proj_class else self._get_key_names()
        args = {
            "ProjectionExpression": ",".join(projection),
            "KeyConditionExpression": key_condition,
            "ScanIndexForward": ascending,
        }
        if key_name:
            args["IndexName"] = key_name
        if further_condition:
            args["FilterExpression"] = further_condition
        while (res is None or "LastEvaluatedKey" in res) and len(items) == 0:
            if res is not None and "LastEvaluatedKey" in res:
                args["ExclusiveStartKey"] = res["LastEvaluatedKey"]
            res = dynamo_table.query(**args)
            items.extend(res.get("Items", []))
        if len(items) != 1:
            msg = f"element not found for query={key_condition} {further_condition}"
            raise StoreErrors.NotFound(msg)
        res_des = dynamo_direct_deserializer(items[0])
        return res_des

    def _find_all(
        self,
        dynamo_table: Any,
        key_condition: DynamoConditionBase,
        key_name: Optional[str] = None,
        further_condition: Optional[DynamoConditionBase] = None,
        limit: Optional[int] = 0,
        project_attributes: Optional[List[str]] = None,
        ascending: bool = True,
    ) -> List[dict]:
        items = []
        res = None
        args = {
            "KeyConditionExpression": key_condition,
            "ScanIndexForward": ascending,
        }
        if limit != 0:
            args["Limit"] = limit
        if key_name:
            args["IndexName"] = key_name
        if project_attributes:
            args["ProjectionExpression"] = ",".join(project_attributes)
        if further_condition:
            args["FilterExpression"] = further_condition
        while (res is None or "LastEvaluatedKey" in res) and (
            (limit != 0 and len(items) <= limit) or (limit == 0)
        ):
            if res is not None and "LastEvaluatedKey" in res:
                args["ExclusiveStartKey"] = res["LastEvaluatedKey"]
            res = dynamo_table.query(**args)
            items.extend(res.get("Items", []))
        return [dynamo_direct_deserializer(x) for x in items[: limit or None]]

    def _update_one(
        self,
        dynamo_table: Any,
        supported_attributes: List[str],
        key_condition: dict,
        further_condition: Optional[DynamoConditionBase] = None,
        **kwargs,
    ) -> dict:
        if not (updates := {k: kwargs[k] for k in supported_attributes if k in kwargs}):
            raise StoreErrors.BaseError("at least one field to update must be passed")
        updates["updated_at"] = self._utcnow()
        updates_ser = dynamo_direct_serializer(updates)
        cleaned_keys = {k: k.replace(".", "_") for k in updates_ser.keys()}
        update_expression = "SET " + ", ".join([f"{k} = :{v}" for k, v in cleaned_keys.items()])
        expression_attribute_values = {f":{cleaned_keys[k]}": v for k, v in updates_ser.items()}

        args = {
            "Key": key_condition,
            "UpdateExpression": update_expression,
            "ReturnValues": "NONE",
            "ExpressionAttributeValues": expression_attribute_values,
        }
        if further_condition:
            args["ConditionExpression"] = further_condition
        dynamo_table.update_item(**args)

        return updates

    def _delete(
        self,
        dynamo_table: Any,
        key_condition: dict,
    ):
        args = {
            "Key": key_condition,
            "ReturnValues": "NONE",
        }
        dynamo_table.delete_item(**args)
