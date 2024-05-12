from typing import Optional

import boto3
from botocore.config import Config

from base.common.adapters.gateways.common import HttpGatewayConfig
from base.common.endpoints.direct.direct_endpoint import GenericAdminEvent
from base.common.utils.context import CallContext
from base.common.utils.logger import Logger

BOTO3_CONFIG = Config(retries={"max_attempts": 10, "mode": "adaptive"})


class SQSGatewayConfig(HttpGatewayConfig):
    region: Optional[str] = None


class SQSGateway:
    config: SQSGatewayConfig

    def __init__(self, config: SQSGatewayConfig, parent_logger: Logger):
        self.config = config
        self.opts = {
            "config": BOTO3_CONFIG,
        }
        if self.config.region:
            self.opts["region_name"] = self.config.region
        sqs = boto3.resource("sqs", **self.opts)
        self.queue = sqs.Queue(self.config.url)
        self.logger = parent_logger.child(self.__class__.__name__)

    def _send_message(self, message: GenericAdminEvent, further_attributes: dict = {}):
        attributes = {
            k: {"DataType": "String", "StringValue": str(v)} for k, v in further_attributes.items()
        }
        self.queue.send_message(
            MessageBody=message.json(),
            MessageAttributes={
                self.config.correlation_id_header: {
                    "DataType": "String",
                    "StringValue": CallContext.get_flow_correlation_id(),
                },
                **attributes,
            },
        )
