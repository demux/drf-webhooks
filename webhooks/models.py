import uuid

from django.db import models
from django_better_admin_arrayfield.models.fields import ArrayField


class Webhook(models.Model):
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

    owner = models.ForeignKey('WebhookOwner', on_delete=models.CASCADE)  # FIXME: Configurable

    events = ArrayField(models.CharField(max_length=64, db_index=True))

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
        return '%s for %s' % (
            ', '.join(self.events),
            self.owner,
        )

    def __repr__(self):
        return '<Webhook: %s for %s>' % (
            self.events,
            self.owner.id,  # FIXME: Configurable
        )


class WebhookLogEntry(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    webhook = models.ForeignKey(Webhook, null=True, on_delete=models.SET_NULL, related_name="log_entries")

    owner = models.ForeignKey('WebhookOwner', on_delete=models.CASCADE, related_name="log_entries")   # FIXME: Configurable
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
