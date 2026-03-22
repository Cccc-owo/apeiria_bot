"""Independent WebChat platform kernel."""

from . import protocol
from .alconna import register_webchat_uniseg
from .connection import WebChatConnection
from .service import WebChatService

register_webchat_uniseg()

web_chat_service = WebChatService()

__all__ = ["WebChatConnection", "WebChatService", "protocol", "web_chat_service"]
