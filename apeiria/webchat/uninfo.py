"""Register the WebChat adapter's uninfo info fetcher with nonebot-plugin-uninfo."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from nonebot.adapters import Bot  # noqa: TC002
from nonebot.log import logger
from nonebot_plugin_uninfo.fetch import InfoFetcher as BaseInfoFetcher
from nonebot_plugin_uninfo.model import Member, Scene, SceneType, User

from apeiria.webchat.event import WebChatMessageEvent  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from nonebot_plugin_uninfo.constraint import SupportAdapter, SupportScope
    from nonebot_plugin_uninfo.model import BasicInfo


class WebChatInfoFetcher(BaseInfoFetcher):
    """Parse WebChat events into uninfo sessions (single user; private/group scenes)."""

    def extract_user(self, data: dict[str, Any]) -> User:
        """Extract a user from WebChat event data.

        Args:
            data: The event data supplied by the fetch hook.

        Returns:
            The parsed user model.
        """
        return User(id=data["user_id"], name=data.get("name"))

    def extract_scene(self, data: dict[str, Any]) -> Scene:
        """Extract a scene from WebChat event data.

        Args:
            data: The event data supplied by the fetch hook.

        Returns:
            The parsed scene model, typed as group or private.
        """
        is_group = data.get("scene_type") == "group"
        return Scene(
            id=data["scene_id"],
            type=SceneType.GROUP if is_group else SceneType.PRIVATE,
            name=data.get("scene_id"),
        )

    def extract_member(self, data: dict[str, Any], user: User | None) -> Member | None:
        """Extract a member from WebChat event data for group scenes.

        Args:
            data: The event data supplied by the fetch hook.
            user: An optional pre-resolved user to reuse.

        Returns:
            The parsed member model, or ``None`` for non-group scenes.
        """
        if data.get("scene_type") != "group":
            return None
        if user is None:
            user = self.extract_user(data)
        return Member(user, nick=user.name)

    def supply_self(self, bot: Bot) -> BasicInfo:
        """Supply the bot's self identity to the uninfo fetcher.

        Args:
            bot: The bot being described.

        Returns:
            The basic identity info for the bot.
        """
        return {
            "self_id": str(bot.self_id),
            "adapter": cast("SupportAdapter", "WebChat"),
            "scope": cast("SupportScope", "WebChat"),
        }

    async def query_user(self, bot: Bot, user_id: str) -> User | None:  # noqa: ARG002
        """Resolve a single user by id, returning a minimal user.

        Args:
            bot: The bot requesting the user.
            user_id: The id of the user to resolve.

        Returns:
            A minimal user model, or ``None``.
        """
        return User(id=user_id)

    async def query_scene(
        self,
        bot: Bot,  # noqa: ARG002
        scene_type: SceneType,
        scene_id: str,
        *,
        parent_scene_id: str | None = None,  # noqa: ARG002
    ) -> Scene | None:
        """Resolve a single scene by type and id.

        Args:
            bot: The bot requesting the scene.
            scene_type: The scene type.
            scene_id: The scene id.
            parent_scene_id: The optional parent scene id.

        Returns:
            A scene model for the given type and id.
        """
        return Scene(id=scene_id, type=scene_type)

    async def query_member(
        self,
        bot: Bot,  # noqa: ARG002
        scene_type: SceneType,  # noqa: ARG002
        parent_scene_id: str,  # noqa: ARG002
        user_id: str,  # noqa: ARG002
    ) -> Member | None:
        """Resolve a single member, always returning ``None``.

        Args:
            bot: The bot requesting the member.
            scene_type: The scene type.
            parent_scene_id: The parent scene id.
            user_id: The id of the member to resolve.

        Returns:
            ``None``, as WebChat does not resolve members.
        """
        return None

    async def query_users(self, bot: Bot) -> AsyncGenerator[User, None]:  # noqa: ARG002
        """Yield all known users, which is always empty for WebChat.

        Args:
            bot: The bot requesting the users.

        Yields:
            User entries; none are provided.
        """
        for item in ():
            yield item

    async def query_scenes(
        self,
        bot: Bot,  # noqa: ARG002
        scene_type: SceneType | None = None,  # noqa: ARG002
        *,
        parent_scene_id: str | None = None,  # noqa: ARG002
    ) -> AsyncGenerator[Scene, None]:
        """Yield all known scenes, which is always empty for WebChat.

        Args:
            bot: The bot requesting the scenes.
            scene_type: An optional scene type filter.
            parent_scene_id: An optional parent scene id filter.

        Yields:
            Scene entries; none are provided.
        """
        for item in ():
            yield item

    async def query_members(
        self,
        bot: Bot,  # noqa: ARG002
        scene_type: SceneType,  # noqa: ARG002
        parent_scene_id: str,  # noqa: ARG002
    ) -> AsyncGenerator[Member, None]:
        """Yield all known members, which is always empty for WebChat.

        Args:
            bot: The bot requesting the members.
            scene_type: The scene type.
            parent_scene_id: The parent scene id.

        Yields:
            Member entries; none are provided.
        """
        for item in ():
            yield item


fetcher = WebChatInfoFetcher(cast("SupportAdapter", "WebChat"))


@fetcher.supply
async def _supply_message(bot: Bot, event: WebChatMessageEvent) -> dict:  # noqa: ARG001
    """Supply the event data used to build uninfo session models.

    Args:
        bot: The bot handling the event.
        event: The WebChat message event.

    Returns:
        The user and scene data for the event.
    """
    return {
        "user_id": event.user_id,
        "name": event.user_id,
        "scene_type": event.scene_type,
        "scene_id": event.scene_id,
    }


def register_uninfo() -> None:
    """Register the WebChat uninfo fetcher in the info fetcher mapping."""
    from nonebot_plugin_uninfo.adapters import INFO_FETCHER_MAPPING

    INFO_FETCHER_MAPPING["WebChat"] = fetcher
    logger.success("WebChat uninfo fetcher registered")
