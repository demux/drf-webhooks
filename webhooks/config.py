from dataclasses import dataclass

from django.conf import settings

# These two live outside of the WEBHOOKS setting
# WEBHOOKS_WEBHOOK_MODEL
# WEBHOOKS_WEBHOOKLOGENTRY_MODEL


@dataclass
class WebhooksConfig:
    LOG_RETENTION: str = '2 weeks'
    DEFAULT_JSON_RENDERER_CLASS: str = 'rest_framework.renderers.JSONRenderer'
    DEFAULT_XML_RENDERER_CLASS: str = 'rest_framework_xml.renderers.XMLRenderer'
    OWNER_FIELD: str = 'owner'


conf = WebhooksConfig(**getattr(settings, 'WEBHOOKS', {}))

REGISTERED_WEBHOOK_CHOICES = {}
