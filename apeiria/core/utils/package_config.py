from __future__ import annotations

from typing import Any

from apeiria.package_ids import normalize_package_id


def normalize_string_list(
    value: object,
    *,
    ignore_literal_null: bool = False,
) -> list[str]:
    if not isinstance(value, list | tuple):
        return []

    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if not normalized:
            continue
        if ignore_literal_null and normalized.lower() in {"none", "null"}:
            continue
        result.append(normalized)
    return result


def normalize_package_item_map(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}

    result: dict[str, list[str]] = {}
    for package_name, items in value.items():
        if not isinstance(package_name, str) or not package_name.strip():
            continue
        normalized_items = sorted(set(normalize_string_list(items)))
        normalized_package = normalize_package_id(package_name)
        if normalized_package and normalized_items:
            result[normalized_package] = normalized_items
    return result


def add_unique_sorted_item(items: list[str], item: str) -> bool:
    if item in items:
        return False
    items.append(item)
    items.sort()
    return True


def remove_item_from_config_packages(
    config: dict[str, Any],
    *,
    items_key: str,
    item: str,
) -> None:
    config[items_key] = [value for value in config[items_key] if value != item]
    for package_name in list(config["packages"]):
        config["packages"][package_name] = [
            value for value in config["packages"][package_name] if value != item
        ]
        if not config["packages"][package_name]:
            del config["packages"][package_name]


def bind_package_item(
    config: dict[str, Any],
    *,
    package_name: str,
    item: str,
) -> bool:
    package_key = normalize_package_id(package_name)
    if not package_key:
        return False

    package_items = set(config["packages"].get(package_key, []))
    package_items.add(item)
    config["packages"][package_key] = sorted(package_items)
    return True


def get_package_bound_items(
    config: dict[str, Any],
    *,
    package_name: str,
) -> list[str]:
    return list(config["packages"].get(normalize_package_id(package_name), []))


def unbind_package_item(
    config: dict[str, Any],
    *,
    package_name: str,
    items_key: str,
    item: str | None = None,
) -> bool:
    package_key = normalize_package_id(package_name)
    if not package_key:
        return False

    if item is None:
        removed_items = config["packages"].pop(package_key, [])
        for removed_item in removed_items:
            config[items_key] = [
                value for value in config[items_key] if value != removed_item
            ]
        return bool(removed_items)

    package_items = config["packages"].get(package_key, [])
    if not package_items:
        return False

    config["packages"][package_key] = [
        value for value in package_items if value != item
    ]
    if not config["packages"][package_key]:
        del config["packages"][package_key]
    config[items_key] = [value for value in config[items_key] if value != item]
    return True
