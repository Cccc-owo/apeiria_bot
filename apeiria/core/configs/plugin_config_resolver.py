from __future__ import annotations

import pkgutil
from dataclasses import dataclass
from pathlib import Path

import nonebot

from apeiria.runtime import FRAMEWORK_BUILTIN_PLUGIN_NAMES, FRAMEWORK_PLUGIN_MODULES
from apeiria.user_config import (
    read_project_plugin_module_map,
    read_pyproject_nonebot_config,
)
from apeiria.user_plugins import read_project_plugin_config

from .models import PluginExtraData, RegisterConfig
from .registry import (
    PluginConfigRegistration,
    RegisterPluginConfigOptions,
    get_registered_plugin_config,
    register_plugin_config,
)
from .static_scan import scan_plugin_config, scan_plugin_config_from_origin


@dataclass(frozen=True)
class PluginScanCandidate:
    module_name: str
    origin: Path | None = None


@dataclass(frozen=True)
class ResolvedPluginConfig:
    section: str
    legacy_flatten: bool
    source: str
    has_config_model: bool
    configs: list[RegisterConfig]


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def _resolve_plugin_dir(path: str) -> Path:
    plugin_dir = Path(path).expanduser()
    if plugin_dir.is_absolute():
        return plugin_dir.resolve()
    return (_project_root() / plugin_dir).resolve()


def _discover_plugin_dir_modules(paths: list[str]) -> list[PluginScanCandidate]:
    discovered: dict[str, PluginScanCandidate] = {}
    for raw_path in paths:
        plugin_dir = _resolve_plugin_dir(raw_path)
        if not plugin_dir.is_dir():
            continue
        for module_info in pkgutil.iter_modules([str(plugin_dir)]):
            if module_info.name.startswith("_"):
                continue
            module_spec = module_info.module_finder.find_spec(module_info.name, None)
            if module_spec is None or not module_spec.origin:
                continue
            discovered.setdefault(
                module_info.name,
                PluginScanCandidate(
                    module_name=module_info.name,
                    origin=Path(module_spec.origin),
                ),
            )
    return sorted(discovered.values(), key=lambda item: item.module_name)


def _iter_explicit_plugin_modules(
    *,
    project_config_path: Path | None = None,
    plugin_config_path: Path | None = None,
    pyproject_path: Path | None = None,
) -> tuple[list[str], list[str]]:
    config = read_project_plugin_config(plugin_config_path)
    pyproject_config = read_pyproject_nonebot_config(pyproject_path)
    persisted_module_map = read_project_plugin_module_map(project_config_path)
    pyproject_modules = pyproject_config["plugins"]
    pyproject_dirs = pyproject_config["plugin_dirs"]

    module_names = [
        *FRAMEWORK_PLUGIN_MODULES,
        *FRAMEWORK_BUILTIN_PLUGIN_NAMES,
        *config["modules"],
        *persisted_module_map.values(),
        *pyproject_modules,
    ]
    plugin_dirs = [*config["dirs"], *pyproject_dirs]
    return module_names, plugin_dirs


def collect_plugin_config_candidates(
    *,
    project_config_path: Path | None = None,
    plugin_config_path: Path | None = None,
    pyproject_path: Path | None = None,
) -> list[PluginScanCandidate]:
    module_names, plugin_dirs = _iter_explicit_plugin_modules(
        project_config_path=project_config_path,
        plugin_config_path=plugin_config_path,
        pyproject_path=pyproject_path,
    )

    candidates: dict[str, PluginScanCandidate] = {}
    for module_name in module_names:
        if module_name:
            candidates.setdefault(module_name, PluginScanCandidate(module_name))

    for candidate in _discover_plugin_dir_modules(plugin_dirs):
        candidates.setdefault(candidate.module_name, candidate)

    return sorted(candidates.values(), key=lambda item: item.module_name)


def _resolved_from_registration(
    registration: PluginConfigRegistration,
) -> ResolvedPluginConfig:
    return ResolvedPluginConfig(
        section=registration.section,
        legacy_flatten=registration.legacy_flatten,
        source=registration.source,
        has_config_model=bool(registration.configs),
        configs=list(registration.configs),
    )


def ensure_plugin_config_registration(
    candidate: PluginScanCandidate,
) -> ResolvedPluginConfig:
    plugin_name = candidate.module_name
    registration = get_registered_plugin_config(plugin_name)
    if registration is not None:
        return _resolved_from_registration(registration)

    scanned = (
        scan_plugin_config_from_origin(plugin_name, candidate.origin)
        if candidate.origin is not None
        else scan_plugin_config(plugin_name)
    )
    if scanned.is_apeiria_plugin or not scanned.has_config_model:
        return ResolvedPluginConfig(
            section=plugin_name.rsplit(".", maxsplit=1)[-1],
            legacy_flatten=False,
            source="none",
            has_config_model=False,
            configs=[],
        )

    registration = register_plugin_config(
        plugin_name,
        options=RegisterPluginConfigOptions(
            section=scanned.section,
            configs=scanned.configs,
            legacy_flatten=True,
            source="static_scan",
        ),
    )
    return _resolved_from_registration(registration)


def resolve_plugin_declared_config(module_name: str) -> ResolvedPluginConfig:
    registration = get_registered_plugin_config(module_name)
    if registration is not None:
        return _resolved_from_registration(registration)

    plugin = next(
        (
            item
            for item in nonebot.get_loaded_plugins()
            if item.module_name == module_name
        ),
        None,
    )
    if plugin and plugin.metadata and plugin.metadata.extra:
        extra = PluginExtraData.from_extra(plugin.metadata.extra)
        if extra is not None:
            return ResolvedPluginConfig(
                section=module_name.rsplit(".", maxsplit=1)[-1],
                legacy_flatten=False,
                source="plugin_metadata",
                has_config_model=bool(extra.configs),
                configs=extra.configs,
            )

    return ensure_plugin_config_registration(PluginScanCandidate(module_name))
