from django import forms
from django.contrib import admin

from .config import REGISTERED_WEBHOOK_CHOICES, conf


class EventsChoiceWidget(forms.CheckboxSelectMultiple):
    @property
    def choices(self):
        return list(REGISTERED_WEBHOOK_CHOICES.items())

    @choices.setter
    def choices(self, v):
        pass


class AbstractWebhookAdminForm(forms.ModelForm):
    class Meta:
        model = conf.WEBHOOK_MODEL
        widgets = {
            'events': EventsChoiceWidget,
        }
        fields = '__all__'


class AbstractWebhookAdmin(admin.ModelAdmin):
    form = AbstractWebhookAdminForm


class AbstractWebhookLogEntryAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
