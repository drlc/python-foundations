from contextvars import ContextVar, Token
from typing import Optional
from uuid import uuid4

from base.common.endpoints.security import BaseWrapperUser

CORRELATION_ID_CTX_KEY = "correlation-id"
FLOW_CORRELATION_ID_CTX_KEY = "flow-correlation-id"
AUTHENTICATED_USER_CTX_KEY = "authenticated-user"
_correlation_id_ctx_var: ContextVar[Optional[str]] = ContextVar(
    CORRELATION_ID_CTX_KEY, default=None
)
_flow_correlation_id_ctx_var: ContextVar[Optional[str]] = ContextVar(
    FLOW_CORRELATION_ID_CTX_KEY, default=None
)
_authenticated_user_ctx_var: ContextVar[Optional[BaseWrapperUser]] = ContextVar(
    AUTHENTICATED_USER_CTX_KEY, default=None
)


class CallContext:
    """Static wrapper class to manage the context."""

    @staticmethod
    def get_correlation_id() -> Optional[str]:
        if _correlation_id_ctx_var.get() is None:
            CallContext.set_correlation_id(CallContext.generate_correlation_id())
        return _correlation_id_ctx_var.get()

    @staticmethod
    def set_correlation_id(correlation_id: str) -> Token:
        return _correlation_id_ctx_var.set(correlation_id)

    @staticmethod
    def get_flow_correlation_id() -> Optional[str]:
        if _flow_correlation_id_ctx_var.get() is None:
            CallContext.set_flow_correlation_id(CallContext.generate_correlation_id())
        return _flow_correlation_id_ctx_var.get()

    @staticmethod
    def set_flow_correlation_id(flow_correlation_id: str) -> Token:
        return _flow_correlation_id_ctx_var.set(flow_correlation_id)

    @staticmethod
    def generate_correlation_id() -> str:
        return str(uuid4())

    @staticmethod
    def get_authenticated_user() -> Optional[BaseWrapperUser]:
        return _authenticated_user_ctx_var.get()

    @staticmethod
    def set_authenticated_user(authenticated_user: Optional[BaseWrapperUser]) -> Token:
        return _authenticated_user_ctx_var.set(authenticated_user)
