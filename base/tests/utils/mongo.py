from typing import Any, Dict, List

from pydantic import ConfigDict

from base.tests.utils import TableUtils


class MnTableUtils(TableUtils):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    cursor: Any
    schema_name: str
    table_name: str

    def fetchall(self):
        db = self.cursor.client.get_database(self.schema_name)
        elems = [row for row in db[self.table_name].find()]
        [x.update({"id": x["_id"]}) for x in elems]
        [x.pop("_id") for x in elems]
        return elems

    def insertmany(self, items: List[Dict[str, Any]]):
        if not items:
            return []

        elems = [x.copy() for x in items]
        [x.update({"_id": x["id"]}) for x in elems]
        [x.pop("id") for x in elems]
        db = self.cursor.client.get_database(self.schema_name)
        collection = db[self.table_name]
        res = collection.insert_many(elems)
        self.cursor.commit_transaction()
        inserted_ids = res.inserted_ids
        inserted_documents = collection.find({"_id": {"$in": inserted_ids}})
        [x.update({"id": x["_id"]}) for x in inserted_documents]
        [x.pop("_id") for x in inserted_documents]
        return inserted_documents
