"""Config field node schema definitions for the configuration contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PrimitiveType = Literal["str", "int", "float", "bool", "enum", "literal"]


def coerce_primitive_type(value: object) -> PrimitiveType:
    """Coerce a value to a valid primitive type name.

    Args:
        value: The value to coerce.

    Returns:
        The matching primitive type name, defaulting to ``"str"``.
    """
    match str(value):
        case "int":
            return "int"
        case "float":
            return "float"
        case "bool":
            return "bool"
        case "enum":
            return "enum"
        case "literal":
            return "literal"
        case _:
            return "str"


@dataclass
class FieldNode:
    """Base node representing a single configuration field.

    Holds common metadata such as the key, label, description, order, and
    immutability flag. Subclasses implement the concrete field kinds.
    """

    kind: str
    key: str = ""
    label: str = ""
    description: str = ""
    order: int = 0
    immutable: bool = False

    def _base_dict(self) -> dict[str, Any]:
        """Return the common metadata fields as a dictionary."""
        return {
            "kind": self.kind,
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "order": self.order,
            "immutable": self.immutable,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize the field node to a dictionary.

        Raises:
            NotImplementedError: Always; subclasses implement this method.
        """
        raise NotImplementedError


@dataclass
class PrimitiveField(FieldNode):
    """A field node for a primitive value such as a string, int, or bool."""

    kind: str = "primitive"
    type: PrimitiveType = "str"
    default: Any = None
    required: bool = True
    secret: bool = False
    choices: list[dict[str, str]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary with primitive-specific metadata."""
        d = self._base_dict()
        d.update(
            {
                "type": self.type,
                "default": self.default,
                "required": self.required,
                "secret": self.secret,
            }
        )
        if self.choices is not None:
            d["choices"] = self.choices
        return d


@dataclass
class ObjectField(FieldNode):
    """A field node for a nested object with child field nodes."""

    kind: str = "object"
    children: list[FieldNode] = field(default_factory=list)
    default: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary including each child field node dict."""
        d = self._base_dict()
        d["children"] = [child.to_dict() for child in self.children]
        if self.default is not None:
            d["default"] = self.default
        return d


@dataclass
class ArrayField(FieldNode):
    """A field node for an array of items described by an item schema."""

    kind: str = "array"
    item_schema: FieldNode | None = None
    default: list[Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary including the item schema dict."""
        d = self._base_dict()
        if self.item_schema is not None:
            d["item_schema"] = self.item_schema.to_dict()
        if self.default is not None:
            d["default"] = self.default
        return d


@dataclass
class MapField(FieldNode):
    """A field node for a string-keyed map with a value schema."""

    kind: str = "map"
    key_type: str = "str"
    value_schema: FieldNode | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary including the value schema dict."""
        d = self._base_dict()
        d["key_type"] = self.key_type
        if self.value_schema is not None:
            d["value_schema"] = self.value_schema.to_dict()
        return d


@dataclass
class AnyField(FieldNode):
    """A field node for an unrestricted arbitrary value."""

    kind: str = "any"
    default: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary including the default value."""
        d = self._base_dict()
        d["default"] = self.default
        return d


@dataclass
class ConfigContract:
    """A reflected configuration contract for a single owner.

    Describes the namespace, scoping flag, owner kind and id, contract
    source, field nodes, JSON schema, and aliases for one plugin, adapter,
    or system block.
    """

    namespace: str | None
    is_scoped: bool
    owner_kind: Literal["plugin", "adapter", "nonebot", "apeiria"]
    owner_id: str
    source: Literal["pydantic", "extra_only", "none"]
    fields: list[FieldNode]
    json_schema: dict[str, Any]
    aliases: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the contract to a dictionary."""
        return {
            "namespace": self.namespace,
            "is_scoped": self.is_scoped,
            "owner_kind": self.owner_kind,
            "owner_id": self.owner_id,
            "source": self.source,
            "fields": [f.to_dict() for f in self.fields],
            "json_schema": self.json_schema,
            "aliases": self.aliases,
        }
