from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from base.common.adapters.stores.dynamo import dynamo_direct_deserializer, dynamo_direct_serializer


class DyTableUtils(BaseModel):
    table: Any
    scan_attributes: List[str]
    scan_filter: Optional[Any] = None

    def fetchall(self):
        items = []
        res = None
        while res is None or "LastEvaluatedKey" in res:
            args = {
                "ProjectionExpression": ",".join(self.scan_attributes),
            }
            if self.scan_filter:
                args["FilterExpression"] = self.scan_filter
            if res is not None and "LastEvaluatedKey" in res:
                args["ExclusiveStartKey"] = res["LastEvaluatedKey"]
            res = self.table.scan(**args)
            items.extend(res.get("Items", []))
        return [self._des(dynamo_direct_deserializer(x)) for x in items]

    def insertmany(self, items: List[Dict[str, Any]]):
        with self.table.batch_writer() as batch:
            for x in items:
                keys = self.create_keys(x)
                batch.put_item(Item=self._ser(dynamo_direct_serializer({**x, **keys})))

    def create_keys(self, item: Dict) -> Dict[str, str]:
        return {}

    @classmethod
    def _ser(cls, item: dict) -> dict:
        return item

    @classmethod
    def _des(cls, item: dict) -> dict:
        return item
