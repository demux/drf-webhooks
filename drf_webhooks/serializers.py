from rest_framework import serializers

from .config import REGISTERED_WEBHOOK_CHOICES
from .fields import DynamicChoiceField


class WebhookEventSerializer(serializers.Serializer):
    webhook_id = serializers.UUIDField()
    event_id = serializers.UUIDField()
    dt_dispatched = serializers.DateTimeField()
    owner_id = serializers.IntegerField()
    event = DynamicChoiceField(choices=lambda: list(REGISTERED_WEBHOOK_CHOICES.items()))  # type: ignore
    object_id = serializers.CharField()
    payload = serializers.DictField()
