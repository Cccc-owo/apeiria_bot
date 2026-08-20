from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import yaml
from nonebot.log import logger

from .config import TriggerReplyConfig  # noqa: TC001
from .models import TriggerRule

_RULE_EXTENSIONS = ("*.yaml", "*.yml")


def collect_rule_files(config: TriggerReplyConfig) -> list[Path]:
    from nonebot import require

    require("nonebot_plugin_localstore")
    from nonebot_plugin_localstore import get_plugin_config_file

    file_path = get_plugin_config_file(config.rules_file)
    if file_path.is_dir():
        paths: list[Path] = []
        for pattern in _RULE_EXTENSIONS:
            paths.extend(file_path.glob(pattern))
        return sorted(set(paths))
    if file_path.exists():
        return [file_path]
    return []


def _normalize_rule(  # noqa: C901, PLR0912
    raw: Mapping[str, object],
) -> dict[str, object]:
    normalized = dict(raw)

    if "match" in normalized and "matches" not in normalized:
        match_value = normalized.pop("match")
        match_type = normalized.pop("type", "full")
        matches: list[dict[str, object]] = []
        if isinstance(match_value, str):
            matches.append(
                {
                    "type": match_type,
                    "pattern": match_value,
                    **_match_options(normalized),
                }
            )
        elif isinstance(match_value, Sequence) and not isinstance(match_value, str):
            for item in match_value:
                if isinstance(item, str):
                    matches.append(
                        {
                            "type": match_type,
                            "pattern": item,
                            **_match_options(normalized),
                        }
                    )
                elif isinstance(item, Mapping):
                    matches.append(dict(item))
        normalized["matches"] = matches

    if "reply" in normalized and "replies" not in normalized:
        reply_value = normalized.pop("reply")
        replies: list[dict[str, object]] = []
        if isinstance(reply_value, str):
            replies.append({"text": reply_value})
        elif isinstance(reply_value, Sequence) and not isinstance(reply_value, str):
            for item in reply_value:
                if isinstance(item, str):
                    replies.append({"text": item})
                elif isinstance(item, Mapping):
                    replies.append(dict(item))
        normalized["replies"] = replies

    for key in ("type", "match", "reply"):
        normalized.pop(key, None)
    for key in ("to_me", "ignore_case", "strip", "allow_plaintext"):
        normalized.pop(key, None)

    return normalized


def _match_options(normalized: dict[str, object]) -> dict[str, object]:
    options: dict[str, object] = {}
    for key in ("to_me", "ignore_case", "strip", "allow_plaintext"):
        if key in normalized:
            options[key] = normalized[key]
    return options


def _load_file(  # noqa: C901
    file_path: Path,
) -> tuple[list[TriggerRule], list[str]]:
    if not file_path.exists():
        return [], []
    try:
        raw_text = file_path.read_text(encoding="utf-8")
        payload = yaml.safe_load(raw_text) or {}
    except Exception as exc:  # noqa: BLE001
        return [], [f"YAML 解析失败: {exc}"]

    if not isinstance(payload, Mapping):
        return [], ["规则文件必须是 YAML 映射，且包含 rules 列表"]
    raw_rules = payload.get("rules", [])
    if not isinstance(raw_rules, list):
        return [], ["rules 必须是列表"]

    rules: list[TriggerRule] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    for index, raw_rule in enumerate(raw_rules):
        prefix = f"rules[{index}]"
        if not isinstance(raw_rule, Mapping):
            errors.append(f"{prefix}: 必须是映射")
            continue
        try:
            normalized = _normalize_rule(raw_rule)
            rule = TriggerRule(**cast("Any", normalized))
            for match in rule.matches:
                if match.type == "regex":
                    flags = re.IGNORECASE if match.ignore_case else 0
                    re.compile(match.pattern, flags)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{prefix}: {exc}")
            continue

        if rule.id in seen_ids:
            errors.append(f"规则 ID 重复: {rule.id}")
            continue
        seen_ids.add(rule.id)
        rules.append(rule)

    rules.sort(key=lambda rule: rule.priority)
    return rules, errors


def load_rules(paths: Sequence[Path]) -> tuple[tuple[TriggerRule, ...], list[str]]:
    all_rules: list[TriggerRule] = []
    all_errors: list[str] = []

    for file_path in paths:
        file_rules, file_errors = _load_file(file_path)
        all_rules.extend(file_rules)
        if file_errors:
            all_errors.append(f"{file_path}: {'; '.join(file_errors)}")

    if all_errors:
        logger.warning(
            "触发回复加载了 {} 条规则，{} 个错误: {}",
            len(all_rules),
            len(all_errors),
            "; ".join(all_errors),
        )
    else:
        logger.info("触发回复加载了 {} 条规则", len(all_rules))
    return tuple(all_rules), all_errors


def files_signature(paths: Sequence[Path]) -> tuple[tuple[str, int, int], ...]:
    signature: list[tuple[str, int, int]] = []
    for path in paths:
        try:
            stat = path.stat()
        except OSError:
            signature.append((str(path), 0, 0))
        else:
            signature.append((str(path), stat.st_mtime_ns, stat.st_size))
    return tuple(signature)
