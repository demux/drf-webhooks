import importlib
from typing import Generator, Type

from django.db import models
from django.db.models.fields.reverse_related import ForeignObjectRel
from rest_framework import serializers


def load_object_from_string(string: str) -> object:
    module_path, class_name = string.rsplit(".", 1)
    return getattr(importlib.import_module(module_path), class_name)


def get_serializer_query_names(
    serializer: serializers.ModelSerializer,
    path: list[str] | None = None,
) -> Generator[tuple[str, Type[models.Model]], None, None]:
    model: models.Model = getattr(serializer.Meta, 'model')
    model_field_map = {
        (f.get_accessor_name() if hasattr(f, "get_accessor_name") else f.name): f for f in model._meta.get_fields()
    }

    for field_name, field in serializer.fields.items():
        source: str = field.source or field_name

        if '.' in source or source == '*':
            # TODO: If a field is referenced on a related model (one2one or foreignkey),
            #       we should trigger a sync if that model changes also.
            continue

        if not isinstance(field, (serializers.ListSerializer, serializers.ModelSerializer)):
            continue

        next_serializer = field
        if isinstance(field, serializers.ListSerializer):
            next_serializer = field.child

        field_model: Type[models.Model] = next_serializer.Meta.model

        model_field = model_field_map[source]
        if isinstance(model_field, ForeignObjectRel):
            source = model_field.related_query_name or model_field.name

        new_path = [*(path or []), source]

        yield (field_model, '__'.join(new_path))

        yield from get_serializer_query_names(next_serializer, new_path)
