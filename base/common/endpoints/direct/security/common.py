from typing import Optional

from base.common.endpoints.security import ADMIN_GROUP, USER_GROUP, BaseWrapperUser
from base.common.utils.context import CallContext
from base.common.utils.logger import Logger


class PassedAuthenticationBackend:
    logger: Logger
    admin_token: Optional[str] = None

    def force_admin(self) -> BaseWrapperUser:
        user = BaseWrapperUser(
            user_id=self.admin_token,
            device_id=self.admin_token,
            account_groups=[USER_GROUP, ADMIN_GROUP],
        )
        CallContext.set_authenticated_user(user)
        return user
