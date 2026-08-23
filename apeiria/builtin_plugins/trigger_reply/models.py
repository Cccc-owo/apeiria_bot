"""Core data models for the trigger-reply plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MatchType = Literal["full", "fuzzy", "start", "end", "regex"]
TriggerScene = Literal["group", "private"]


class TriggerMatch(BaseModel):
    """A single match condition.

    Defines the match type, the pattern string, and matching options such as
    case sensitivity, whitespace handling, and plaintext fallback.
    """

    model_config = ConfigDict(extra="forbid")

    type: MatchType
    pattern: str
    to_me: bool = False
    ignore_case: bool = True
    strip: bool = True
    allow_plaintext: bool = True


class TriggerReply(BaseModel):
    """A single reply entry.

    Holds the reply text and the weight used for random selection.
    """

    model_config = ConfigDict(extra="forbid")

    text: str
    weight: float = Field(default=1.0, gt=0)


class TriggerRule(BaseModel):
    """A complete trigger rule.

    Composed of match conditions, replies, and controlling fields such as
    scope, filter lists, and probability.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    enabled: bool = True
    priority: int = Field(default=1, ge=1)
    block: bool = True
    chance: float = Field(default=1.0, ge=0.0, le=1.0)
    scenes: frozenset[TriggerScene] = frozenset()
    groups: tuple[str, ...] = ()
    group_mode: Literal["white", "black"] = "white"
    users: tuple[str, ...] = ()
    user_mode: Literal["white", "black"] = "white"
    vars: dict[str, str | int | float | bool] = {}
    matches: tuple[TriggerMatch, ...]
    replies: tuple[TriggerReply, ...]


@dataclass(slots=True)
class TriggerInput:
    """Input context for a single trigger evaluation.

    Describes the message source, sender, group, and time, used for rule
    matching and template rendering.
    """

    platform: str | None = None
    bot_id: str | None = None
    user_id: str | None = None
    group_id: str | None = None
    message_text: str = ""
    plaintext: str = ""
    is_to_me: bool = False
    user_name: str | None = None
    group_name: str | None = None
    message_id: str | None = None
    time: str = ""
    date: str = ""

    @property
    def scene(self) -> TriggerScene:
        """Return the scene of the current input.

        Returns:
            ``"group"`` when group context is present, otherwise ``"private"``.
        """
        return "group" if self.group_id is not None else "private"


@dataclass(slots=True)
class MatchResult:
    """The result of a single rule match.

    Contains the rendered reply text, the matched rule, the text that
    triggered the match, and the rendering context.
    """

    text: str
    rule: TriggerRule
    triggered_text: str
    context: dict[str, object]
