import swapper
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import models as webhook_models

Webhook: webhook_models.AbstractWebhook = swapper.load_model("webhooks", "Webhook")


class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = (
            'id',
            'dt_created',
            'dt_updated',
            'events',
            'target_url',
            'target_method',
            'target_content_type',
            'target_headers',
        )


class WebhookViewSet(viewsets.ModelViewSet):
    model = Webhook
    serializer_class = WebhookSerializer
    queryset = Webhook.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        # TODO: filter owners
        return qs

    @action(detail=True, methods=['post'])
    def trigger(self, request, pk=None):
        self.get_object().trigger()
        return Response(status=204)
