# SPDX-License-Identifier: Apache-2.0

from importlib import import_module
from typing import Any

from dream.extensions.errors import ExtensionLoadError


def load_class(class_path: str) -> type[Any]:
    """Load a class from ``package.module:ClassName`` config syntax."""
    module_name, separator, class_name = class_path.partition(":")
    if not separator or not module_name or not class_name:
        raise ExtensionLoadError(
            "Plugin class_path must use 'package.module:ClassName' syntax."
        )
    try:
        module = import_module(module_name)
    except Exception as exc:
        raise ExtensionLoadError(f"Could not import plugin module '{module_name}'.") from exc
    try:
        loaded = getattr(module, class_name)
    except AttributeError as exc:
        raise ExtensionLoadError(
            f"Plugin class '{class_name}' was not found in module '{module_name}'."
        ) from exc
    if not isinstance(loaded, type):
        raise ExtensionLoadError(f"Plugin target is not a class: {class_path}")
    return loaded


def load_instance(class_path: str, **kwargs: Any) -> Any:
    """Instantiate a configured plugin class."""
    plugin_class = load_class(class_path)
    try:
        return plugin_class(**kwargs)
    except TypeError:
        if kwargs:
            return plugin_class()
        raise
