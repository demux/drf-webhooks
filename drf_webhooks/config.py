from dataclasses import dataclass

from django.apps import apps
from django.conf import settings


@dataclass
class WebhooksConfig:
    MAIN_APP: str = 'webhooks'
    LOG_RETENTION: str = '2 weeks'
    DEFAULT_JSON_RENDERER_CLASS: str = 'rest_framework.renderers.JSONRenderer'
    DEFAULT_XML_RENDERER_CLASS: str = 'rest_framework_xml.renderers.XMLRenderer'
    OWNER_FIELD: str = 'owner'

    @property
    def WEBHOOK_MODEL(self):
        return apps.get_model(self.MAIN_APP, "Webhook")

    @property
    def WEBHOOK_MODEL_NAME(self):
        return f"{self.MAIN_APP}.Webhook"

    @property
    def WEBHOOK_LOG_ENTRY_MODEL(self):
        return apps.get_model(self.MAIN_APP, "WebhookLogEntry")

    @property
    def WEBHOOK_LOG_ENTRY_MODEL_NAME(self):
        return f"{self.MAIN_APP}.WebhookLogEntry"


conf = WebhooksConfig(**getattr(settings, 'WEBHOOKS', {}))

REGISTERED_WEBHOOK_CHOICES = {}
