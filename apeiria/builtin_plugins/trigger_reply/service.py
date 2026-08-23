"""Rule-set caching, matching, and reply selection for trigger-reply."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from random import choices, random

from nonebot.log import logger

from .loader import files_signature, load_rules
from .models import (
    MatchResult,
    TriggerInput,
    TriggerMatch,
    TriggerReply,
    TriggerRule,
)
from .template import render_template


def _scoped_id(platform: str | None, value: str | None) -> str | None:
    """Build a platform-scoped user or group identifier.

    Args:
        platform: The platform name.
        value: The raw user or group ID.

    Returns:
        A ``platform:value`` identifier, or ``None`` when either input is
        ``None``.
    """
    if platform is None or value is None:
        return None
    return f"{platform}:{value}"


def _filter_allows(
    ids: Sequence[str],
    mode: str,
    target: str | None,
) -> bool:
    """Decide whether a target identifier passes the filter list.

    In ``white`` mode only listed IDs pass; in ``black`` mode every ID except
    the listed ones passes, including when no group or user background exists.

    Args:
        ids: The IDs in the filter list.
        mode: The filter mode, ``white`` or ``black``.
        target: The platform-scoped target identifier.

    Returns:
        ``True`` when the target passes the filter, otherwise ``False``.
    """
    if not ids:
        return True
    matches = False
    if target is not None:
        platform, _, _ = target.partition(":")
        matches = target in ids or f"{platform}:*" in ids
    # white: 只能在列出名单内触发; black: 除列出名单外都触发(含无群/无用户背景)
    return matches if mode == "white" else not matches


@lru_cache(maxsize=256)
def _compile_regex(pattern: str, *, ignore_case: bool) -> re.Pattern[str]:
    """Compile and cache a regular expression.

    Args:
        pattern: The regular expression pattern.
        ignore_case: Whether matching should ignore case.

    Returns:
        The compiled regular expression.
    """
    flags = re.IGNORECASE if ignore_case else 0
    return re.compile(pattern, flags)


def _match_one(  # noqa: C901, PLR0911, PLR0912
    match: TriggerMatch,
    trigger: TriggerInput,
) -> tuple[str, dict[str, str]] | None:
    """Test a single match condition against the trigger input.

    Args:
        match: The match condition.
        trigger: The trigger input.

    Returns:
        A ``(triggered_text, captures)`` tuple on a hit (``captures`` holds
        named regex groups, empty otherwise), or ``None`` when there is no
        match.
    """
    if match.to_me and not trigger.is_to_me:
        return None

    message_text = trigger.message_text
    plaintext = trigger.plaintext
    pattern = match.pattern

    if match.strip:
        message_text = message_text.strip()
        plaintext = plaintext.strip()
        pattern = pattern.strip()

    if match.type == "regex":
        compiled = _compile_regex(pattern, ignore_case=match.ignore_case)
        m = compiled.search(message_text)
        if m is None and match.allow_plaintext:
            m = compiled.search(plaintext)
        if m is None:
            return None
        captures = {key: value or "" for key, value in m.groupdict().items()}
        return m.group(0), captures

    cmp_msg = message_text
    cmp_plain = plaintext
    cmp_pattern = pattern
    if match.ignore_case:
        cmp_msg = cmp_msg.lower()
        cmp_plain = cmp_plain.lower()
        cmp_pattern = cmp_pattern.lower()

    if match.type == "full":
        if cmp_msg == cmp_pattern:
            return message_text, {}
        if match.allow_plaintext and cmp_plain == cmp_pattern:
            return plaintext, {}
    elif match.type == "start":
        if cmp_msg.startswith(cmp_pattern):
            return message_text, {}
        if match.allow_plaintext and cmp_plain.startswith(cmp_pattern):
            return plaintext, {}
    elif match.type == "end":
        if cmp_msg.endswith(cmp_pattern):
            return message_text, {}
        if match.allow_plaintext and cmp_plain.endswith(cmp_pattern):
            return plaintext, {}
    else:
        if cmp_pattern in cmp_msg:
            return message_text, {}
        if match.allow_plaintext and cmp_pattern in cmp_plain:
            return plaintext, {}
    return None


def _select_reply(replies: tuple[TriggerReply, ...]) -> TriggerReply:
    """Select a reply entry by weighted random choice.

    Args:
        replies: The candidate replies.

    Returns:
        The selected reply entry.
    """
    weights = tuple(reply.weight for reply in replies)
    return choices(replies, weights=weights, k=1)[0]


def _build_context(
    trigger: TriggerInput,
    rule: TriggerRule,
    captures: Mapping[str, str],
    triggered_text: str,
) -> dict[str, object]:
    """Build the template-rendering context.

    Merges the trigger input, rule variables, and regex captures for use by
    the template engine.

    Args:
        trigger: The trigger input.
        rule: The matched rule.
        captures: The regex capture mapping.
        triggered_text: The text that triggered the match.

    Returns:
        The template-rendering context mapping.
    """
    context: dict[str, object] = {
        "user_id": trigger.user_id or "",
        "user_name": trigger.user_name or "",
        "group_id": trigger.group_id or "",
        "group_name": trigger.group_name or "",
        "platform": trigger.platform or "",
        "scene": trigger.scene,
        "scene_id": trigger.group_id or trigger.user_id or "",
        "bot_id": trigger.bot_id or "",
        "message": trigger.message_text,
        "text": trigger.plaintext,
        "trigger": triggered_text,
        "message_id": trigger.message_id or "",
        "time": trigger.time,
        "date": trigger.date,
    }
    context.update(rule.vars)
    context.update(captures)
    return context


class TriggerRuleSet:
    """A set of loaded trigger rules and their file state.

    Detects changes via file names and metadata signatures, and performs
    matching against a trigger input.
    """

    def __init__(
        self,
        rules: tuple[TriggerRule, ...],
        paths: tuple[Path, ...] = (),
        signature: tuple[tuple[str, int, int], ...] = (),
    ) -> None:
        """Initialize the rule set.

        Args:
            rules: The loaded rules.
            paths: The rule file paths.
            signature: The metadata signature of the rule files.
        """
        self.rules = rules
        self._paths = paths
        self._signature = signature

    @classmethod
    def load(cls, paths: Sequence[Path]) -> tuple["TriggerRuleSet", list[str]]:
        """Load a rule set from file paths.

        Args:
            paths: Sequence of rule file paths.

        Returns:
            A tuple of the new rule set and the list of error messages.
        """
        rules, errors = load_rules(paths)
        return cls(
            rules,
            tuple(paths),
            files_signature(paths),
        ), errors

    def has_changed(self) -> bool:
        """Return whether the rule files have changed.

        Returns:
            ``True`` when the current file signature differs from the recorded
            one, otherwise ``False``.
        """
        return files_signature(self._paths) != self._signature

    def match(  # noqa: C901
        self,
        trigger: TriggerInput,
    ) -> MatchResult | None:
        """Run rule matching for the trigger input.

        Iterates the rules in priority order, checking the enabled flag, scene
        and filter lists, match conditions, and probability; on a hit it
        selects a reply and renders the template.

        Args:
            trigger: The trigger input.

        Returns:
            The match result on a hit, otherwise ``None``.
        """
        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.scenes and trigger.scene not in rule.scenes:
                continue
            if rule.groups and not _filter_allows(
                rule.groups,
                rule.group_mode,
                _scoped_id(trigger.platform, trigger.group_id),
            ):
                continue
            if rule.users and not _filter_allows(
                rule.users,
                rule.user_mode,
                _scoped_id(trigger.platform, trigger.user_id),
            ):
                continue

            triggered_text: str | None = None
            captures: dict[str, str] = {}
            for match in rule.matches:
                matched = _match_one(match, trigger)
                if matched is not None:
                    triggered_text, captures = matched
                    break
            if triggered_text is None:
                continue

            if rule.chance < 1.0 and random() >= rule.chance:
                continue

            reply = _select_reply(rule.replies)
            context = _build_context(trigger, rule, captures, triggered_text)
            try:
                text = render_template(reply.text, context)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "触发回复模板渲染失败，使用原始文本: {}",
                    exc,
                )
                text = reply.text
            return MatchResult(
                text=text,
                rule=rule,
                triggered_text=triggered_text,
                context=context,
            )
        return None
