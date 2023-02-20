import importlib

import swapper
from django.contrib import admin

from . import models as webhook_models
from .config import conf

Webhook: webhook_models.AbstractWebhook = swapper.load_model("webhooks", "Webhook")
WebhookLogEntry: webhook_models.AbstractWebhookLogEntry = swapper.load_model("webhooks", "WebhookLogEntry")


class AbstractWebhookAdmin(admin.ModelAdmin):
    pass


class WebhookAdmin(AbstractWebhookAdmin):
    pass


class AbstractWebhookLogEntryAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class WebhookLogEntryAdmin(AbstractWebhookLogEntryAdmin):
    pass


# FIXME: duplicate code
def load_object_from_string(string: str | None) -> object:
    if not string:
        return
    module_path, class_name = string.rsplit(".", 1)
    return getattr(importlib.import_module(module_path), class_name)


if conf.REGISTER_ADMIN:
    admin.site.register(
        Webhook,
        load_object_from_string(conf.WEBHOOK_ADMIN_CLASS) or WebhookAdmin,
    )
    admin.site.register(
        WebhookLogEntry,
        load_object_from_string(conf.WEBHOOK_LOG_ADMIN_CLASS) or WebhookLogEntryAdmin,
    )
