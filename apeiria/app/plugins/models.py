"""Shared plugin application models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PluginUninstallResult:
    """Result of one plugin uninstall operation."""

    requirement: str
    module_names: list[str]
