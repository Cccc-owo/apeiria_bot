"""Reflect Pydantic models into the configuration field node schema."""

from __future__ import annotations

import typing
from enum import Enum
from typing import Any, Literal, cast, get_args, get_origin

from pydantic import BaseModel

from apeiria.config.schema import (
    AnyField,
    ArrayField,
    FieldNode,
    MapField,
    ObjectField,
    PrimitiveField,
    PrimitiveType,
)


def _get_pydantic_type(field_info: Any) -> type:
    """Return the annotation of a Pydantic field.

    Args:
        field_info: The Pydantic field info.

    Returns:
        The field's annotation type.
    """
    return field_info.annotation


def _is_optional(annotation: type) -> bool:
    """Return whether the annotation is Optional (Union with None).

    Args:
        annotation: The type annotation to inspect.

    Returns:
        True if the annotation includes None in its union, else False.
    """
    origin = get_origin(annotation)
    if origin is typing.Union:
        args = get_args(annotation)
        return type(None) in args
    return False


def _unwrap_optional(annotation: type) -> type:
    """Strip the Optional (None) member from a union annotation.

    Args:
        annotation: The type annotation to unwrap.

    Returns:
        The single non-None type in the union, or the original annotation.
    """
    origin = get_origin(annotation)
    if origin is typing.Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
        return annotation
    return annotation


def _is_secret_type(annotation: type) -> bool:
    """Return whether the annotation is a Pydantic secret type.

    Args:
        annotation: The type annotation to inspect.

    Returns:
        True if the type's name or module contains "secret".
    """
    if not isinstance(annotation, type):
        return False
    qualname = getattr(annotation, "__qualname__", "").lower()
    module = getattr(annotation, "__module__", "").lower()
    return "secret" in qualname or "secret" in module


def _is_enum_type(annotation: type) -> bool:
    """Return whether the annotation is an Enum type.

    Args:
        annotation: The type annotation to inspect.

    Returns:
        True if the annotation is an Enum subclass and not a Literal.
    """
    origin = get_origin(annotation)
    if origin is Literal:
        return False
    return isinstance(annotation, type) and issubclass(annotation, Enum)


def _is_bool_type(annotation: type) -> bool:
    """Return whether the annotation is the bool type.

    Args:
        annotation: The type annotation to inspect.

    Returns:
        True if the annotation is exactly bool.
    """
    return isinstance(annotation, type) and annotation is bool


def _is_int_type(annotation: type) -> bool:
    """Return whether the annotation is an int type.

    Args:
        annotation: The type annotation to inspect.

    Returns:
        True if the annotation is a subclass of int.
    """
    return isinstance(annotation, type) and issubclass(annotation, int)


def _is_float_type(annotation: type) -> bool:
    """Return whether the annotation is a float type.

    Args:
        annotation: The type annotation to inspect.

    Returns:
        True if the annotation is a subclass of float.
    """
    return isinstance(annotation, type) and issubclass(annotation, float)


def _infer_primitive_type(annotation: type) -> PrimitiveType:
    """Infer the primitive type name for an annotation.

    Args:
        annotation: The type annotation to inspect.

    Returns:
        The primitive type name: literal, enum, bool, int, float, or str.
    """
    origin = get_origin(annotation)
    if origin is Literal:
        return "literal"
    if _is_enum_type(annotation):
        return "enum"
    if _is_bool_type(annotation):
        return "bool"
    if _is_int_type(annotation):
        return "int"
    if _is_float_type(annotation):
        return "float"
    return "str"


def _extract_choices(annotation: type) -> list[dict[str, str]] | None:
    """Extract selectable choices from a Literal or Enum annotation.

    Args:
        annotation: The type annotation to inspect.

    Returns:
        A list of ``{"value": ..., "label": ...}`` dicts for Literal and Enum
        types, or None when the annotation has no fixed choices.
    """
    origin = get_origin(annotation)
    if origin is Literal:
        args = get_args(annotation)
        return [{"value": str(a), "label": str(a)} for a in args]
    if _is_enum_type(annotation):
        members = cast("type[Enum]", annotation).__members__.values()
        return [{"value": member.value, "label": member.name} for member in members]
    return None


class _FakeFieldInfo:
    """Stand-in for a Pydantic field that carries only an annotation."""

    def __init__(self, annotation: type) -> None:
        """Initialize the fake field info with a required annotation.

        Args:
            annotation: The annotation to expose as ``self.annotation``.
        """
        self.annotation = annotation
        self.description = None
        self.title = None

    def is_required(self) -> bool:
        """Return whether the field is required.

        Returns:
            True; the fake field is always treated as required.
        """
        return True

    def get_default(self, *, call_default_factory: Any = False) -> Any:  # noqa: ARG002
        """Return no default value.

        Args:
            call_default_factory: Ignored; present for API compatibility.

        Returns:
            None.
        """
        return None


def _make_fake_field_info(annotation: type) -> _FakeFieldInfo:
    """Create a fake field-info object holding only the given annotation.

    Args:
        annotation: The annotation to attach to the fake field info.

    Returns:
        A ``_FakeFieldInfo`` instance carrying the annotation.
    """
    return _FakeFieldInfo(annotation)


_JSON_SAFE_TYPES = (str, int, float, bool, list, dict, type(None))


def _make_json_safe(value: Any) -> Any:
    """Normalize a value to a JSON-serializable form.

    Args:
        value: The value to normalize.

    Returns:
        The value itself when already JSON-safe, otherwise its string form.
    """
    if value is None:
        return None
    if isinstance(value, _JSON_SAFE_TYPES):
        return value
    return str(value)


def _field_default_to_dict(default_val: Any) -> Any:
    """Convert a Pydantic model default into a plain dict.

    Args:
        default_val: The default value to convert.

    Returns:
        A dict for a model default, or the value itself as-is.
    """
    if default_val is None:
        return None
    if isinstance(default_val, BaseModel):
        try:
            return default_val.model_dump()
        except (AttributeError, TypeError):
            return None
    return default_val


def _reflect_field(field_name: str, field_info: Any) -> FieldNode:
    """Reflect a single Pydantic field into a schema node.

    Args:
        field_name: The field name.
        field_info: The Pydantic ``FieldInfo`` for the field.

    Returns:
        The corresponding schema node for the field.
    """
    annotation = _get_pydantic_type(field_info)
    if annotation is None:
        annotation = str

    is_required = field_info.is_required()
    description = field_info.description or ""
    title = field_info.title or ""

    base_kwargs: dict[str, Any] = {
        "key": field_name,
        "label": title or field_name,
        "description": description,
    }

    is_secret = _is_secret_type(annotation)

    optional = _is_optional(annotation)
    if optional:
        annotation = _unwrap_optional(annotation)

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        children = reflect_model(annotation)
        raw_default = field_info.get_default(call_default_factory=True)
        return ObjectField(
            children=children,
            default=_field_default_to_dict(raw_default),
            **base_kwargs,
        )

    origin = get_origin(annotation)
    if origin in (list, set):
        args = get_args(annotation)
        item_type = args[0] if args else str
        item_schema = _reflect_field("", _make_fake_field_info(item_type))
        return ArrayField(item_schema=item_schema, **base_kwargs)

    if origin is dict:
        args = get_args(annotation)
        value_type = args[1] if len(args) > 1 else str
        value_schema = _reflect_field("", _make_fake_field_info(value_type))
        return MapField(value_schema=value_schema, **base_kwargs)

    ptype = _infer_primitive_type(annotation)
    choices = _extract_choices(annotation)
    default_val = field_info.get_default(call_default_factory=True)

    return PrimitiveField(
        type=ptype,
        default=_make_json_safe(default_val),
        required=is_required and not optional,
        secret=is_secret,
        choices=choices or None,
        **base_kwargs,
    )


def _collect_attr_docstrings(model_cls: type[BaseModel]) -> dict[str, str]:
    """Collect docstrings of a model class and its base classes.

    Args:
        model_cls: The model class to inspect.

    Returns:
        A mapping of attribute names to their extracted docstrings.
    """
    from pydantic._internal._docs_extraction import extract_docstrings_from_cls

    result: dict[str, str] = {}
    for klass in model_cls.__mro__:
        if klass is BaseModel or klass is object:
            continue
        if not (isinstance(klass, type) and issubclass(klass, BaseModel)):
            continue
        docs: dict[str, str] = {}
        for use_inspect in (False, True):
            try:
                extracted = extract_docstrings_from_cls(klass, use_inspect=use_inspect)
            except Exception:  # noqa: BLE001 - pydantic internal API / no source
                continue
            if extracted:
                docs = extracted
                break
        for key, text in docs.items():
            if key not in result and text:
                result[key] = text
    return result


def reflect_model(model_cls: type[BaseModel]) -> list[FieldNode]:
    """Reflect a Pydantic model into a list of field node schemas.

    Args:
        model_cls: The Pydantic model class to reflect.

    Returns:
        A list of ``FieldNode`` instances describing the model's fields.
    """
    docstrings = _collect_attr_docstrings(model_cls)
    fields: list[FieldNode] = []
    for field_name, field_info in model_cls.model_fields.items():
        try:
            node = _reflect_field(field_name, field_info)
        except (TypeError, ValueError, KeyError):
            node = AnyField(
                key=field_name,
                label=field_name,
                description=field_info.description or f"Type: {field_info.annotation}",
            )
        if not node.description and field_name in docstrings:
            node.description = docstrings[field_name]
        fields.append(node)
    return fields
