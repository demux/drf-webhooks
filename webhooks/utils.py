import logging
from collections import deque
from contextlib import contextmanager
from typing import (
    Callable,
    Hashable,
    Iterable,
    Literal,
    NamedTuple,
    Type,
    TypedDict,
)

import swapper
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from inflection import underscore
from rest_framework import serializers
from rest_framework.renderers import BaseRenderer

from . import models as webhook_models
from .config import REGISTERED_WEBHOOK_CHOICES, conf
from .tasks import dispatch_serializer_webhook_event

logger = logging.getLogger(__name__)

WebhookCUD = Literal["created", "updated", "deleted"]

Webhook: webhook_models.AbstractWebhook = swapper.load_model("webhooks", "Webhook")


class Signal(NamedTuple):
    instance: models.Model
    pk: Hashable
    cud: WebhookCUD


class Store(TypedDict):
    disable_webhooks: bool
    model_serializer_webhook_instances: dict[str, "ModelSerializerWebhook"]
    model_serializer_webhook_base_names: set[str]
    model_serializer_webhook_serializers: set[serializers.ModelSerializer]


_STORE: Store = {
    "disable_webhooks": False,
    "model_serializer_webhook_instances": {},
    "model_serializer_webhook_base_names": set(),
    "model_serializer_webhook_serializers": set(),
}


class ModelSerializerWebhookMeta(type):
    def __init__(cls, name, bases, clsdict):
        super().__init__(name, bases, clsdict)

        if len(cls.mro()) > 2:
            msw: ModelSerializerWebhook = cls()

            instances = _STORE["model_serializer_webhook_instances"]
            base_names = _STORE["model_serializer_webhook_base_names"]
            _serialisers = _STORE["model_serializer_webhook_serializers"]

            if msw.base_name in base_names:
                raise RuntimeError(f'ModelSerializerWebhook with base_name "{msw.base_name}" already defined')

            if msw.serializer_class in _serialisers:
                raise RuntimeError(f'ModelSerializerWebhook for "{msw.serializer_class.__name__}" already defined')

            instances[cls] = msw
            base_names.add(msw.base_name)
            _serialisers.add(msw.serializer_class)


SignalModelInstanceBaseMap = dict[
    models.Model,
    Callable[[models.Model], Iterable[models.Model]],
]


class ModelSerializerWebhook(metaclass=ModelSerializerWebhookMeta):
    serializer_class: Type[serializers.ModelSerializer]
    json_renderer_class: Type[BaseRenderer] | None = None
    xml_renderer_class: Type[BaseRenderer] | None = None
    base_name: str = ''

    create: bool = True
    update: bool = True
    delete: bool = True

    signal_model_instance_base_getters: SignalModelInstanceBaseMap = {}

    def __init__(self):
        model: Type[models.Model] = self.serializer_class.Meta.model
        self.model = model

        if not self.base_name:
            self.base_name = underscore(model.__name__)

        self.nested_serializers = tuple(self._find_nested_model_serializers(self.serializer_class(), tuple()))
        self.nested_serializers_map = {m: s for m, s, _ in self.nested_serializers}

        _getters = self.get_signal_model_instance_base_getters()
        _getters_not_implemented = [m for m in self.nested_serializers_map.keys() if m not in _getters]
        if _getters_not_implemented:
            debug_tree = ""
            debug_tree += f"{self.serializer_class.__name__}\n"
            for m, _, p in self.nested_serializers:
                debug_tree += f"  .{'.'.join(p)} -> {m._meta.object_name}\n"

            _errors = [
                f"{self.__class__.__name__}.signal_model_instance_base_getters[{m.__module__}.{m._meta.object_name}]"
                for m in _getters_not_implemented
            ]
            raise NotImplementedError(
                "The following getters must be implemented:\n%s\nSerializer Tree:\n%s"
                % (
                    "\n".join(_errors),
                    debug_tree,
                )
            )

        if self.create:
            self._register('created')
        if self.update:
            self._register('updated')
        if self.delete:
            self._register('deleted')

    @classmethod
    def __del__(cls):
        cls.disconnect()

    @classmethod
    def disconnect(cls):
        try:
            self = cls.instance
        except (KeyError, TypeError):
            return

        del _STORE["model_serializer_webhook_instances"][self.__class__]
        _STORE["model_serializer_webhook_base_names"].remove(self.base_name)
        _STORE["model_serializer_webhook_serializers"].remove(self.serializer_class)

    @classmethod
    @property
    def instance(cls):
        return _STORE["model_serializer_webhook_instances"][cls]

    @property
    def serializer_module_path(self):
        return f"{self.serializer_class.__module__}.{self.serializer_class.__name__}"

    @property
    def own_module_path(self):
        return f'{self.__class__.__module__}.{self.__class__.__name__}'

    def get_owner(self, instance: models.Model) -> models.Model:
        return getattr(instance, conf.OWNER_FIELD)

    def get_signal_model_instance_base_getters(self) -> SignalModelInstanceBaseMap:
        return self.signal_model_instance_base_getters

    def _register(self, name: WebhookCUD):
        REGISTERED_WEBHOOK_CHOICES[f'{self.base_name}.{name}'] = "%s %s" % (
            self.model._meta.verbose_name.title(),
            name.title(),
        )

    def _get_owner(self, instance: models.Model) -> models.Model:
        owner = getattr(instance, "_cached_owner", None)
        if owner:
            return owner
        return self.get_owner(instance)

    def _dispatch(self, instance: models.Model, cud: WebhookCUD):
        event = f'{self.base_name}.{cud}'
        owner = self._get_owner(instance)
        if not owner:
            return

        webhook_ids = Webhook.objects.filter(
            owner_id=owner.id,
            events__contains=[event],
        ).values_list('id', flat=True)

        tasks = []
        for webhook_id in webhook_ids:
            task = dispatch_serializer_webhook_event.apply_async(
                args=(
                    str(webhook_id),
                    event,
                    owner.id,
                    str(instance.pk),
                    self.serializer_module_path if cud != "deleted" else None,
                    self.json_renderer_class,
                    self.xml_renderer_class,
                ),
            )
            tasks.append(task)

        return tasks

    def on_create(self, instance: models.Model):
        return self._dispatch(instance, 'created')

    def on_update(self, instance: models.Model):
        return self._dispatch(instance, 'updated')

    def on_delete(self, instance: models.Model):
        return self._dispatch(instance, 'deleted')

    @classmethod
    def _find_nested_model_serializers(cls, serializer: serializers.ModelSerializer, path: tuple[str]):
        for key, field in serializer.fields.items():
            if isinstance(field, serializers.ListSerializer):
                field = field.child
            if isinstance(field, serializers.ModelSerializer):
                yield (field.Meta.model, field, (*path, key))
                yield from cls._find_nested_model_serializers(field, (*path, key))

    def _exec(self, signals: deque[Signal]):
        created = set()
        deleted = set()
        latest_instances: dict[Hashable, models.Model] = {}

        base_getters = self.get_signal_model_instance_base_getters()

        for signal in signals:
            if signal.instance.__class__ is self.model:
                if signal.cud == "created":
                    created.add(signal.pk)
                elif signal.cud == "deleted":
                    signal.instance.pk = signal.pk
                    deleted.add(signal.pk)

                latest_instances[signal.pk] = signal.instance
                continue

            if signal.cud == "deleted":
                continue

            try:
                base_instances = base_getters[signal.instance.__class__](signal.instance)
            except (KeyError, ValueError, ObjectDoesNotExist):
                pass
            else:
                for inst in base_instances:
                    latest_instances[inst.pk] = inst

        for instance in latest_instances.values():
            if instance.pk in created and instance.pk in deleted:
                # Both created and deleted in the same session.
                # No webhooks sent
                pass
            elif self.delete and instance.pk in deleted:
                self.on_delete(instance)
            elif self.create and instance.pk in created:
                self.on_create(instance)
            elif self.update:
                self.on_update(instance)


@contextmanager
def disable(instance, signals):
    """
    Used to disable webhooks, for example, while importing large data sets
    """
    try:
        _STORE['disable_webhooks'] = True
        yield
    finally:
        _STORE['disable_webhooks'] = False


class WebhookSignalSession:
    """
    Collect all signals in a session and send them to ModelSerializerWebhook instances
    to minimize the number of webhook events
    """

    def __init__(self):
        self._signals: deque[Signal] = deque()
        models.signals.post_save.connect(self._post_save)
        models.signals.pre_delete.connect(self._pre_delete)
        # TODO:
        # models.signals.m2m_changed.connect(self._m2m_changed)

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
