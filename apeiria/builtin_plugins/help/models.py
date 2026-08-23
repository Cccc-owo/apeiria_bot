"""Data models for the help plugin."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class HelpCommandItem:
    """Data describing a single command exposed by a plugin.

    Holds the command name, aliases, description, usage, and whether the
    command is restricted to superusers only.
    """

    name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    usage: str = ""
    admin_only: bool = False


@dataclass(slots=True)
class HelpPluginItem:
    """Data describing a plugin and its commands for the help view.

    Collects the plugin identity, metadata, source, and the command items
    that are shown to the user.
    """

    plugin_id: str
    module_name: str
    name: str
    description: str = ""
    usage: str = ""
    plugin_type: str = "application"
    source: str = "user"
    icon_url: str = ""
    commands: list[HelpCommandItem] = field(default_factory=list)

    @property
    def command_count(self) -> int:
        """Return the number of commands exposed by the plugin."""
        return len(self.commands)

    @property
    def is_builtin(self) -> bool:
        """Return whether the plugin is a built-in plugin."""
        return self.source == "builtin"
