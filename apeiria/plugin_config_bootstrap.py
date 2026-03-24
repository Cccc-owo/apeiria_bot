from apeiria.core.configs.plugin_config_resolver import (
    collect_plugin_config_candidates,
    ensure_plugin_config_registration,
)


def bootstrap_plugin_configs() -> None:
    for candidate in collect_plugin_config_candidates():
        ensure_plugin_config_registration(candidate)
