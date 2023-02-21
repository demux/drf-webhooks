import uuid

import swapper
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _


class AbstractWebhook(models.Model):
    class TargetMethod(models.TextChoices):
        GET = 'get', 'GET'
        PUT = 'put', 'PUT'
        POST = 'post', 'POST'
        PATCH = 'patch', 'PATCH'
        DELETE = 'delete', 'DELETE'

    class ContentType(models.TextChoices):
        JSON = 'application/json', 'JSON'
        XML = 'application/xml', 'XML'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    dt_created = models.DateTimeField(auto_now_add=True)
    dt_updated = models.DateTimeField(auto_now=True)

    events = ArrayField(models.CharField(max_length=128, db_index=True))

    target_url = models.URLField(max_length=255)
    target_method = models.CharField(
        max_length=6,
        choices=TargetMethod.choices,
        default=TargetMethod.POST,
    )
    target_content_type = models.CharField(
        max_length=64,
        choices=ContentType.choices,
        default=ContentType.JSON,
    )
    target_headers = models.JSONField(default=dict)

    def __str__(self):
        return 'id=%s, events=%s' % (self.id, ', '.join(self.events))

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self)

    class Meta:
        verbose_name = _("webhook")
        verbose_name_plural = _("webhooks")
        abstract = True


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
        swappable = swapper.swappable_setting('webhooks', 'Webhook')


class AbstractWebhookLogEntry(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    webhook = models.ForeignKey(Webhook, null=True, on_delete=models.SET_NULL, related_name="log_entries")

    event = models.CharField(max_length=64, db_index=True)

    req_dt = models.DateTimeField(null=True, blank=True, db_index=True)
    req_url = models.URLField(max_length=255, db_index=True)
    req_method = models.CharField(max_length=6, db_index=True)
    req_headers = models.JSONField()
    req_data = models.JSONField(null=True, blank=True)
    req_content = models.TextField(blank=True)

    res_dt = models.DateTimeField(null=True, blank=True, db_index=True)
    res_data = models.JSONField(null=True, blank=True)
    res_content = models.TextField(blank=True)
    res_headers = models.JSONField(null=True, blank=True)
    res_status = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)

    error_code = models.CharField(max_length=100, blank=True, db_index=True)
    error_message = models.TextField(blank=True)

    def __str__(self) -> str:
        return f'{self.req_dt}: {self.event}'

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self)

    class Meta:
        verbose_name = _("webhook log entry")
        verbose_name_plural = _("webhook log")
        abstract = True


class WebhookLogEntry(AbstractWebhookLogEntry):
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("webhook log entry")
        verbose_name_plural = _("webhook log")
        swappable = swapper.swappable_setting('webhooks', 'WebhookLogEntry')
