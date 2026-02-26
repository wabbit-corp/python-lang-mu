"""Mu serialization and formatting helpers.

This module provides `json.dumps`-style APIs for rendering Python values and
Mu AST nodes to Mu source text in either concise or pretty form.
"""

from __future__ import annotations

import dataclasses
import re
import typing
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated, Any, get_args, get_origin

from mu.quoted import Quoted
from mu.typed import FieldName, OneOrMore, OptionalArg, ZeroOrMore
from mu.types import (
    AtomExpr,
    Document,
    Expr,
    GroupExpr,
    MappingExpr,
    MappingField,
    SequenceExpr,
    StringExpr,
    TokenSpans,
)

_DEFAULT_POSITIONAL_FIRST_FIELD_NAMES = frozenset({"id", "name"})
_ATOM_RE = re.compile(r"^[^\s\(\)\[\]\{\}\",;]+$")


def dumps(
    value: Any,
    *,
    indent: int | None = None,
    max_line_length: int = 88,
    positional_first_id_or_name: bool = False,
    positional_first_field_names: Iterable[str] | None = None,
    positional_single_field: bool = True,
    preserve_spans: bool = True,
) -> str:
    """Serialize a value to Mu source text.

    Args:
        value: Value to serialize. Supports Mu AST nodes, dataclass instances,
            and common Python container/scalar types.
        indent: Pretty indentation width. If `None`, concise mode is used.
        max_line_length: Preferred maximum line width before multiline layout.
        positional_first_id_or_name: When `True`, dataclass groups may render
            the first field positionally when its field name matches
            `positional_first_field_names`.
        positional_first_field_names: Field names that may be rendered
            positionally for the first dataclass field when
            `positional_first_id_or_name=True`.
        positional_single_field: When `True`, single-field dataclasses are
            rendered positionally (for example `(include "path")`).
        preserve_spans: When `True`, AST inputs with complete span metadata are
            rendered from source spans to preserve original formatting.
    """
    if max_line_length < 20:
        raise ValueError("max_line_length must be >= 20")

    pretty = indent is not None
    indent_width = 2 if indent is None else indent
    if indent_width <= 0:
        raise ValueError("indent must be > 0 when provided")
    positional_names = (
        _DEFAULT_POSITIONAL_FIRST_FIELD_NAMES
        if positional_first_field_names is None
        else frozenset(positional_first_field_names)
    )

    settings = _SerializeSettings(
        positional_first_id_or_name=positional_first_id_or_name,
        positional_first_field_names=positional_names,
        positional_single_field=positional_single_field,
        preserve_spans=preserve_spans,
    )
    doc = _to_document(value, settings=settings)

    formatter = _Formatter(
        pretty=pretty,
        indent=indent_width,
        max_line_length=max_line_length,
        preserve_spans=preserve_spans,
    )
    return formatter.format_document(doc)


def dumps_pretty(
    value: Any,
    *,
    indent: int = 2,
    max_line_length: int = 88,
    positional_first_id_or_name: bool = False,
    positional_first_field_names: Iterable[str] | None = None,
    positional_single_field: bool = True,
    preserve_spans: bool = True,
) -> str:
    """Serialize a value using pretty multiline formatting."""
    return dumps(
        value,
        indent=indent,
        max_line_length=max_line_length,
        positional_first_id_or_name=positional_first_id_or_name,
        positional_first_field_names=positional_first_field_names,
        positional_single_field=positional_single_field,
        preserve_spans=preserve_spans,
    )


def dumps_concise(
    value: Any,
    *,
    max_line_length: int = 88,
    positional_first_id_or_name: bool = False,
    positional_first_field_names: Iterable[str] | None = None,
    positional_single_field: bool = True,
    preserve_spans: bool = True,
) -> str:
    """Serialize a value using concise formatting."""
    return dumps(
        value,
        indent=None,
        max_line_length=max_line_length,
        positional_first_id_or_name=positional_first_id_or_name,
        positional_first_field_names=positional_first_field_names,
        positional_single_field=positional_single_field,
        preserve_spans=preserve_spans,
    )


@dataclass(frozen=True)
class _SerializeSettings:
    positional_first_id_or_name: bool
    positional_first_field_names: frozenset[str]
    positional_single_field: bool
    preserve_spans: bool


@dataclass(frozen=True)
class _FieldSpec:
    field_name: str
    mu_name: str
    marker: type[Any] | None


def _to_document(value: Any, *, settings: _SerializeSettings) -> Document:
    if isinstance(value, Document):
        return value if settings.preserve_spans else value.drop_spans()

    if isinstance(value, Expr):
        expr = value if settings.preserve_spans else value.drop_spans()
        return Document([expr])

    if _is_top_level_expr_list(value):
        return Document([_encode_expr(v, context="field", settings=settings) for v in value])

    return Document([_encode_expr(value, context="field", settings=settings)])


def _is_top_level_expr_list(value: Any) -> bool:
    if not isinstance(value, (list, tuple)):
        return False
    if not value:
        return False
    return all(isinstance(item, Expr) or dataclasses.is_dataclass(item) for item in value)


def _encode_expr(value: Any, *, context: str, settings: _SerializeSettings) -> Expr:
    if isinstance(value, Expr):
        return value if settings.preserve_spans else value.drop_spans()

    if isinstance(value, Quoted):
        return _encode_expr(value.value, context=context, settings=settings)

    if dataclasses.is_dataclass(value):
        return _encode_dataclass(value, settings=settings)

    if value is None:
        return AtomExpr("none")
    if isinstance(value, bool):
        return AtomExpr("true" if value else "false")
    if isinstance(value, int):
        return AtomExpr(str(value))
    if isinstance(value, float):
        return AtomExpr(repr(value))
    if isinstance(value, str):
        return _encode_string(value, context=context)
    if isinstance(value, (list, tuple)):
        return SequenceExpr(
            [
                _encode_expr(item, context="sequence", settings=settings)
                for item in value
            ]
        )
    if isinstance(value, dict):
        fields = []
        for key, item in value.items():
            key_expr = _encode_expr(key, context="map_key", settings=settings)
            value_expr = _encode_expr(item, context="map_value", settings=settings)
            fields.append(MappingField(key=key_expr, value=value_expr))
        return MappingExpr(fields)

    return AtomExpr(str(value))


def _encode_string(value: str, *, context: str) -> Expr:
    if context == "field":
        return StringExpr(value)
    if _is_atom_text(value):
        return AtomExpr(value)
    return StringExpr(value)


def _is_atom_text(value: str) -> bool:
    return bool(value) and _ATOM_RE.fullmatch(value) is not None


def _encode_dataclass(value: Any, *, settings: _SerializeSettings) -> GroupExpr:
    target = type(value)
    fields = _collect_dataclass_fields(target, value, settings=settings)
    values: list[Expr] = [AtomExpr(_dataclass_tag(target))]

    if not fields:
        return GroupExpr(values=values)

    positional = _positional_fields(fields, settings=settings)

    for spec, encoded_values in fields:
        if spec.field_name in positional:
            values.extend(encoded_values)
            continue
        values.append(AtomExpr(f":{spec.mu_name}"))
        values.extend(encoded_values)

    return GroupExpr(values=values)


def _collect_dataclass_fields(
    target: type[Any],
    value: Any,
    *,
    settings: _SerializeSettings,
) -> list[tuple[_FieldSpec, list[Expr]]]:
    specs = _field_specs(target)
    result: list[tuple[_FieldSpec, list[Expr]]] = []
    for spec in specs:
        raw = getattr(value, spec.field_name)

        if spec.marker is OptionalArg and raw is None:
            continue

        if spec.marker in {ZeroOrMore, OneOrMore}:
            if not isinstance(raw, (list, tuple)):
                raise TypeError(
                    f"Field '{spec.field_name}' uses a vararg marker but value is not a sequence"
                )
            if spec.marker is OneOrMore and len(raw) == 0:
                raise ValueError(f"Field '{spec.field_name}' uses OneOrMore but value is empty")
            if len(raw) == 0:
                continue
            encoded = [
                _encode_expr(item, context="field", settings=settings)
                for item in raw
            ]
            result.append((spec, encoded))
            continue

        encoded_value = _encode_expr(raw, context="field", settings=settings)
        result.append((spec, [encoded_value]))

    return result


def _positional_fields(
    fields: list[tuple[_FieldSpec, list[Expr]]],
    *,
    settings: _SerializeSettings,
) -> set[str]:
    if not fields:
        return set()
    if settings.positional_single_field and len(fields) == 1:
        return {fields[0][0].field_name}

    if settings.positional_first_id_or_name:
        first = fields[0][0]
        names = {first.field_name, first.mu_name}
        if names & settings.positional_first_field_names:
            return {first.field_name}
    return set()


def _field_specs(target: type[Any]) -> list[_FieldSpec]:
    type_hints = typing.get_type_hints(target, include_extras=True)
    specs: list[_FieldSpec] = []
    for field in dataclasses.fields(target):
        hint = type_hints.get(field.name, Any)
        _, metadata = _unwrap_annotated(hint)

        name_meta = _find_metadata(metadata, FieldName)
        mu_name = name_meta.name if name_meta is not None else _snake_to_kebab(field.name)
        marker = _pick_arity_marker(metadata)

        specs.append(
            _FieldSpec(
                field_name=field.name,
                mu_name=mu_name,
                marker=marker,
            )
        )
    return specs


def _unwrap_annotated(target: Any) -> tuple[Any, list[Any]]:
    metadata: list[Any] = []
    current = target
    while get_origin(current) is Annotated:
        args = list(get_args(current))
        if not args:
            break
        current = args[0]
        metadata.extend(args[1:])
    return current, metadata


def _find_metadata(metadata: list[Any], target_type: type[Any]) -> Any | None:
    found: Any | None = None
    for item in metadata:
        if isinstance(item, target_type):
            if found is not None:
                raise TypeError(f"Multiple {target_type.__name__} annotations are not allowed")
            found = item
    return found


def _pick_arity_marker(metadata: list[Any]) -> type[Any] | None:
    markers: list[type[Any]] = []
    if any(_is_marker(item, OptionalArg) for item in metadata):
        markers.append(OptionalArg)
    if any(_is_marker(item, ZeroOrMore) for item in metadata):
        markers.append(ZeroOrMore)
    if any(_is_marker(item, OneOrMore) for item in metadata):
        markers.append(OneOrMore)
    if len(markers) > 1:
        names = ", ".join(marker.__name__ for marker in markers)
        raise TypeError(f"At most one arity marker is allowed, found: {names}")
    return markers[0] if markers else None


def _is_marker(item: Any, marker: type[Any]) -> bool:
    return item is marker or isinstance(item, marker)


def _dataclass_tag(target: type[Any]) -> str:
    override = getattr(target, "__mu_tag__", None)
    if override is not None:
        return str(override)
    return _snake_to_kebab(_camel_to_snake(target.__name__))


def _camel_to_snake(name: str) -> str:
    step1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", step1).lower()


def _snake_to_kebab(name: str) -> str:
    return name.replace("_", "-")


class _Formatter:
    def __init__(
        self,
        *,
        pretty: bool,
        indent: int,
        max_line_length: int,
        preserve_spans: bool,
    ) -> None:
        self.pretty = pretty
        self.indent = indent
        self.max_line_length = max_line_length
        self.preserve_spans = preserve_spans

    def format_document(self, doc: Document) -> str:
        if self.preserve_spans:
            return self._format_document_preserving_spans(doc)
        parts = [self._format_expr_no_spans(expr, level=0) for expr in doc.exprs]
        if self.pretty:
            return "\n\n".join(parts)
        return "\n".join(parts)

    def _format_document_preserving_spans(self, doc: Document) -> str:
        result = ""
        if doc.leading_space is not None:
            result += doc.leading_space.raw

        for index, expr in enumerate(doc.exprs):
            result += self._render_expr_with_spans(expr, level=0)
            if index < len(doc.exprs) - 1 and not result.endswith((" ", "\n", "\t", "\r")):
                result += "\n\n" if self.pretty else "\n"
        return result

    def _render_expr_with_spans(self, expr: Expr, *, level: int) -> str:
        if isinstance(expr, (AtomExpr, StringExpr)):
            if _complete_token_spans(expr.span):
                return str(expr)
            return self._format_expr_no_spans(expr, level=level)

        if isinstance(expr, GroupExpr):
            return self._render_group_with_spans(expr, level=level)

        if isinstance(expr, SequenceExpr):
            return self._render_sequence_with_spans(expr, level=level)

        if isinstance(expr, MappingExpr):
            return self._render_map_with_spans(expr, level=level)

        return self._format_expr_no_spans(expr, level=level)

    def _render_group_with_spans(self, expr: GroupExpr, *, level: int) -> str:
        if expr.open_bracket is None and expr.close_bracket is None and expr.separators is None:
            return self._format_expr_no_spans(expr, level=level)

        open_text = str(expr.open_bracket) if _complete_token_spans(expr.open_bracket) else "("
        close_text = str(expr.close_bracket) if _complete_token_spans(expr.close_bracket) else ")"
        seps = expr.separators or []

        result = open_text
        for i, value in enumerate(expr.values):
            child_has_spans = _has_any_spans_expr(value)
            result += self._render_expr_with_spans(value, level=level + 1)
            sep = seps[i] if i < len(seps) else None
            if _complete_token_spans(sep):
                sep_text = str(sep)
                if sep_text == "" and i < len(expr.values) - 1 and not child_has_spans:
                    sep_text = " "
                result += sep_text
            elif i < len(expr.values) - 1:
                result += " "
        result += close_text
        return result

    def _render_sequence_with_spans(self, expr: SequenceExpr, *, level: int) -> str:
        if expr.open_bracket is None and expr.close_bracket is None and expr.separators is None:
            return self._format_expr_no_spans(expr, level=level)

        open_text = str(expr.open_bracket) if _complete_token_spans(expr.open_bracket) else "["
        close_text = str(expr.close_bracket) if _complete_token_spans(expr.close_bracket) else "]"
        seps = expr.separators or []

        result = open_text
        for i, value in enumerate(expr.values):
            child_has_spans = _has_any_spans_expr(value)
            result += self._render_expr_with_spans(value, level=level + 1)
            sep = seps[i] if i < len(seps) else None
            if _complete_token_spans(sep):
                sep_text = str(sep)
                if sep_text == "" and i < len(expr.values) - 1 and not child_has_spans:
                    sep_text = " "
                result += sep_text
            elif i < len(expr.values) - 1:
                result += " "
        result += close_text
        return result

    def _render_map_with_spans(self, expr: MappingExpr, *, level: int) -> str:
        if expr.open_bracket is None and expr.close_bracket is None and expr.separators is None:
            return self._format_expr_no_spans(expr, level=level)

        open_text = str(expr.open_bracket) if _complete_token_spans(expr.open_bracket) else "{"
        close_text = str(expr.close_bracket) if _complete_token_spans(expr.close_bracket) else "}"
        seps = expr.separators or []

        result = open_text
        for i, field in enumerate(expr.values):
            key_has_spans = _has_any_spans_expr(field.key)
            result += self._render_expr_with_spans(field.key, level=level + 1)
            if _complete_token_spans(field.separator):
                sep_text = str(field.separator)
                if sep_text == "" and not key_has_spans:
                    sep_text = ": "
                result += sep_text
            else:
                result += ": "
            result += self._render_expr_with_spans(field.value, level=level + 1)

            sep = seps[i] if i < len(seps) else None
            if _complete_token_spans(sep):
                sep_text = str(sep)
                if sep_text == "" and i < len(expr.values) - 1:
                    sep_text = ", "
                result += sep_text
            elif i < len(expr.values) - 1:
                result += ", "

        result += close_text
        return result

    def _format_expr_no_spans(self, expr: Expr, *, level: int) -> str:
        if self.pretty:
            return self._format_expr_pretty(expr, level=level)
        return self._format_expr_concise(expr, level=level)

    def _format_expr_concise(self, expr: Expr, *, level: int) -> str:
        inline = self._inline_expr(expr)
        if len(inline) <= self._budget(level):
            return inline
        return self._format_expr_pretty(expr, level=level)

    def _format_expr_pretty(self, expr: Expr, *, level: int) -> str:
        inline = self._inline_expr(expr)
        if len(inline) <= self._budget(level) and self._can_inline(expr):
            return inline

        if isinstance(expr, GroupExpr):
            return self._format_group(expr, level=level)
        if isinstance(expr, SequenceExpr):
            return self._format_sequence(expr, level=level)
        if isinstance(expr, MappingExpr):
            return self._format_map(expr, level=level)
        return inline

    def _format_group(self, expr: GroupExpr, *, level: int) -> str:
        if not expr.values:
            return "()"

        head = expr.values[0]
        args = expr.values[1:]
        inline = self._inline_expr(expr)
        if len(inline) <= self._budget(level):
            return inline

        parsed = self._parse_named_args(args)
        positional = parsed[0]
        named = parsed[1]

        head_text = self._inline_expr(head)
        start_tokens = [head_text] + [self._format_expr_concise(v, level=level) for v in positional]
        lines = ["(" + " ".join(start_tokens)]

        for name, values in named:
            field_lines = self._format_named_field(name, values, level=level + 1)
            lines.extend(self._indent_lines(field_lines, levels=1))

        lines.append(")")
        return "\n".join(lines)

    def _format_named_field(self, name: str, values: list[Expr], *, level: int) -> list[str]:
        if not values:
            return [f":{name}"]

        rendered = [self._format_expr_no_spans(v, level=level) for v in values]
        if all("\n" not in text for text in rendered):
            candidate = f":{name} " + " ".join(rendered)
            if len(candidate) <= self._budget(level):
                return [candidate]

        if len(rendered) == 1:
            lines = rendered[0].splitlines()
            first = f":{name} {lines[0]}"
            return [first, *lines[1:]]

        result = [f":{name}"]
        for text in rendered:
            result.extend(self._indent_lines(text.splitlines(), levels=1))
        return result

    def _format_sequence(self, expr: SequenceExpr, *, level: int) -> str:
        if not expr.values:
            return "[]"

        inline = self._inline_expr(expr)
        if len(inline) <= self._budget(level) and self._can_inline_sequence(expr):
            return inline

        lines = ["["]
        for value in expr.values:
            value_lines = self._format_expr_no_spans(value, level=level + 1).splitlines()
            lines.extend(self._indent_lines(value_lines, levels=1))
        lines.append("]")
        return "\n".join(lines)

    def _format_map(self, expr: MappingExpr, *, level: int) -> str:
        if not expr.values:
            return "{}"

        inline = self._inline_expr(expr)
        if len(inline) <= self._budget(level) and self._can_inline_map(expr):
            return inline

        lines = ["{"]
        for index, field in enumerate(expr.values):
            suffix = "," if index < len(expr.values) - 1 else ""
            key_text = self._format_expr_concise(field.key, level=level + 1)
            value_text = self._format_expr_no_spans(field.value, level=level + 1)
            value_lines = value_text.splitlines()
            if len(value_lines) == 1:
                lines.append(f"{self._indent(1)}{key_text}: {value_lines[0]}{suffix}")
                continue
            lines.append(f"{self._indent(1)}{key_text}: {value_lines[0]}")
            lines.extend(self._indent_lines(value_lines[1:], levels=1))
            if suffix:
                lines[-1] = f"{lines[-1]}{suffix}"
        lines.append("}")
        return "\n".join(lines)

    def _parse_named_args(self, values: list[Expr]) -> tuple[list[Expr], list[tuple[str, list[Expr]]]]:
        positional: list[Expr] = []
        named: list[tuple[str, list[Expr]]] = []
        current_name: str | None = None
        current_values: list[Expr] = []

        for value in values:
            if isinstance(value, AtomExpr) and value.value.startswith(":"):
                if current_name is not None:
                    named.append((current_name, current_values))
                current_name = value.value[1:]
                current_values = []
                continue

            if current_name is None:
                positional.append(value)
            else:
                current_values.append(value)

        if current_name is not None:
            named.append((current_name, current_values))

        return positional, named

    def _can_inline(self, expr: Expr) -> bool:
        if isinstance(expr, MappingExpr):
            return len(expr.values) <= 1
        if isinstance(expr, SequenceExpr):
            return self._can_inline_sequence(expr)
        return True

    def _can_inline_sequence(self, expr: SequenceExpr) -> bool:
        if not expr.values:
            return True
        if len(expr.values) > 8:
            return False
        if not all(isinstance(v, (AtomExpr, StringExpr)) for v in expr.values):
            return False
        first_type = type(expr.values[0])
        return all(type(v) is first_type for v in expr.values)

    def _can_inline_map(self, expr: MappingExpr) -> bool:
        if len(expr.values) <= 1:
            return True
        if not self.pretty:
            return True
        return False

    def _budget(self, level: int) -> int:
        return self.max_line_length - (self.indent * level)

    def _inline_expr(self, expr: Expr) -> str:
        if isinstance(expr, AtomExpr):
            return expr.value
        if isinstance(expr, StringExpr):
            return _quote_string(expr.value)
        if isinstance(expr, GroupExpr):
            inner = " ".join(self._inline_expr(item) for item in expr.values)
            return f"({inner})"
        if isinstance(expr, SequenceExpr):
            inner = " ".join(self._inline_expr(item) for item in expr.values)
            return f"[{inner}]"
        if isinstance(expr, MappingExpr):
            parts = [
                f"{self._inline_expr(field.key)}: {self._inline_expr(field.value)}"
                for field in expr.values
            ]
            return "{" + ", ".join(parts) + "}"
        raise TypeError(f"Unsupported expression type: {type(expr).__name__}")

    def _indent(self, levels: int) -> str:
        return " " * (self.indent * levels)

    def _indent_lines(self, lines: list[str], *, levels: int) -> list[str]:
        prefix = self._indent(levels)
        return [f"{prefix}{line}" if line else prefix for line in lines]


def _quote_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("\r", "\\r")
        .replace("\0", "\\0")
        .replace('"', '\\"')
    )
    return f'"{escaped}"'


def _complete_token_spans(spans: TokenSpans | None) -> bool:
    if spans is None:
        return False
    return spans.token is not None and spans.space is not None


def _has_any_spans_expr(expr: Expr) -> bool:
    if isinstance(expr, (AtomExpr, StringExpr)):
        return expr.span is not None
    if isinstance(expr, GroupExpr):
        return (
            expr.open_bracket is not None
            or expr.close_bracket is not None
            or expr.separators is not None
            or any(_has_any_spans_expr(value) for value in expr.values)
        )
    if isinstance(expr, SequenceExpr):
        return (
            expr.open_bracket is not None
            or expr.close_bracket is not None
            or expr.separators is not None
            or any(_has_any_spans_expr(value) for value in expr.values)
        )
    if isinstance(expr, MappingExpr):
        return (
            expr.open_bracket is not None
            or expr.close_bracket is not None
            or expr.separators is not None
            or any(
                field.separator is not None
                or _has_any_spans_expr(field.key)
                or _has_any_spans_expr(field.value)
                for field in expr.values
            )
        )
    return False


__all__ = ["dumps", "dumps_concise", "dumps_pretty"]
