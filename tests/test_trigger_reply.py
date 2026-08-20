from __future__ import annotations

from pathlib import Path

from apeiria.builtin_plugins.trigger_reply import template
from apeiria.builtin_plugins.trigger_reply.loader import load_rules
from apeiria.builtin_plugins.trigger_reply.models import (
    TriggerInput,
    TriggerMatch,
    TriggerReply,
    TriggerRule,
)
from apeiria.builtin_plugins.trigger_reply.service import TriggerRuleSet


def _input(**kw: object) -> TriggerInput:
    base = {
        "platform": "qq",
        "bot_id": "b",
        "user_id": "u1",
        "group_id": None,
        "message_text": "",
        "plaintext": "",
        "is_to_me": False,
        "user_name": None,
        "group_name": None,
        "message_id": None,
        "time": "12:00",
        "date": "2026-01-01",
    }
    base.update(kw)
    return TriggerInput(**base)


def _rule(
    *,
    rule_id: str = "e",
    matches: tuple[TriggerMatch, ...] = (),
    replies: tuple[TriggerReply, ...] = (),
    **kw: object,
) -> TriggerRule:
    return TriggerRule(
        id=rule_id,
        matches=matches,
        replies=replies,
        **kw,
    )


def _ruleset(rules: tuple[TriggerRule, ...]) -> TriggerRuleSet:
    return TriggerRuleSet(rules)


# ---------------------------------------------------------------------------
# _extract_input
# ---------------------------------------------------------------------------


def test_extract_input_uses_uninfo_scene_and_scope() -> None:
    from types import SimpleNamespace

    from apeiria.builtin_plugins.trigger_reply import _extract_input

    event = SimpleNamespace(
        get_type=lambda: "message",
        get_message=lambda: "hello",
        get_plaintext=lambda: "hello",
        is_tome=lambda: False,
        message_id="m1",
        time=1_700_000_000,
    )
    bot = SimpleNamespace(self_id="111")
    session = SimpleNamespace(
        scope="QQClient",
        user=SimpleNamespace(id="456", nick="nick", name="name"),
        scene=SimpleNamespace(is_group=True, id="123", name="group-name"),
    )

    trigger = _extract_input(bot, event, session)

    assert trigger is not None
    assert trigger.platform == "QQClient"
    assert trigger.group_id == "123"
    assert trigger.user_id == "456"
    assert trigger.user_name == "nick"
    assert trigger.group_name == "group-name"
    assert trigger.message_id == "m1"


# ---------------------------------------------------------------------------
# template
# ---------------------------------------------------------------------------


def test_template_variable_and_default() -> None:
    assert template.render_template("hi {name}", {"name": "a"}) == "hi a"
    assert template.render_template("hi {name|朋友}", {}) == "hi 朋友"
    assert template.render_template("hi {name}", {}) == "hi {name}"


def test_template_if_else() -> None:
    tpl = "{% if name %}{name}{% else %}nobody{% endif %}"
    assert template.render_template(tpl, {"name": "a"}) == "a"
    assert template.render_template(tpl, {}) == "nobody"


def test_template_nested_if() -> None:
    tpl = "{% if a %}{% if b %}ab{% else %}a{% endif %}{% else %}none{% endif %}"
    assert template.render_template(tpl, {"a": "1", "b": "2"}) == "ab"
    assert template.render_template(tpl, {"a": "1"}) == "a"
    assert template.render_template(tpl, {}) == "none"


# ---------------------------------------------------------------------------
# loader
# ---------------------------------------------------------------------------


def test_load_rules_parses_yaml(tmp_path: Path) -> None:
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        """
rules:
  - id: greet
    priority: 2
    matches:
      - type: full
        pattern: hi
    replies:
      - text: hello
""".lstrip(),
        encoding="utf-8",
    )

    rules, errors = load_rules([rules_file])

    assert errors == []
    assert len(rules) == 1
    assert rules[0].id == "greet"
    assert rules[0].priority == 2
    assert rules[0].matches[0].pattern == "hi"


def test_load_rules_supports_shorthand(tmp_path: Path) -> None:
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        """
rules:
  - id: hello
    match: 你好
    reply: 你好呀
""".lstrip(),
        encoding="utf-8",
    )

    rules, errors = load_rules([rules_file])

    assert errors == []
    assert rules[0].matches[0].type == "full"
    assert rules[0].matches[0].pattern == "你好"
    assert rules[0].replies[0].text == "你好呀"


def test_load_rules_duplicate_id_reports_error(tmp_path: Path) -> None:
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        """
rules:
  - id: same
    match: a
    reply: x
  - id: same
    match: b
    reply: y
""".lstrip(),
        encoding="utf-8",
    )

    rules, errors = load_rules([rules_file])

    assert len(rules) == 1
    assert any("ID 重复" in error for error in errors)


def test_load_rules_sorts_by_priority(tmp_path: Path) -> None:
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        """
rules:
  - id: low
    priority: 10
    match: a
    reply: low
  - id: high
    priority: 1
    match: b
    reply: high
""".lstrip(),
        encoding="utf-8",
    )

    rules, _ = load_rules([rules_file])

    assert [rule.id for rule in rules] == ["high", "low"]


def test_load_rules_missing_file_returns_empty(tmp_path: Path) -> None:
    rules, errors = load_rules([tmp_path / "missing.yaml"])

    assert rules == ()
    assert errors == []


# ---------------------------------------------------------------------------
# service matching
# ---------------------------------------------------------------------------


def test_full_match_returns_reply() -> None:
    rule = _rule(
        matches=(TriggerMatch(type="full", pattern="hello"),),
        replies=(TriggerReply(text="hi"),),
    )
    result = _ruleset((rule,)).match(_input(message_text="hello", plaintext="hello"))
    assert result is not None
    assert result.text == "hi"


def test_non_match_returns_none() -> None:
    rule = _rule(
        matches=(TriggerMatch(type="full", pattern="hello"),),
        replies=(TriggerReply(text="hi"),),
    )
    result = _ruleset((rule,)).match(_input(message_text="bye", plaintext="bye"))
    assert result is None


def test_fuzzy_start_end_match() -> None:
    rules = (
        _rule(
            rule_id="fuzzy",
            matches=(TriggerMatch(type="fuzzy", pattern="lo"),),
            replies=(TriggerReply(text="f"),),
        ),
        _rule(
            rule_id="start",
            matches=(TriggerMatch(type="start", pattern="he"),),
            replies=(TriggerReply(text="s"),),
        ),
        _rule(
            rule_id="end",
            matches=(TriggerMatch(type="end", pattern="lo"),),
            replies=(TriggerReply(text="e"),),
        ),
    )
    assert (
        _ruleset(rules).match(_input(message_text="hello", plaintext="hello"))
        is not None
    )


def test_regex_match_with_capture() -> None:
    rule = _rule(
        matches=(TriggerMatch(type="regex", pattern=r"你好，?(?P<name>.+)"),),
        replies=(TriggerReply(text="你好，{name}"),),
    )
    result = _ruleset((rule,)).match(
        _input(message_text="你好，小明", plaintext="你好，小明")
    )
    assert result is not None
    assert result.text == "你好，小明"


def test_ignore_case_false_is_respected() -> None:
    case_sensitive = _rule(
        matches=(TriggerMatch(type="full", pattern="Hello", ignore_case=False),),
        replies=(TriggerReply(text="yes"),),
    )
    assert (
        _ruleset((case_sensitive,)).match(
            _input(message_text="hello", plaintext="hello")
        )
        is None
    )
    assert (
        _ruleset((case_sensitive,)).match(
            _input(message_text="Hello", plaintext="Hello")
        )
        is not None
    )


def test_strip_and_plaintext_fallback() -> None:
    rule = _rule(
        matches=(TriggerMatch(type="full", pattern="hello", allow_plaintext=True),),
        replies=(TriggerReply(text="hi"),),
    )
    assert (
        _ruleset((rule,)).match(_input(message_text="  hello  ", plaintext="hello"))
        is not None
    )


def test_to_me_filter_blocks_when_not_to_me() -> None:
    rule = _rule(
        matches=(TriggerMatch(type="full", pattern="hello", to_me=True),),
        replies=(TriggerReply(text="hi"),),
    )
    assert _ruleset((rule,)).match(_input(message_text="hello", is_to_me=False)) is None
    assert (
        _ruleset((rule,)).match(_input(message_text="hello", is_to_me=True)) is not None
    )


def test_scene_filter_blocks_private() -> None:
    rule = _rule(
        scenes=frozenset({"group"}),
        matches=(TriggerMatch(type="full", pattern="hello"),),
        replies=(TriggerReply(text="hi"),),
    )
    assert _ruleset((rule,)).match(_input(message_text="hello", group_id=None)) is None
    assert (
        _ruleset((rule,)).match(_input(message_text="hello", group_id="g1")) is not None
    )


def test_user_filter() -> None:
    rule = _rule(
        users=("qq:u1",),
        matches=(TriggerMatch(type="full", pattern="hello"),),
        replies=(TriggerReply(text="hi"),),
    )
    allowed = _input(message_text="hello", user_id="u1")
    blocked = _input(message_text="hello", user_id="u2")
    assert _ruleset((rule,)).match(allowed) is not None
    assert _ruleset((rule,)).match(blocked) is None


def test_rule_vars_and_template_condition() -> None:
    rule = _rule(
        vars={"title": "主人"},
        matches=(TriggerMatch(type="full", pattern="hello"),),
        replies=(
            TriggerReply(
                text=("{% if name %}{name}，{title}{% else %}欢迎，{title}{% endif %}")
            ),
        ),
    )
    result = _ruleset((rule,)).match(_input(message_text="hello", plaintext="hello"))
    assert result is not None
    assert result.text == "欢迎，主人"


def test_priority_uses_first_match() -> None:
    low = _rule(
        rule_id="low",
        priority=10,
        matches=(TriggerMatch(type="full", pattern="hello"),),
        replies=(TriggerReply(text="low"),),
    )
    high = _rule(
        rule_id="high",
        priority=1,
        matches=(TriggerMatch(type="full", pattern="hello"),),
        replies=(TriggerReply(text="high"),),
    )
    result = _ruleset((high, low)).match(
        _input(message_text="hello", plaintext="hello")
    )
    assert result is not None
    assert result.text == "high"
