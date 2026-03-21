"""Plugin metadata types and configuration models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class PluginType(str, Enum):
    """Plugin type classification."""

    NORMAL = "normal"
    ADMIN = "admin"
    SUPERUSER = "superuser"
    HIDDEN = "hidden"
    PARENT = "parent"


@dataclass
class RegisterConfig:
    """Declares a plugin configuration item."""

    key: str
    default: Any
    help: str = ""
    type: type = str


@dataclass
class PluginExtraData:
    """Extended metadata for apeiria plugins.

    Stored in PluginMetadata.extra via .to_dict().
    Third-party plugins without this format are handled via graceful degradation.
    """

    author: str = "apeiria"
    version: str = "0.1.0"
    plugin_type: PluginType = PluginType.NORMAL
    admin_level: int = 0
    commands: list[str] = field(default_factory=list)
    configs: list[RegisterConfig] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for PluginMetadata.extra."""
        data = asdict(self)
        data["plugin_type"] = self.plugin_type.value
        data["_apeiria"] = True  # Marker for identification
        return data

    @classmethod
    def from_extra(cls, extra: dict[str, Any]) -> PluginExtraData | None:
        """Try to parse from PluginMetadata.extra.

        Returns None if not our format (third-party plugin).
        """
        if not extra.get("_apeiria"):
            return None
        try:
            plugin_type = extra.get("plugin_type", "normal")
            if isinstance(plugin_type, str):
                plugin_type = PluginType(plugin_type)

            configs_raw = extra.get("configs", [])
            configs = [
                RegisterConfig(**c) if isinstance(c, dict) else c for c in configs_raw
            ]

            return cls(
                author=extra.get("author", "unknown"),
                version=extra.get("version", "0.0.0"),
                plugin_type=plugin_type,
                admin_level=extra.get("admin_level", 0),
                commands=extra.get("commands", []),
                configs=configs,
            )
        except (ValueError, TypeError, KeyError):
            return None
