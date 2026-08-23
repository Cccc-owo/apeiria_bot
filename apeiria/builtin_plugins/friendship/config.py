"""Configuration model and accessor for the friendship plugin."""

from __future__ import annotations

from nonebot import get_plugin_config
from pydantic import BaseModel, ConfigDict, Field


class FriendshipConfig(BaseModel):
    """Configuration settings for the friendship request plugin.

    Controls whether request handling is enabled, whether to notify
    superusers of incoming requests, and whether to auto-approve whitelisted
    requests.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    enabled: bool = Field(
        default=True,
        alias="friendship__enabled",
        description="是否启用好友请求通知和处理",
    )
    notify_superusers: bool = Field(default=True, description="是否通知超级用户")
    auto_approve: bool = Field(
        default=False, description="自动通过白名单请求（未实现）"
    )


def get_friendship_config() -> FriendshipConfig:
    """Return the loaded friendship plugin configuration."""
    return get_plugin_config(FriendshipConfig)
