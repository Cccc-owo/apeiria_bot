"""Utilities for reading the bot's configured superusers."""

from __future__ import annotations

from nonebot import get_driver


def get_superuser_set() -> set[str]:
    """Return the set of configured superuser IDs.

    Returns:
        The set of superuser IDs from the driver config.
    """
    return set(get_driver().config.superusers)
