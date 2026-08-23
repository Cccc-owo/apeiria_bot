"""Access control rule loading and evaluation for plugins."""

from __future__ import annotations

from sqlalchemy import select

from apeiria.db.engine import get_db
from apeiria.db.models.access import AccessRule


class AccessControl:
    """Evaluate access rules and decide whether a user may use a plugin.

    AccessControl loads a snapshot of the configured access rules and then
    answers permission queries for a given user, group, and plugin. Rules are
    evaluated in descending priority order, and the first rule that matches
    both the subject and the plugin determines the outcome; when no rule
    matches, access is allowed by default.
    """

    def __init__(self) -> None:
        """Initialize an empty access control state.

        Sets the loaded rules to an empty list and marks the snapshot as not
        loaded yet.
        """
        self._rules: list[AccessRule] = []
        self._loaded = False

    async def load_snapshot(self) -> None:
        """Load and sort the access rules from the database.

        Reads every access rule, sorts them by priority in descending order,
        and stores them so that later permission checks use the latest rules.
        """
        db = get_db()
        async with db.gate.read() as sess:
            rules = list((await sess.execute(select(AccessRule))).scalars().all())
        self._rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        self._loaded = True

    def evaluate(
        self,
        user_id: str,
        group_id: str | None,
        plugin_name: str,
        *,
        is_superuser: bool = False,
    ) -> bool:
        """Return whether the user is allowed to use the given plugin.

        Args:
            user_id: The identifier of the user requesting access.
            group_id: The identifier of the group the event originates from,
                or None when not in a group.
            plugin_name: The name of the plugin being accessed.
            is_superuser: Whether the user is a superuser; superusers are
                always granted access.

        Returns:
            True if access is allowed, False if a matching rule denies it.
        """
        if not self._loaded:
            return True

        if is_superuser:
            return True

        for rule in self._rules:
            if not _subject_matches(rule, user_id, group_id):
                continue
            if rule.plugin_name is not None and rule.plugin_name != plugin_name:
                continue
            return rule.action == "allow"

        return True

    def evaluate_with_detail(
        self,
        user_id: str,
        group_id: str | None,
        plugin_name: str,
        *,
        is_superuser: bool = False,
    ) -> dict:
        """Return access decisions along with the matched rule details.

        Args:
            user_id: The identifier of the user requesting access.
            group_id: The identifier of the group the event originates from,
                or None when not in a group.
            plugin_name: The name of the plugin being accessed.
            is_superuser: Whether the user is a superuser; superusers are
                always granted access.

        Returns:
            A dictionary with the resulting action ("allow" or "deny"), the
            id of the matched rule, and a dict describing the matched rule; the
            unmatched fields are None.
        """
        result: dict = {
            "action": "allow",
            "matched_rule_id": None,
            "matched_rule": None,
        }

        if not self._loaded:
            return result

        if is_superuser:
            return result

        for rule in self._rules:
            if not _subject_matches(rule, user_id, group_id):
                continue
            if rule.plugin_name is not None and rule.plugin_name != plugin_name:
                continue
            result["action"] = rule.action
            result["matched_rule_id"] = rule.id
            result["matched_rule"] = {
                "id": rule.id,
                "subject_type": rule.subject_type,
                "subject_id": rule.subject_id,
                "plugin_name": rule.plugin_name,
                "action": rule.action,
                "priority": rule.priority,
            }
            break

        return result


def _subject_matches(
    rule: AccessRule,
    user_id: str,
    group_id: str | None,
) -> bool:
    """Return whether the user and group match the rule's subject.

    Args:
        rule: The access rule whose subject is checked.
        user_id: The identifier of the user requesting access.
        group_id: The identifier of the group the event originates from,
            or None when not in a group.

    Returns:
        True if the rule's subject type matches the provided identifiers.
    """
    if rule.subject_type == "user":
        return rule.subject_id == user_id
    if rule.subject_type == "group":
        return group_id is not None and rule.subject_id == group_id
    return False
