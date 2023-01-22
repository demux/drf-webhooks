from django.conf import settings

conf = getattr(settings, 'WEBHOOKS', {})

REGISTERED_WEBHOOK_CHOICES = {}
