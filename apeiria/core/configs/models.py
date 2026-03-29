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
    type: object = str
    choices: list[Any] = field(default_factory=list)
    item_type: object | None = None
    key_type: object | None = None
    allows_null: bool = False
    fields: list["RegisterConfig"] = field(default_factory=list)
    item_schema: "RegisterConfig | None" = None
    key_schema: "RegisterConfig | None" = None
    value_schema: "RegisterConfig | None" = None


@dataclass
class CommandDeclaration:
    """Declares one command help entry for plugin metadata."""

    name: str
    description: str = ""
    usage: str = ""
    aliases: list[str] = field(default_factory=list)
    custom_prefix: str | None = None


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
    commands: list[str | CommandDeclaration] = field(default_factory=list)
    configs: list[RegisterConfig] = field(default_factory=list)
    required_plugins: list[str] = field(default_factory=list)

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
                _coerce_register_config(c) if isinstance(c, dict) else c
                for c in configs_raw
            ]
            commands_raw = extra.get("commands", [])
            commands = [
                _coerce_command_declaration(item) if isinstance(item, dict) else item
                for item in commands_raw
            ]

            return cls(
                author=extra.get("author", "unknown"),
                version=extra.get("version", "0.0.0"),
                plugin_type=plugin_type,
                admin_level=extra.get("admin_level", 0),
                commands=commands,
                configs=configs,
                required_plugins=extra.get("required_plugins", []),
            )
        except (ValueError, TypeError, KeyError):
            return None


def _coerce_register_config(raw: dict[str, Any]) -> RegisterConfig:
    fields = [
        _coerce_register_config(item)
        for item in raw.get("fields", [])
        if isinstance(item, dict)
    ]
    item_schema = raw.get("item_schema")
    key_schema = raw.get("key_schema")
    value_schema = raw.get("value_schema")
    return RegisterConfig(
        key=str(raw.get("key", "")),
        default=raw.get("default"),
        help=str(raw.get("help", "")),
        type=raw.get("type", str),
        choices=list(raw.get("choices", [])),
        item_type=raw.get("item_type"),
        key_type=raw.get("key_type"),
        allows_null=bool(raw.get("allows_null", False)),
        fields=fields,
        item_schema=(
            _coerce_register_config(item_schema)
            if isinstance(item_schema, dict)
            else None
        ),
        key_schema=(
            _coerce_register_config(key_schema)
            if isinstance(key_schema, dict)
            else None
        ),
        value_schema=(
            _coerce_register_config(value_schema)
            if isinstance(value_schema, dict)
            else None
        ),
    )


def _coerce_command_declaration(raw: dict[str, Any]) -> CommandDeclaration:
    return CommandDeclaration(
        name=str(raw.get("name", "")),
        description=str(raw.get("description", "")),
        usage=str(raw.get("usage", "")),
        aliases=[
            str(item)
            for item in raw.get("aliases", [])
            if isinstance(item, str) and item.strip()
        ],
        custom_prefix=(
            str(raw.get("custom_prefix"))
            if isinstance(raw.get("custom_prefix"), str) and raw.get("custom_prefix")
            else None
        ),
    )
