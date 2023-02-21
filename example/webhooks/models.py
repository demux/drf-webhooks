from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from drf_webhooks.models import AbstractWebhook, AbstractWebhookLogEntry


class Webhook(AbstractWebhook):
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    def __str__(self):
        return 'id=%s, events=%s, owner=%s' % (
            str(self.id),
            ', '.join(self.events),
            str(self.owner),
        )

    class Meta:
        verbose_name = _("webhook")
        verbose_name_plural = _("webhooks")


class WebhookLogEntry(AbstractWebhookLogEntry):
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("webhook log entry")
        verbose_name_plural = _("webhook log")
