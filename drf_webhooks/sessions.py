from collections import deque
from contextlib import contextmanager

from django.db import models

from drf_webhooks.main import _STORE, Signal, WebhookCUD


class WebhookSignalSession:
    """
    Collect all signals in a session and send them to ModelSerializerWebhook instances
    to minimize the number of webhook events
    """

    def __init__(self):
        self._signals: deque[Signal] = deque()
        models.signals.post_save.connect(self._post_save)
        models.signals.m2m_changed.connect(self._m2m_changed)
        models.signals.pre_delete.connect(self._pre_delete)

    def _post_save(self, sender, instance: models.Model, created: bool, **kwargs):
        if _STORE['disable_webhooks']:
            return
        if created:
            self.created(instance)
        else:
            self.updated(instance)

    def _pre_delete(self, sender, instance: models.Model, **kwargs):
        if _STORE['disable_webhooks']:
            return
        self.deleted(instance)

    def _collect(self, instance: models.Model, cud: WebhookCUD):
        self._signals.append(Signal(instance, instance.pk, cud))

    def created(self, instance: models.Model):
        self._collect(instance, "created")

    def updated(self, instance: models.Model):
        self._collect(instance, "updated")

    def _m2m_changed(self, sender, instance: models.Model, action: str, **kwargs):
        if action.startswith("post_"):  # post_add, post_remove, post_clear
            self.updated(instance)

    def deleted(self, instance: models.Model):
        self._collect(instance, "deleted")

        # This has be get done while these objects still exist:
        for msw in _STORE["model_serializer_webhook_instances"].values():
            if isinstance(instance, msw.model):
                instance._cached_owner = msw.get_owner(instance)

            base_getters = msw.get_signal_model_instance_base_getters()
            try:
                base_instances = base_getters[msw.instance.__class__](msw.instance)
            except KeyError:
                continue
            for inst in base_instances:
                self.updated(inst)

    def close(self):
        for swh in _STORE["model_serializer_webhook_instances"].values():
            swh._exec(self._signals)
        # Clear
        self._signals = deque()


@contextmanager
def webhook_signal_session():
    _session = WebhookSignalSession()
    try:
        yield _session
    finally:
        _session.close()


@contextmanager
def disable_webhooks(instance, signals):
    """
    Used to disable webhooks, for example, while importing large data sets
    """
    try:
        _STORE['disable_webhooks'] = True
        yield
    finally:
        _STORE['disable_webhooks'] = False
