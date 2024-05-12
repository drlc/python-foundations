from typing import Callable, List, Optional

from pydantic import BaseModel

from base.common.endpoints.direct.direct_endpoint import DirectEndpoint, DirectEndpointApp
from base.common.endpoints.direct.security.common import PassedAuthenticationBackend


class SQSRecord(BaseModel):
    body: str
    attributes: Optional[dict] = {}
    messageAttributes: Optional[dict] = {}


class SQSEvent(BaseModel):
    Records: List[SQSRecord]


class SNSNotificationBody(BaseModel):
    Message: str
    MessageAttributes: Optional[dict] = {}


class SNSNotificationRecord(BaseModel):
    Sns: SNSNotificationBody


class SNSNotificationEvent(BaseModel):
    Records: List[SNSNotificationRecord]


class AWSDirectEndpointApp(DirectEndpointApp):
    @classmethod
    def add_endpoints(
        cls, auth: Optional[PassedAuthenticationBackend], endpoints: List[DirectEndpoint]
    ):
        def _create_endpoint(method: Callable):
            def ep(cls, aws_event, aws_context):
                if auth is not None:
                    auth.force_admin()
                return method(aws_event)

            return ep

        for endpoint in endpoints:
            for method in endpoint.get_endpoints():
                method_name = method.__name__
                if method_name.startswith("endpoint_") is True:
                    setattr(cls, method_name, classmethod(_create_endpoint(method)))
        return cls
