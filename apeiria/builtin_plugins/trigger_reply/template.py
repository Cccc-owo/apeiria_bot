from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class _Text:
    text: str


@dataclass(frozen=True)
class _Variable:
    name: str
    default: str | None = None


@dataclass(frozen=True)
class _If:
    var: str
    body: tuple[_Node, ...]
    orelse: tuple[_Node, ...] = ()


type _Node = _Text | _Variable | _If


class _TemplateSyntaxError(ValueError):
    pass


class _Parser:
    def __init__(self, source: str) -> None:
        self._source = source
        self._pos = 0

    def parse(self) -> tuple[_Node, ...]:
        nodes, stop = self._parse_until(frozenset())
        if stop is not None:
            msg = f"unexpected tag: {stop}"
            raise _TemplateSyntaxError(msg)
        return tuple(nodes)

    def _parse_until(  # noqa: C901, PLR0912, PLR0915
        self, stop: frozenset[str]
    ) -> tuple[list[_Node], str | None]:
        nodes: list[_Node] = []
        source = self._source

        while True:
            idx = source.find("{", self._pos)
            if idx == -1:
                if self._pos < len(source):
                    nodes.append(_Text(source[self._pos :]))
                self._pos = len(source)
                if stop:
                    msg = f"missing one of tags: {', '.join(sorted(stop))}"
                    raise _TemplateSyntaxError(msg)
                return nodes, None

            if idx > self._pos:
                nodes.append(_Text(source[self._pos : idx]))
                self._pos = idx

            if source.startswith("{%", self._pos):
                end = source.find("%}", self._pos + 2)
                if end == -1:
                    msg = "unclosed block tag"
                    raise _TemplateSyntaxError(msg)
                tag = source[self._pos + 2 : end].strip()
                self._pos = end + 2

                if tag in stop:
                    return nodes, tag

                if tag.startswith("if "):
                    var = tag[3:].strip()
                    if not var:
                        msg = "if tag requires a variable name"
                        raise _TemplateSyntaxError(msg)
                    body, body_stop = self._parse_until(frozenset({"else", "endif"}))
                    orelse: list[_Node] = []
                    if body_stop == "else":
                        orelse, end_stop = self._parse_until(frozenset({"endif"}))
                        if end_stop != "endif":
                            msg = "if block is missing endif"
                            raise _TemplateSyntaxError(msg)
                    elif body_stop != "endif":
                        msg = "if block is missing endif"
                        raise _TemplateSyntaxError(msg)
                    nodes.append(_If(var, tuple(body), tuple(orelse)))
                    continue

                msg = f"unknown template tag: {tag}"
                raise _TemplateSyntaxError(msg)

            end = source.find("}", self._pos + 1)
            if end == -1:
                msg = "unclosed variable tag"
                raise _TemplateSyntaxError(msg)
            content = source[self._pos + 1 : end].strip()
            self._pos = end + 1
            if not content:
                msg = "empty variable tag"
                raise _TemplateSyntaxError(msg)
            if "|" in content:
                name, default = content.split("|", 1)
                name = name.strip()
                default = default.strip()
            else:
                name = content
                default = None
            if not name.isidentifier():
                msg = f"invalid variable name: {name!r}"
                raise _TemplateSyntaxError(msg)
            nodes.append(_Variable(name, default))


@lru_cache(maxsize=1024)
def _compile(template: str) -> tuple[_Node, ...]:
    return _Parser(template).parse()


def _render_nodes(nodes: tuple[_Node, ...], context: Mapping[str, object]) -> str:
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, _Text):
            parts.append(node.text)
        elif isinstance(node, _Variable):
            value = context.get(node.name)
            if value is None or value == "":
                default = node.default
                parts.append(default if default is not None else f"{{{node.name}}}")
            else:
                parts.append(str(value))
        else:
            value = context.get(node.var)
            if value is not None and value != "" and bool(value):
                parts.append(_render_nodes(node.body, context))
            else:
                parts.append(_render_nodes(node.orelse, context))
    return "".join(parts)


def render_template(template: str, context: Mapping[str, object]) -> str:
    return _render_nodes(_compile(template), context)
