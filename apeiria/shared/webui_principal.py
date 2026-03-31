"""Shared Web UI principal model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WebUIPrincipal:
    """Authenticated Web UI principal."""

    user_id: str
    username: str
    role: str
    capabilities: list[str] = field(default_factory=list)
