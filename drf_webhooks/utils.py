import importlib


def load_object_from_string(string: str) -> object:
    module_path, class_name = string.rsplit(".", 1)
    return getattr(importlib.import_module(module_path), class_name)
