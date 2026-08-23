"""Pydantic models describing the Apeiria configuration schema."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel


class NoneBotConfig(BaseModel):
    """Configuration for the underlying NoneBot runtime.

    Holds the NoneBot core settings that are expanded into the process
    environment at startup.
    """

    driver: str = "~fastapi+~httpx+~websockets"
    host: str = "127.0.0.1"
    port: int = 8080
    command_start: list[str] = ["/"]
    command_sep: list[str] = ["."]
    superusers: list[str] = []
    nickname: list[str] = ["Bot"]
    locale: str = "zh_CN"
    log_level: str = "INFO"


class DatabaseConfig(BaseModel):
    """Configuration for the application database.

    Defines the path to the SQLite database file.
    """

    path: str = "data/apeiria.db"


class WebConfig(BaseModel):
    """Configuration for the Web UI server.

    Defines the network address, authentication credentials, and proxy
    handling for the browser-facing Web UI.
    """

    host: str = "127.0.0.1"
    port: int = 8080
    username: str = "admin"
    token_expire_days: int = 7
    trusted_proxies: list[str] = []
    real_ip_header: str = ""


class LogConfig(BaseModel):
    """Configuration for the logging system.

    Defines the log file, level, rotation, retention, and stream buffer.
    """

    file: str = "data/logs/apeiria.log"
    level: str = "INFO"
    rotation: str = "10 MB"
    retention: str = "7 days"
    stream_buffer: int = 500


class WebChatConfig(BaseModel):
    """Configuration for the WebChat bridge.

    Defines whether the bridge is enabled and how its WebSocket endpoint and
    default user are resolved.
    """

    enabled: bool = True
    ws_path: str = "/ws/webchat"
    default_user_id: str = ""
    history_limit: int = 50


class ApeiriaConfig(BaseModel):
    """Apeiria-specific configuration grouping its sub-configs.

    Bundles the database, web, logging, and WebChat configurations.
    """

    database: DatabaseConfig = DatabaseConfig()
    web: WebConfig = WebConfig()
    logging: LogConfig = LogConfig()
    webchat: WebChatConfig = WebChatConfig()


class AppConfig(BaseModel):
    """Top-level application configuration.

    Groups the NoneBot runtime config, plugin configs, adapter configs, and
    the Apeiria-specific settings.
    """

    nonebot: NoneBotConfig = NoneBotConfig()
    plugins: dict[str, dict] = {}
    adapters: dict[str, dict] = {}
    apeiria: ApeiriaConfig = ApeiriaConfig()

    _nonebot_field_names: ClassVar[tuple[str, ...]] = (
        "driver",
        "host",
        "port",
        "command_start",
        "command_sep",
        "superusers",
        "nickname",
        "locale",
        "log_level",
    )
