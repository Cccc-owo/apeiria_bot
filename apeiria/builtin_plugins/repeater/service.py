"""Core repeating logic for the repeater plugin."""

from __future__ import annotations

import time
from hashlib import sha256
from random import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .config import RepeaterConfig


class _RoundState:
    """Track one active repeating round for a group and content.

    A round starts when group members send messages with the same content
    hash and ends when someone sends different content. ``last_triggered_at``
    is ``0.0`` while the round has not yet triggered a repeat, and greater
    than ``0`` once it has.
    """

    __slots__ = (
        "content_hash",  # 当前轮内容哈希
        "count",  # 当前轮累计次数
        "last_triggered_at",  # 本轮上一次复读时间戳，0.0 = 未复读
        "last_updated_at",  # 最近更新（含普通计数），用于过期清理
        "last_user_id",  # 上一个说话的用户
        "message",  # 原始消息对象
    )

    def __init__(  # noqa: PLR0913
        self,
        *,
        content_hash: str,
        message: Any,
        count: int,
        last_user_id: str,
        last_triggered_at: float,
        last_updated_at: float | None = None,
    ) -> None:
        """Initialize a round state for one group's repeated content.

        Args:
            content_hash (str): Hash identifying the round's content.
            message (Any): The message object stored for the round.
            count (int): Number of messages counted in the round so far.
            last_user_id (str): User id of the most recent sender.
            last_triggered_at (float): Timestamp of the last repeat, or ``0.0``.
            last_updated_at (float | None): Timestamp of the last update;
                defaults to the current monotonic time.
        """
        self.content_hash = content_hash
        self.message = message
        self.count = count
        self.last_user_id = last_user_id
        self.last_triggered_at = last_triggered_at
        self.last_updated_at = (
            last_updated_at if last_updated_at is not None else time.monotonic()
        )


def hash_message(message: Any) -> str:
    """Return a stable hash of the message content.

    Args:
        message (Any): The message object to hash.

    Returns:
        str: The SHA-256 hex digest of the message's string form.
    """
    raw = str(message)
    return sha256(raw.encode("utf-8")).hexdigest()


class RepeaterService:
    """Core logic that tracks repeating rounds per group and decides when to repeat.

    Lifecycle: a global in-memory singleton whose state is cleared on restart.
    """

    _CLEANUP_INTERVAL = 50

    def __init__(self) -> None:
        """Initialize an empty service with no tracked per-group state."""
        self._states: dict[str, _RoundState] = {}
        self._last_triggered: dict[str, float] = {}
        self._call_count = 0

    def _cleanup_stale(self, now: float, ttl: float) -> None:
        """Drop round states that have been idle for longer than the TTL.

        Remove states whose last update is older than ``ttl`` seconds, along
        with their corresponding last-triggered records, so that long-inactive
        groups do not leak memory.

        Args:
            now (float): Current monotonic timestamp.
            ttl (float): Maximum age in seconds before a state is considered
                stale.
        """
        self._states = {
            k: v for k, v in self._states.items() if now - v.last_updated_at < ttl
        }
        self._last_triggered = {
            k: v for k, v in self._last_triggered.items() if k in self._states
        }

    def evaluate(  # noqa: PLR0911
        self,
        group_scope: str,
        content_hash: str,
        message: Any,
        user_id: str,
        *,
        config: RepeaterConfig,
    ) -> Any | None:
        """Evaluate a message and return it when it should be repeated.

        Return the original message to trigger a repeat when the round count
        for the same group and content reaches the configured repeat threshold,
        the round has not yet repeated, the per-group cooldown has elapsed, and
        ``random()`` falls below the configured probability. Otherwise return
        ``None`` to skip the message. Consecutive messages from the same user
        are not counted.

        Args:
            group_scope (str): Group scope identifier, typically
                ``scope:group_id``.
            content_hash (str): Stable hash of the message content.
            message (Any): The incoming message object to evaluate.
            user_id (str): User id of the message sender.
            config (RepeaterConfig): Plugin configuration.

        Returns:
            Any | None: The original message when repeating should trigger,
                otherwise ``None``.
        """
        now = time.monotonic()
        self._call_count += 1

        # ---- 周期性清理僵死状态 ----
        if self._call_count % self._CLEANUP_INTERVAL == 0:
            self._cleanup_stale(now, config.cooldown_seconds * 5)

        # ---- 定位当前群的状态 ----
        previous = self._states.get(group_scope)

        if previous is not None:
            previous.last_updated_at = now
            # 内容变了 → 开启新一轮
            if previous.content_hash != content_hash:
                previous = None
            # 同一用户连续发 → 不计入
            elif previous.last_user_id == user_id:
                return None

        # 无历史或内容已变 → 初始化新轮
        if previous is None:
            self._states[group_scope] = _RoundState(
                content_hash=content_hash,
                message=message,
                count=1,
                last_user_id=user_id,
                last_triggered_at=0.0,
                last_updated_at=now,
            )
            return None

        # ---- 本轮存在，递增加 ----
        count = previous.count + 1
        state = _RoundState(
            content_hash=content_hash,
            message=message,
            count=count,
            last_user_id=user_id,
            last_triggered_at=previous.last_triggered_at,
            last_updated_at=now,
        )

        # 未达阈值
        if count < config.repeat_threshold:
            self._states[group_scope] = state
            return None

        # 本轮已复读过 → 不再复读
        if previous.last_triggered_at > 0:
            self._states[group_scope] = state
            return None

        # 冷却中：按群维度记录上一次真正触发时间，跨内容轮次也生效。
        last_triggered = self._last_triggered.get(group_scope)
        if (
            last_triggered is not None
            and now - last_triggered < config.cooldown_seconds
        ):
            self._states[group_scope] = state
            return None

        # 概率拦截
        if random() >= config.probability:
            self._states[group_scope] = state
            return None

        # ---- 触发复读 ----
        self._states[group_scope] = _RoundState(
            content_hash=content_hash,
            message=message,
            count=count,
            last_user_id=user_id,
            last_triggered_at=now,
            last_updated_at=now,
        )
        self._last_triggered[group_scope] = now
        return message

    def reset(self, group_scope: str) -> None:
        """Reset the tracked state for the given group (for testing/debugging).

        Args:
            group_scope (str): Group scope identifier whose state to clear.
        """
        self._states.pop(group_scope, None)
        self._last_triggered.pop(group_scope, None)


__all__ = ["RepeaterService", "hash_message"]
