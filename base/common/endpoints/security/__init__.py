from typing import List

from pydantic import BaseModel

ADMIN_GROUP = "admin"
USER_GROUP = "user"


class BaseWrapperUser(BaseModel):
    user_id: str
    device_id: str = None
    account_groups: List[str] = []

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def identification(self) -> str:
        return self.user_id

    @property
    def device_identification(self) -> str:
        return self.device_id

    @property
    def groups(self) -> List[str]:
        return self.account_groups
