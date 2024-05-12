import functools
import inspect
from dataclasses import dataclass
from typing import Callable, Optional, Sequence, Tuple

import starlette.authentication as star_auth
from fastapi.security import HTTPBearer
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from base.common.endpoints.security import BaseWrapperUser
from base.common.utils.context import CallContext
from base.common.utils.logger import Logger

StarletteAuthenticateResult = Tuple[star_auth.AuthCredentials, star_auth.BaseUser]


class APIUser(star_auth.BaseUser, BaseWrapperUser):
    @property
    def display_name(self) -> str:
        return self.user_id

    @property
    def identity(self) -> str:
        return self.user_id


@dataclass
class BearerAuthenticationBackend(star_auth.AuthenticationBackend):
    logger: Logger
    prefix: str = "Bearer"
    auth_scheme = HTTPBearer()

    def get_token_from_header(self, authorization: str, prefix: str) -> str:
        """Parses the Authorization header and returns only the token"""
        try:
            scheme, token = authorization.split()
        except ValueError:
            raise star_auth.AuthenticationError("Could not separate Authorization scheme and token")
        if scheme.lower() != prefix.lower():
            raise star_auth.AuthenticationError(f"Authorization scheme is not supported: {scheme}")
        return token

    def get_payload_data(self, token: str) -> APIUser:
        raise NotImplementedError()  # pragma: no cover

    async def authenticate(self, request) -> Optional[StarletteAuthenticateResult]:
        if not (auth := request.headers.get("Authorization")):
            return None

        try:
            token = self.get_token_from_header(authorization=auth, prefix=self.prefix)
            user = self.get_payload_data(token)
            user.account_groups.append("authenticated")
        except star_auth.AuthenticationError as err:
            msg = f"Error while authentication: {str(err)}"
            self.logger.warning(msg, err=err)
            raise err
        except Exception as err:
            msg = f"Unexpected error while authentication: {str(err)}"
            self.logger.warning(msg, err=err)
            raise star_auth.AuthenticationError(err)
        return star_auth.AuthCredentials(scopes=user.groups), user


def authorize(scopes: Sequence[Sequence[str]]):
    def decorator(func: Callable):
        sig = inspect.signature(func)
        for _, parameter in enumerate(sig.parameters.values()):
            if parameter.name == "request":
                break
        else:
            raise Exception(f'No "request" argument on function "{func}"')

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Response:
            request = kwargs.get("request")
            assert isinstance(request, Request)

            if not request.headers.get("authorization"):
                raise HTTPException(status_code=401)

            user = request.scope["user"]
            assert isinstance(user, APIUser)
            CallContext.set_authenticated_user(user)

            for single_scope_list in scopes:
                if star_auth.has_required_scope(request, single_scope_list):
                    return func(*args, **kwargs)

            raise HTTPException(status_code=403)

        return wrapper

    return decorator
