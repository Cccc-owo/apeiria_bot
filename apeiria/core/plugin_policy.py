from __future__ import annotations

from functools import lru_cache

from apeiria.runtime_framework import get_framework_dependency_plugin_modules

ALWAYS_PROTECTED_PLUGIN_MODULES = frozenset({"apeiria.plugins.web_ui"})


@lru_cache(maxsize=1)
def framework_dependency_plugin_modules() -> frozenset[str]:
    return get_framework_dependency_plugin_modules()


def is_framework_dependency_plugin_module(module_name: str) -> bool:
    return module_name in framework_dependency_plugin_modules()


def is_protected_plugin_module(module_name: str) -> bool:
    return (
        module_name in ALWAYS_PROTECTED_PLUGIN_MODULES
        or is_framework_dependency_plugin_module(module_name)
    )
