import logging
from collections import defaultdict, deque
from functools import reduce
from operator import __or__
from typing import (
    Callable,
    DefaultDict,
    Hashable,
    Literal,
    NamedTuple,
    Type,
    TypedDict,
)

from django.db import models
from inflection import underscore
from rest_framework import serializers
from rest_framework.renderers import BaseRenderer

from drf_webhooks.utils import get_serializer_query_names

from .config import REGISTERED_WEBHOOK_CHOICES, conf
from .tasks import dispatch_serializer_webhook_event

logger = logging.getLogger(__name__)

WebhookCUD = Literal["created", "updated", "deleted"]


class Signal(NamedTuple):
    instance: models.Model
    pk: Hashable
    cud: WebhookCUD


class Store(TypedDict):
    disable_webhooks: bool
    model_serializer_webhook_instances: dict[Type[serializers.ModelSerializer], "ModelSerializerWebhook"]
    model_serializer_webhook_base_names: set[str]


SignalModelInstanceBaseMap = dict[
    Type[models.Model],
    Callable[[models.Model], models.Q],
]

_STORE: Store = {
    "disable_webhooks": False,
    "model_serializer_webhook_instances": {},
    "model_serializer_webhook_base_names": set(),
}


class ModelSerializerWebhook:
    serializer_class: Type[serializers.ModelSerializer]
    json_renderer_class: Type[BaseRenderer] | None = None
    xml_renderer_class: Type[BaseRenderer] | None = None
    base_name: str = ''

    create: bool = True
    update: bool = True
    delete: bool = True

    signal_model_instance_base_getters: SignalModelInstanceBaseMap = {}

    def __init__(self, serializer_class: Type[serializers.ModelSerializer]):
        self.serializer_class = serializer_class
        model: Type[models.Model] = self.serializer_class.Meta.model
        self.model = model

        if not self.base_name:
            self.base_name = underscore(model.__name__)

        self.nested_serializers = tuple(self._find_nested_model_serializers(self.serializer_class(), []))
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

    def _register_all_choices(self):
        if self.create:
            self._register_choice('created')
        if self.update:
            self._register_choice('updated')
        if self.delete:
            self._register_choice('deleted')

    def _register_choice(self, name: WebhookCUD):
        REGISTERED_WEBHOOK_CHOICES[f'{self.base_name}.{name}'] = "%s %s" % (
            self.model._meta.verbose_name.title(),  # type: ignore
            name.title(),
        )

    @property
    def instance(self):
        return _STORE["model_serializer_webhook_instances"][self.serializer_class]

    @property
    def serializer_module_path(self):
        return f"{self.serializer_class.__module__}.{self.serializer_class.__name__}"

    def get_owner(self, instance: models.Model) -> models.Model:
        return getattr(instance, conf.OWNER_FIELD)

    def get_signal_model_instance_base_getters(self) -> SignalModelInstanceBaseMap:
        getters = self._generate_signal_model_instance_base_getters()
        getters.update(self.signal_model_instance_base_getters)
        return getters

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

        webhook_ids = conf.WEBHOOK_MODEL.objects.filter(
            **{conf.OWNER_FIELD: owner.pk},
            events__contains=[event],
        ).values_list('id', flat=True)

        tasks = []
        for webhook_id in webhook_ids:
            task = dispatch_serializer_webhook_event.apply_async(
                args=(
                    str(webhook_id),
                    event,
                    owner.pk,
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
    def _find_nested_model_serializers(cls, serializer: serializers.ModelSerializer, path: list[str]):
        for key, field in serializer.fields.items():
            if isinstance(field, serializers.ListSerializer):
                field = field.child
            if isinstance(field, serializers.ModelSerializer):
                yield (field.Meta.model, field, (*path, key))
                yield from cls._find_nested_model_serializers(field, [*path, key])

    @staticmethod
    def _base_getter_factory(q: set[str]):
        def _fn(instance: models.Model):
            return reduce(
                __or__,
                [models.Q(**{query_str: instance}) for query_str in q],
            )

        return _fn

    def _generate_signal_model_instance_base_getters(self) -> SignalModelInstanceBaseMap:
        queries: DefaultDict[Type[models.Model], set[str]] = defaultdict(set)

        for m, qname in get_serializer_query_names(self.serializer_class()):
            queries[m].add(qname)

        return {m: self._base_getter_factory(q) for m, q in queries.items()}

    def _exec(self, signals: deque[Signal]):
        created = set()
        deleted = set()
        latest_instances: dict[Hashable, models.Model] = {}

        base_getters = self.get_signal_model_instance_base_getters()

        queries: list[models.Q] = []

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
                getter = base_getters[signal.instance.__class__]
            except KeyError:
                pass
            else:
                queries.append(getter(signal.instance))

        if queries:
            queryset = self.model.objects.filter(reduce(__or__, queries))
            for inst in queryset:
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


def register_webhook(serializer_class: Type[serializers.ModelSerializer]):
    def fn(webhook_class: Type[ModelSerializerWebhook] | None = None):
        instances = _STORE["model_serializer_webhook_instances"]
        base_names = _STORE["model_serializer_webhook_base_names"]

        if webhook_class:
            msw = webhook_class(serializer_class)
        else:
            msw = ModelSerializerWebhook(serializer_class)

        if msw.serializer_class in instances.keys():
            raise RuntimeError(f'ModelSerializerWebhook for "{serializer_class.__name__}" already registered')

        if msw.base_name in base_names:
            raise RuntimeError(f'ModelSerializerWebhook with base_name="{msw.base_name}" already registered')

        msw._register_all_choices()
        instances[msw.serializer_class] = msw
        base_names.add(msw.base_name)

        return msw

    return fn


def unregister_webhook(serializer_class: Type[serializers.ModelSerializer]):
    try:
        msw = _STORE["model_serializer_webhook_instances"][serializer_class]
    except KeyError:
        return False

    del _STORE["model_serializer_webhook_instances"][serializer_class]
    _STORE["model_serializer_webhook_base_names"].remove(msw.base_name)

    return True
