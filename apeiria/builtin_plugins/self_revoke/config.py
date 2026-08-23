"""Configuration models for the self-revoke plugin.

This module defines the runtime configuration used by the self-revoke plugin
and the helper that loads it.
"""

from __future__ import annotations

from typing import Literal

from nonebot import get_plugin_config
from pydantic import BaseModel, ConfigDict, Field

SelfRevokePermission = Literal["public", "superuser"]
SelfRevokeFeedback = Literal["silent", "reaction"]


class SelfRevokeConfig(BaseModel):
    """Runtime configuration for the self-revoke plugin.

    This model groups the settings that control who may trigger a revoke,
    whether the trigger message itself is also revoked, and how the plugin
    gives feedback to the user.
    """

    model_config = ConfigDict(extra="ignore")

    permission: SelfRevokePermission = Field(
        default="public", description="撤回权限：public=所有人，superuser=仅超管"
    )
    revoke_trigger_message: bool = Field(
        default=False, description="是否同时撤回触发消息本身"
    )
    feedback: SelfRevokeFeedback = Field(
        default="silent", description="操作反馈方式：silent=静默，reaction=表情反应"
    )


def get_self_revoke_config() -> SelfRevokeConfig:
    """Return the self-revoke plugin configuration.

    Returns:
        The validated :class:`SelfRevokeConfig` instance for the plugin.
    """
    return get_plugin_config(SelfRevokeConfig)
