from apeiria.core.configs.plugin_config_resolver import (
    PluginScanCandidate,
    collect_plugin_config_candidates,
    ensure_plugin_config_registration,
)
from apeiria.core.configs.registry import PluginConfigConflictError


def _register_candidate(candidate: PluginScanCandidate) -> None:
    try:
        ensure_plugin_config_registration(candidate)
    except PluginConfigConflictError as exc:
        msg = (
            "failed to bootstrap plugin config for "
            f"{candidate.module_name}: {exc}"
        )
        raise RuntimeError(msg) from exc


def bootstrap_plugin_configs() -> None:
    for candidate in collect_plugin_config_candidates():
        _register_candidate(candidate)
