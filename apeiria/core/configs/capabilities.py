"""Configuration field capability rules.

Pipeline:
1. declarations.py normalizes source annotations into RegisterConfig fields.
2. capabilities.py maps RegisterConfig to UI/runtime capabilities.
3. route layer only exposes values plus capability metadata.
4. frontend renders strictly from `editor` and `editable`.

Support matrix:
- bool -> switch/select
- str/int/float -> input/select
- list[str] / set[str] -> chips
- Path -> input
- timedelta -> input
- pydantic network/address-like types -> input
- everything else -> readonly
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from .models import RegisterConfig


@dataclass(frozen=True)
class TypeCapability:
    category: str
    editor: str
    editable: bool


def format_type_name(value: object | None) -> str | None:
    if value is None:
        return None
    return getattr(value, "__name__", str(value))


def get_field_capability(config: RegisterConfig) -> TypeCapability:
    if config.choices:
        capability = _capability_for_choice(config)
        if capability is not None:
            return capability

    capability = _capability_for_simple(config)
    if capability is not None:
        return capability

    capability = _capability_for_collection(config)
    if capability is not None:
        return capability

    return _readonly_capability("unsupported")


def normalize_value_for_response(
    config: RegisterConfig,
    value: object | None,
) -> object | None:
    if value is None:
        return None

    capability = get_field_capability(config)
    if capability.category == "sequence" and isinstance(value, list | set | tuple):
        return [_normalize_scalar_value(item) for item in value]
    if capability.category == "mapping" and isinstance(value, dict):
        return {
            str(key): _normalize_json_compatible_value(item)
            for key, item in value.items()
        }
    return _normalize_scalar_value(value)


def normalize_choices_for_response(values: list[object]) -> list[object]:
    return [_normalize_scalar_value(value) for value in values]


def coerce_config_value(config: RegisterConfig, value: object) -> object:
    capability = get_field_capability(config)
    if not capability.editable:
        raise HTTPException(
            status_code=400,
            detail=f"field {config.key} is not editable",
        )

    if value is None:
        if config.allows_null:
            return None
        raise HTTPException(
            status_code=400,
            detail=f"field {config.key} does not allow null",
        )

    handlers = {
        "bool": _coerce_bool_value,
        "scalar": _coerce_scalar_value,
        "path": _coerce_string_value,
        "duration": _coerce_string_value,
        "text_like": _coerce_string_value,
        "sequence": _coerce_sequence_value,
        "mapping": _coerce_mapping_value,
    }
    handler = handlers.get(capability.category)
    if handler is None:
        raise HTTPException(
            status_code=400,
            detail=f"field {config.key} is not editable",
        )
    return handler(config, value)


def _editable_capability(category: str, editor: str) -> TypeCapability:
    return TypeCapability(category=category, editor=editor, editable=True)


def _readonly_capability(category: str) -> TypeCapability:
    return TypeCapability(category=category, editor="readonly", editable=False)


def _capability_for_choice(config: RegisterConfig) -> TypeCapability | None:
    if config.type is bool:
        return _editable_capability("bool", "select")
    if config.type in {str, int, float}:
        return _editable_capability("scalar", "select")
    return None


def _capability_for_simple(config: RegisterConfig) -> TypeCapability | None:
    if config.type is bool:
        return _editable_capability("bool", "switch")
    if config.type in {str, int, float}:
        return _editable_capability("scalar", "input")
    if config.type is Path:
        return _editable_capability("path", "input")
    if config.type is timedelta:
        return _editable_capability("duration", "input")
    if _supports_text_input(config.type):
        return _editable_capability("text_like", "input")
    return None


def _capability_for_collection(config: RegisterConfig) -> TypeCapability | None:
    if config.type in {list, set}:
        return _capability_for_sequence(config)
    if config.type is dict:
        return _capability_for_mapping(config)
    return None


def _capability_for_sequence(config: RegisterConfig) -> TypeCapability:
    if config.item_type not in {None, str}:
        return _readonly_capability("sequence")
    return _editable_capability("sequence", "chips")


def _capability_for_mapping(_config: RegisterConfig) -> TypeCapability:
    return _readonly_capability("mapping")


def _supports_text_input(value: object) -> bool:
    if not isinstance(value, type):
        return False
    module_name = getattr(value, "__module__", "")
    return module_name.startswith("pydantic.networks")


def _normalize_scalar_value(value: object) -> object:
    if isinstance(value, Path | timedelta):
        return str(value)
    if isinstance(value, bool | int | float | str):
        return value
    return str(value)


def _normalize_json_compatible_value(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): _normalize_json_compatible_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list | set | tuple):
        return [_normalize_json_compatible_value(item) for item in value]
    return _normalize_scalar_value(value)


def _coerce_bool_value(config: RegisterConfig, value: object) -> bool:
    if isinstance(value, bool):
        return value
    raise HTTPException(status_code=400, detail=f"field {config.key} expects bool")


def _coerce_scalar_value(config: RegisterConfig, value: object) -> object:
    if config.type is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise HTTPException(
                status_code=400,
                detail=f"field {config.key} expects int",
            )
        return value
    if config.type is float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise HTTPException(
                status_code=400,
                detail=f"field {config.key} expects float",
            )
        return float(value)
    if config.type is str:
        if not isinstance(value, str):
            raise HTTPException(
                status_code=400,
                detail=f"field {config.key} expects str",
            )
        return value
    raise HTTPException(status_code=400, detail=f"field {config.key} is not editable")


def _coerce_string_value(config: RegisterConfig, value: object) -> str:
    if isinstance(value, str):
        return value
    raise HTTPException(status_code=400, detail=f"field {config.key} expects str")


def _coerce_sequence_value(config: RegisterConfig, value: object) -> list[object]:
    if not isinstance(value, list):
        raise HTTPException(
            status_code=400,
            detail=f"field {config.key} expects list",
        )
    normalized_items = [_coerce_sequence_item_value(config, item) for item in value]
    if config.type is set:
        return list(dict.fromkeys(normalized_items))
    return normalized_items


def _coerce_sequence_item_value(config: RegisterConfig, value: object) -> object:
    item_type = config.item_type if isinstance(config.item_type, type) else str
    if item_type is bool:
        if isinstance(value, bool):
            return value
        raise HTTPException(
            status_code=400,
            detail=f"field {config.key} expects list[bool]",
        )
    if item_type is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise HTTPException(
                status_code=400,
                detail=f"field {config.key} expects list[int]",
            )
        return value
    if item_type is float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise HTTPException(
                status_code=400,
                detail=f"field {config.key} expects list[float]",
            )
        return float(value)
    if not isinstance(value, str):
        raise HTTPException(
            status_code=400,
            detail=f"field {config.key} expects list[str]",
        )
    return value


def _coerce_mapping_value(
    config: RegisterConfig,
    value: object,
) -> dict[object, object]:
    if not isinstance(value, dict):
        raise HTTPException(
            status_code=400,
            detail=f"field {config.key} expects object",
        )
    if not _is_json_compatible_mapping(value):
        raise HTTPException(
            status_code=400,
            detail=f"field {config.key} expects JSON-compatible object",
        )
    return value


def _is_json_compatible_mapping(value: object) -> bool:
    if isinstance(value, bool | int | float | str):
        return True
    if isinstance(value, list):
        return all(_is_json_compatible_mapping(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_compatible_mapping(item)
            for key, item in value.items()
        )
    return False
