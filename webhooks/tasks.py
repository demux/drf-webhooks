import importlib
import logging
from contextlib import suppress
from typing import TYPE_CHECKING, Type
from uuid import UUID, uuid4

import httpx
import pendulum
import swapper
import xmltodict
from celery import shared_task
from django.db import models
from django.utils import timezone
from pytimeparse.timeparse import timeparse
from rest_framework import serializers
from rest_framework.renderers import BaseRenderer

from . import models as webhook_models
from .config import conf
from .serializers import WebhookEventSerializer

if TYPE_CHECKING:
    from .utils import ModelSerializerWebhook

logger = logging.getLogger(__name__)


Webhook: webhook_models.AbstractWebhook = swapper.load_model("webhooks", "Webhook")
WebhookLogEntry: webhook_models.AbstractWebhookLogEntry = swapper.load_model("webhooks", "WebhookLogEntry")


def load_object_from_string(string: str) -> object:
    module_path, class_name = string.rsplit(".", 1)
    return getattr(importlib.import_module(module_path), class_name)


@shared_task
def dispatch_webhook_event(
    webhook_id: str,
    event: str,
    owner_id: int,
    object_id: str | None = None,
    data: None | dict = None,
    json_renderer_class: None | str = None,
    xml_renderer_class: None | str = None,
):
    webhook = Webhook.objects.get(id=webhook_id)
    if data is None:
        data = {}

    event_id = uuid4()
    now = timezone.now()
    serializer = WebhookEventSerializer(
        data={
            'webhook_id': UUID(webhook_id),
            'event_id': event_id,
            'dt_dispatched': now,
            'owner_id': owner_id,
            'event': event,
            'object_id': object_id,
            'payload': data,
        }
    )
    serializer.is_valid(raise_exception=True)

    content_type = webhook.target_content_type
    content_type_renderer_map = {
        'application/json': load_object_from_string(json_renderer_class or conf.DEFAULT_JSON_RENDERER_CLASS),
        'application/xml': load_object_from_string(xml_renderer_class or conf.DEFAULT_XML_RENDERER_CLASS),
    }

    renderer: BaseRenderer = content_type_renderer_map[content_type]()
    req_content = renderer.render(serializer.data)

    headers = {
        **webhook.target_headers,
        'Content-Type': webhook.target_content_type,
    }

    log_entry = WebhookLogEntry.objects.create(
        id=event_id,
        webhook_id=webhook_id,
        owner_id=owner_id,  # FIXME: should be a configurable field name
        event=event,
        req_dt=now,
        req_url=webhook.target_url,
        req_method=webhook.target_method,
        req_headers=headers,
        req_data=serializer.data,
        req_content=req_content,
    )

    try:
        res: httpx.Response = getattr(httpx, webhook.target_method)(
            url=webhook.target_url,
            headers=headers,
            content=req_content,
        )
        res.raise_for_status()

    except httpx.HTTPStatusError as e:
        # The only exception that has a response
        log_entry.error_code = "HTTPStatusError"
        log_entry.error_message = str(e)

    except (httpx.HTTPError, httpx.InvalidURL) as e:
        # These exceptions happened before getting a response
        log_entry.error_code = e.__class__.__name__
        log_entry.error_message = str(e)
        log_entry.save(update_fields=['error_code', 'error_message'])
        return

    log_entry.res_dt = timezone.now()
    log_entry.res_status = res.status_code
    log_entry.res_headers = dict(res.headers.items())
    log_entry.res_content = res.text

    res_content_type = res.headers.get("Content-Type", "")
    if 'application/json' in res_content_type:
        with suppress(ValueError):
            log_entry.data = res.json()

    elif 'application/xml' in res_content_type or 'text/xml' in res_content_type:
        with suppress(Exception):
            log_entry.data = xmltodict.parse(res.text)

    log_entry.save()
    return res


@shared_task
def dispatch_serializer_webhook_event(
    webhook_id: str,
    event: str,
    owner_id: int,
    instance_id: int | str,
    serializer_class_module: str | None,
    json_renderer_class: None | str = None,
    xml_renderer_class: None | str = None,
):
    data = None

    if serializer_class_module:
        serializer_class: Type[serializers.ModelSerializer] = load_object_from_string(serializer_class_module)

        model_class: Type[models.Model] = serializer_class.Meta.model
        try:
            instance = model_class.objects.get(pk=instance_id)
        except model_class.DoesNotExist:
            logger.warning(f"Webhook task for {repr(instance)} failed. Instance no longer exists in database")
            return

        data = serializer_class(instance=instance).data

    return dispatch_webhook_event(
        webhook_id,
        event,
        owner_id,
        str(instance_id),
        data,
        json_renderer_class,
        xml_renderer_class,
    )


@shared_task
def auto_clean_log():
    log_retention = conf.get("LOG_RETENTION")
    if not log_retention:
        return
    log_retention = timeparse(log_retention, "minutes")
    cutoff_dt = pendulum.now().subtract(minutes=log_retention)
    WebhookLogEntry.objects.filter(req_dt__lt=cutoff_dt).delete()
