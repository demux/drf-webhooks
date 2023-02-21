import importlib

import swapper
from django import forms
from django.contrib import admin

from . import models as webhook_models
from .config import REGISTERED_WEBHOOK_CHOICES, conf

Webhook: webhook_models.AbstractWebhook = swapper.load_model("webhooks", "Webhook")
WebhookLogEntry: webhook_models.AbstractWebhookLogEntry = swapper.load_model("webhooks", "WebhookLogEntry")


class EventsChoiceWidget(forms.CheckboxSelectMultiple):
    @property
    def choices(self):
        return list(REGISTERED_WEBHOOK_CHOICES.items())

    @choices.setter
    def choices(self, v):
        pass


class AbstractWebhookAdminForm(forms.ModelForm):
    class Meta:
        model = Webhook
        widgets = {
            'events': EventsChoiceWidget,
        }
        fields = '__all__'


class AbstractWebhookAdmin(admin.ModelAdmin):
    form = AbstractWebhookAdminForm


class WebhookAdmin(AbstractWebhookAdmin):
    raw_id_fields = ["owner"]


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
