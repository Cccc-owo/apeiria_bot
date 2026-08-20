from __future__ import annotations

from nonebot import get_plugin_config
from pydantic import BaseModel, ConfigDict, Field


class TriggerReplyConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    enabled: bool = Field(
        default=True,
        alias="trigger_reply__enabled",
        description="是否启用触发回复",
    )
    rules_file: str = Field(default="rules", description="规则文件路径或规则目录")
    debug: bool = Field(default=False, description="启用调试日志")


def get_trigger_reply_config() -> TriggerReplyConfig:
    return get_plugin_config(TriggerReplyConfig)
