"""Pydantic request/response schemas for Web UI API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from apeiria.domains.chat.protocol import (
    AuthHelloPayload,
    AuthOkPayload,
    CapabilitiesResponsePayload,
    ChatCapabilities,
    ChatEnvelope,
    ChatSegment,
    ChatSessionState,
    EnvelopeVersion,
    ErrorPayload,
    ImageSegment,
    MentionSegment,
    MessageAckPayload,
    MessageReceivePayload,
    MessageSendPayload,
    RawSegment,
    ReplySegment,
    SessionCreatePayload,
    SessionDeletedPayload,
    SessionDeletePayload,
    SessionListItem,
    SessionListPayload,
    SessionStatePayload,
    SessionStatus,
    SessionUpdatePayload,
    SystemMessagePayload,
    TextSegment,
    WebUIPrincipal,
)

__all__ = [
    "AdapterConfigItem",
    "AdapterConfigRequest",
    "AdapterConfigResponse",
    "AuthHelloPayload",
    "AuthOkPayload",
    "BanCreateRequest",
    "BanItem",
    "CapabilitiesResponsePayload",
    "ChatCapabilities",
    "ChatEnvelope",
    "ChatSegment",
    "ChatSessionState",
    "DriverConfigItem",
    "DriverConfigRequest",
    "DriverConfigResponse",
    "EnvelopeVersion",
    "ErrorPayload",
    "GroupItem",
    "ImageSegment",
    "LoginRequest",
    "LoginResponse",
    "MentionSegment",
    "MessageAckPayload",
    "MessageReceivePayload",
    "MessageSendPayload",
    "OperationStatusResponse",
    "PluginConfigDirItem",
    "PluginConfigModuleItem",
    "PluginConfigRequest",
    "PluginConfigResponse",
    "PluginItem",
    "PluginRawSettingsResponse",
    "PluginSettingFieldItem",
    "PluginSettingsRawUpdateRequest",
    "PluginSettingsResponse",
    "PluginSettingsUpdateRequest",
    "RawSegment",
    "ReplySegment",
    "SessionCreatePayload",
    "SessionDeletePayload",
    "SessionDeletedPayload",
    "SessionListItem",
    "SessionListPayload",
    "SessionStatePayload",
    "SessionStatus",
    "SessionUpdatePayload",
    "StatusResponse",
    "SystemMessagePayload",
    "TextSegment",
    "UpdateLevelRequest",
    "UserLevelItem",
    "WebUIPrincipal",
]


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str


class StatusResponse(BaseModel):
    status: str
    uptime: float
    plugins_count: int
    disabled_plugins_count: int
    groups_count: int
    disabled_groups_count: int
    bans_count: int
    adapters: list[str]


class PluginItem(BaseModel):
    module_name: str
    name: str | None
    description: str | None
    source: str
    is_global_enabled: bool
    is_protected: bool = False
    protected_reason: str | None = None


class OperationStatusResponse(BaseModel):
    status: str = "ok"
    detail: str | None = None


class PluginConfigResponse(BaseModel):
    modules: list["PluginConfigModuleItem"]
    dirs: list["PluginConfigDirItem"]


class PluginSettingFieldItem(BaseModel):
    key: str
    type: str
    editor: str = "readonly"
    item_type: str | None = None
    key_type: str | None = None
    default: object | None
    help: str
    choices: list[object] = []
    current_value: object | None = None
    local_value: object | None = None
    value_source: str = "default"
    global_key: str | None = None
    has_local_override: bool = False
    allows_null: bool = False
    editable: bool = False
    type_category: str = "unsupported"


class PluginSettingsResponse(BaseModel):
    module_name: str
    section: str
    legacy_flatten: bool = False
    config_source: str = "none"
    has_config_model: bool = False
    fields: list[PluginSettingFieldItem]


class PluginRawSettingsResponse(BaseModel):
    module_name: str
    section: str
    text: str


class PluginSettingsUpdateRequest(BaseModel):
    values: dict[str, object | None]
    clear: list[str] = []


class PluginSettingsRawUpdateRequest(BaseModel):
    text: str


class PluginConfigRequest(BaseModel):
    modules: list[str]
    dirs: list[str]


class AdapterConfigItem(BaseModel):
    name: str
    is_loaded: bool
    is_importable: bool


class AdapterConfigResponse(BaseModel):
    modules: list[AdapterConfigItem]


class AdapterConfigRequest(BaseModel):
    modules: list[str]


class PluginConfigModuleItem(BaseModel):
    name: str
    is_loaded: bool
    is_importable: bool


class PluginConfigDirItem(BaseModel):
    path: str
    exists: bool
    is_loaded: bool


class DriverConfigItem(BaseModel):
    name: str
    is_active: bool


class DriverConfigResponse(BaseModel):
    builtin: list[DriverConfigItem]


class DriverConfigRequest(BaseModel):
    builtin: list[str]


class BanItem(BaseModel):
    id: int
    user_id: str | None
    group_id: str | None
    duration: int
    reason: str | None


class BanCreateRequest(BaseModel):
    user_id: str
    group_id: str | None = None
    duration: int = 0
    reason: str | None = None


class GroupItem(BaseModel):
    group_id: str
    group_name: str | None
    bot_status: bool
    disabled_plugins: list[str]


class UserLevelItem(BaseModel):
    user_id: str
    group_id: str
    level: int


class UpdateLevelRequest(BaseModel):
    level: int = Field(ge=0, le=4)


class DataTableInfo(BaseModel):
    name: str
    label: str
    primary_key: str


class DataListResponse(BaseModel):
    table: str
    primary_key: str
    columns: list[str]
    total: int
    page: int
    page_size: int
    items: list[dict[str, object | None]]


class DataRecordResponse(BaseModel):
    table: str
    primary_key: str
    record: dict[str, object | None]


class DataUpdateRequest(BaseModel):
    values: dict[str, object | None]
