"""Shared Web UI role constants and capability helpers."""

from __future__ import annotations

from typing import Final

ROLE_OWNER: Final = "owner"
CAP_CONTROL_PANEL: Final = "control_panel"
CAP_ACCOUNT_MANAGE: Final = "account_manage"
ROLE_CAPABILITIES: Final[dict[str, tuple[str, ...]]] = {
    ROLE_OWNER: (CAP_CONTROL_PANEL, CAP_ACCOUNT_MANAGE),
}
SUPPORTED_ASSIGNABLE_ROLES: Final[frozenset[str]] = frozenset(ROLE_CAPABILITIES)


def normalize_role(role: object) -> str:
    """Normalize persisted/user-provided role names."""
    if not isinstance(role, str):
        return ""
    return role.strip().lower()


def normalize_supported_role(role: object, *, fallback: str = "") -> str:
    """Normalize one role and reject unsupported values."""
    normalized = normalize_role(role)
    if normalized in ROLE_CAPABILITIES:
        return normalized
    return fallback


def capabilities_for_role(role: object) -> list[str]:
    """Return control-panel capabilities for one role."""
    normalized = normalize_supported_role(role)
    return list(ROLE_CAPABILITIES.get(normalized, ()))


def has_capability(role: object, capability: str) -> bool:
    """Return whether one role has the requested capability."""
    normalized = normalize_supported_role(role)
    return capability in ROLE_CAPABILITIES.get(normalized, ())


def can_access_control_panel(role: object) -> bool:
    """Return whether one role may enter the control panel."""
    return has_capability(role, CAP_CONTROL_PANEL)


def can_manage_accounts(role: object) -> bool:
    """Return whether one role may manage Web UI accounts."""
    return has_capability(role, CAP_ACCOUNT_MANAGE)
