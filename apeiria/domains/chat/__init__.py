"""Chat application-facing services.

Only the Web UI-facing chat facade is exported here. Transport protocol details
remain separate so this package-level surface stays small.
"""

from . import protocol
from .service import (
    ChatAssetFileMissingError,
    ChatAssetNotFoundError,
    ChatAuthError,
    ChatGatewayService,
    chat_gateway_service,
)

__all__ = [
    "ChatAssetFileMissingError",
    "ChatAssetNotFoundError",
    "ChatAuthError",
    "ChatGatewayService",
    "chat_gateway_service",
    "protocol",
]
