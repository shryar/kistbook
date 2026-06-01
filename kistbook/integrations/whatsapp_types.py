from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DeliveryStatus(BaseModel):
    id: str
    status: str
    timestamp: str


class InboundText(BaseModel):
    body: str


class InboundMessage(BaseModel):
    from_: str
    id: str
    timestamp: str
    text: Optional[InboundText] = None
    type: str

    model_config = {"populate_by_name": True}

    @classmethod
    def model_validate(cls, obj: object, **kwargs: object) -> InboundMessage:
        if isinstance(obj, dict) and "from" in obj:
            obj = dict(obj)
            obj["from_"] = obj.pop("from")
        return super().model_validate(obj, **kwargs)


class WebhookValue(BaseModel):
    statuses: Optional[list[DeliveryStatus]] = None
    messages: Optional[list[InboundMessage]] = None


class WebhookChange(BaseModel):
    value: WebhookValue


class WebhookEntry(BaseModel):
    changes: list[WebhookChange]


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: list[WebhookEntry]
