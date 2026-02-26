"""Typed decoding helpers that map Mu AST expressions to Python types."""

from __future__ import annotations

import dataclasses
import re
import types
import typing
from collections.abc import Callable
from dataclasses import MISSING, dataclass
from typing import Annotated, Any, TypeVar, get_args, get_origin

from mu.arg_match import (
    ArgArity,
    MatchArgsException,
    NamedArg,
    PositionalArg,
    match_args,
)
from mu.parser import parse
from mu.quoted import Quoted
from mu.types import (
    AtomExpr,
    Document,
    Expr,
    GroupExpr,
    MappingExpr,
    SequenceExpr,
    SInt,
    SRational,
    SReal,
    StringExpr,
)

T = TypeVar("T")
DecoderFn = Callable[[Expr, "DecodeContext"], Any]


class DecodeError(ValueError):
    """Structured decode error with path/expected/got/span/cause details."""

    def __init__(
        self,
        path: str,
        expected: str,
        got: str,
        span: Any | None = None,
        cause: Exception | None = None,
        message: str | None = None,
    ):
        self.path = path
        self.expected = expected
        self.got = got
        self.span = span
        self.cause = cause
        if message is None:
            message = f"{path}: expected {expected}, got {got}"
            if cause is not None:
                message += f" ({cause})"
        super().__init__(message)


@dataclass(frozen=True)
class FieldName:
    """Annotated marker for overriding a dataclass field's Mu argument name."""

    name: str


@dataclass(frozen=True)
class DecodeWith:
    """Annotated marker for a field-specific custom decode function."""

    fn: DecoderFn


class OptionalArg:
    """Annotated marker for optional field arity (`0..1`)."""

    pass


class ZeroOrMore:
    """Annotated marker for variadic field arity (`0..N`)."""

    pass


class OneOrMore:
    """Annotated marker for required variadic field arity (`1..N`)."""

    pass


@dataclass(frozen=True)
class DecodeContext:
    """Context object passed to custom decoder functions."""

    path: str
    target: Any
    registry: DecoderRegistry

    def decode(self, expr: Expr, target: Any, *, path: str | None = None) -> Any:
        """Decode a nested expression with inherited registry settings."""
        next_path = self.path if path is None else path
        return _decode_value(expr, target, self.registry, next_path)


class DecoderRegistry:
    """Registry of target-type-specific decoder functions."""

    def __init__(self) -> None:
        self._registry: dict[Any, DecoderFn] = {}

    def register(self, target: Any, fn: DecoderFn) -> None:
        """Register a custom decoder function for a target type."""
        self._registry[target] = fn

    def get(self, target: Any) -> DecoderFn | None:
        """Look up a custom decoder function for a target type."""
        return self._registry.get(target)


def tag(tag: str) -> Callable[[type[T]], type[T]]:
    """Decorator that overrides the default dataclass tag used during decoding."""

    def decorator(cls: type[T]) -> type[T]:
        typing.cast(Any, cls).__mu_tag__ = tag
        return cls

    return decorator


@dataclass(frozen=True)
class _FieldSpec:
    field_name: str
    mu_name: str
    type_hint: Any
    base_type: Any
    metadata: tuple[Any, ...]
    arity: ArgArity
    has_default: bool


def parse_one(
    source: str,
    target: Any,
    *,
    registry: DecoderRegistry | None = None,
) -> Any:
    """Parse and decode exactly one top-level Mu expression."""
    decode_registry = registry or DecoderRegistry()
    doc = parse(source, preserve_spans=True)
    if len(doc.exprs) != 1:
        raise DecodeError(
            path="$",
            expected="exactly one top-level expression",
            got=f"{len(doc.exprs)} expressions",
        )
    return _decode_value(doc.exprs[0], target, decode_registry, path="$")


def parse_many(
    source: str,
    target: Any,
    *,
    registry: DecoderRegistry | None = None,
) -> list[Any]:
    """Parse and decode all top-level Mu expressions as a list."""
    decode_registry = registry or DecoderRegistry()
    doc = parse(source, preserve_spans=True)
    return [
        _decode_value(expr, target, decode_registry, path=f"$[{index}]")
        for index, expr in enumerate(doc.exprs)
    ]


def decode(
    expr: Expr,
    target: Any,
    *,
    registry: DecoderRegistry | None = None,
    path: str = "$",
) -> Any:
    """Decode a pre-parsed Mu `Expr` into a target Python type."""
    decode_registry = registry or DecoderRegistry()
    return _decode_value(expr, target, decode_registry, path)


def _decode_value(
    expr: Expr,
    target: Any,
    registry: DecoderRegistry,
    path: str,
) -> Any:
    target_base, metadata = _unwrap_annotated(target)

    custom = _find_metadata(metadata, DecodeWith)
    if custom is not None:
        return _call_deserializer(custom.fn, expr, target_base, registry, path)

    registry_decoder = registry.get(target_base)
    if registry_decoder is not None:
        return _call_deserializer(registry_decoder, expr, target_base, registry, path)

    return _decode_builtin(expr, target_base, registry, path)


def _decode_builtin(
    expr: Expr,
    target: Any,
    registry: DecoderRegistry,
    path: str,
) -> Any:
    if target is Any:
        return _decode_any(expr, registry, path)

    if isinstance(target, type) and issubclass(target, Expr):
        if isinstance(expr, target):
            return expr
        _raise_decode(path, f"{target.__name__}", expr)

    origin = get_origin(target)

    if origin in {typing.Union, types.UnionType}:
        return _decode_union(expr, list(get_args(target)), registry, path)

    if _is_quoted_type(target):
        args = get_args(target)
        quoted_inner = args[0] if args else Any
        return _decode_quoted(expr, quoted_inner, path)

    if isinstance(target, type) and dataclasses.is_dataclass(target):
        return _decode_dataclass(expr, target, registry, path)

    if target is str:
        if isinstance(expr, StringExpr):
            return expr.value
        if isinstance(expr, AtomExpr):
            return expr.value
        _raise_decode(path, "str", expr)

    if target is bool:
        if not isinstance(expr, AtomExpr):
            _raise_decode(path, "bool (atom true/false)", expr)
        value = expr.value.lower()
        if value == "true":
            return True
        if value == "false":
            return False
        _raise_decode(path, "bool (atom true/false)", expr)

    if target is int:
        if isinstance(expr, SInt):
            return expr.value
        if not isinstance(expr, AtomExpr):
            _raise_decode(path, "int atom", expr)
        try:
            return int(expr.value)
        except ValueError as cause:
            _raise_decode(path, "int atom", expr, cause=cause)

    if target is float:
        if isinstance(expr, SReal):
            return expr.value
        if isinstance(expr, SInt):
            return float(expr.value)
        if isinstance(expr, SRational):
            return expr.value[0] / expr.value[1]
        if not isinstance(expr, AtomExpr):
            _raise_decode(path, "float atom", expr)
        try:
            return float(expr.value)
        except ValueError as cause:
            _raise_decode(path, "float atom", expr, cause=cause)

    if origin is list:
        if not isinstance(expr, SequenceExpr):
            _raise_decode(path, "sequence []", expr)
        args = get_args(target)
        item_type = args[0] if args else Any
        return [
            _decode_value(item, item_type, registry, f"{path}[{index}]")
            for index, item in enumerate(expr.values)
        ]

    if origin is dict:
        if not isinstance(expr, MappingExpr):
            _raise_decode(path, "map {}", expr)
        args = get_args(target)
        key_type = args[0] if len(args) >= 1 else Any
        value_type = args[1] if len(args) >= 2 else Any
        result: dict[Any, Any] = {}
        for index, field in enumerate(expr.values):
            key = _decode_value(field.key, key_type, registry, f"{path}.keys[{index}]")
            value = _decode_value(field.value, value_type, registry, f"{path}.values[{index}]")
            try:
                result[key] = value
            except TypeError as cause:
                _raise_decode(path, "hashable map key", expr, cause=cause)
        return result

    if target is Document:
        _raise_decode(path, "Document is not a valid expression target", expr)

    if isinstance(target, type):
        _raise_decode(path, target.__name__, expr)

    _raise_decode(path, str(target), expr)


def _decode_any(expr: Expr, registry: DecoderRegistry, path: str) -> Any:
    if isinstance(expr, SInt):
        return expr.value
    if isinstance(expr, SReal):
        return expr.value
    if isinstance(expr, SRational):
        return expr.value
    if isinstance(expr, AtomExpr):
        return expr.value
    if isinstance(expr, StringExpr):
        return expr.value
    if isinstance(expr, SequenceExpr):
        return [
            _decode_any(item, registry, f"{path}[{index}]")
            for index, item in enumerate(expr.values)
        ]
    if isinstance(expr, MappingExpr):
        result: dict[Any, Any] = {}
        for index, field in enumerate(expr.values):
            key = _decode_any(field.key, registry, f"{path}.keys[{index}]")
            value = _decode_any(field.value, registry, f"{path}.values[{index}]")
            result[key] = value
        return result
    if isinstance(expr, GroupExpr):
        return [
            _decode_any(item, registry, f"{path}[{index}]")
            for index, item in enumerate(expr.values)
        ]
    return expr


def _decode_union(
    expr: Expr,
    union_members: list[Any],
    registry: DecoderRegistry,
    path: str,
) -> Any:
    members: list[Any] = []
    for member in union_members:
        base, _ = _unwrap_annotated(member)
        members.append(base)

    none_member = type(None)
    has_none = any(member is none_member for member in members)

    dataclass_members = [
        member
        for member in members
        if isinstance(member, type) and dataclasses.is_dataclass(member)
    ]
    if dataclass_members and len(dataclass_members) == len(
        [member for member in members if member is not none_member]
    ):
        return _decode_dataclass_union(expr, dataclass_members, path, registry)

    if has_none and _is_none_atom(expr):
        return None

    errors: list[DecodeError] = []
    for member in members:
        if member is none_member:
            continue
        try:
            return _decode_value(expr, member, registry, path)
        except DecodeError as error:
            errors.append(error)

    if errors:
        _raise_decode(
            path,
            " | ".join(_target_name(member) for member in members),
            expr,
            cause=errors[0],
        )

    _raise_decode(path, "non-empty union", expr)


def _decode_dataclass_union(
    expr: Expr,
    members: list[type[Any]],
    path: str,
    registry: DecoderRegistry,
) -> Any:
    if not isinstance(expr, GroupExpr) or not expr.values:
        _raise_decode(path, "tagged group for dataclass union", expr)

    head = expr.values[0]
    if not isinstance(head, AtomExpr):
        _raise_decode(path, "tag atom", head)

    tag_to_type: dict[str, type[Any]] = {}
    for member in members:
        tag = _dataclass_tag(member)
        if tag in tag_to_type and tag_to_type[tag] is not member:
            raise DecodeError(
                path=path,
                expected="unique dataclass union tags",
                got=f"duplicate tag '{tag}'",
            )
        tag_to_type[tag] = member

    selected = tag_to_type.get(head.value)
    if selected is None:
        expected_tags = ", ".join(sorted(tag_to_type))
        _raise_decode(path, f"one of dataclass tags: {expected_tags}", head)

    return _decode_dataclass(expr, selected, registry, path)


def _decode_dataclass(
    expr: Expr,
    target: type[Any],
    registry: DecoderRegistry,
    path: str,
) -> Any:
    if not isinstance(expr, GroupExpr) or not expr.values:
        _raise_decode(path, f"tagged group for {target.__name__}", expr)

    head = expr.values[0]
    if not isinstance(head, AtomExpr):
        _raise_decode(path, f"tag atom for {target.__name__}", head)

    expected_tag = _dataclass_tag(target)
    if head.value != expected_tag:
        _raise_decode(path, f"tag '{expected_tag}'", head)

    specs = _field_specs(target)
    parameters = [(spec.arity, spec.mu_name) for spec in specs]
    arguments = _group_tail_to_match_args(expr.values[1:])

    try:
        assigned = match_args(parameters, arguments)
    except MatchArgsException as cause:
        _raise_decode(path, f"arguments for {target.__name__}", expr, cause=cause)

    kwargs: dict[str, Any] = {}
    for spec in specs:
        raw_values = assigned.get(spec.mu_name, [])

        if spec.arity == ArgArity.Required:
            if len(raw_values) != 1:
                _raise_decode(path, f"single value for '{spec.mu_name}'", expr)
            kwargs[spec.field_name] = _decode_value(
                raw_values[0],
                spec.type_hint,
                registry,
                f"{path}.{spec.field_name}",
            )
            continue

        if spec.arity == ArgArity.Optional:
            if not raw_values:
                if spec.has_default:
                    continue
                kwargs[spec.field_name] = None
            else:
                kwargs[spec.field_name] = _decode_value(
                    raw_values[0],
                    spec.type_hint,
                    registry,
                    f"{path}.{spec.field_name}",
                )
            continue

        item_type = _list_item_type(spec.base_type)
        kwargs[spec.field_name] = [
            _decode_value(value, item_type, registry, f"{path}.{spec.field_name}[{index}]")
            for index, value in enumerate(raw_values)
        ]

    try:
        return target(**kwargs)
    except Exception as cause:  # pragma: no cover - constructor errors are surfaced as decode errors
        _raise_decode(path, f"construct {target.__name__}", expr, cause=cause)


def _group_tail_to_match_args(
    values: list[Expr],
) -> list[NamedArg[str] | PositionalArg[Expr]]:
    result: list[NamedArg[str] | PositionalArg[Expr]] = []
    for value in values:
        if isinstance(value, AtomExpr) and value.value.startswith(":"):
            result.append(NamedArg(value.value[1:]))
        else:
            result.append(PositionalArg(value))
    return result


def _field_specs(target: type[Any]) -> tuple[_FieldSpec, ...]:
    type_hints = typing.get_type_hints(target, include_extras=True)
    specs: list[_FieldSpec] = []

    for field in dataclasses.fields(target):
        hint = type_hints.get(field.name, Any)
        base_type, metadata = _unwrap_annotated(hint)

        name_meta = _find_metadata(metadata, FieldName)
        mu_name = name_meta.name if name_meta is not None else _snake_to_kebab(field.name)

        marker = _pick_arity_marker(metadata)
        has_default = field.default is not MISSING or field.default_factory is not MISSING

        if marker is OptionalArg:
            arity = ArgArity.Optional
        elif marker is ZeroOrMore:
            arity = ArgArity.ZeroOrMore
        elif marker is OneOrMore:
            arity = ArgArity.OneOrMore
        else:
            arity = ArgArity.Optional if has_default else ArgArity.Required

        if arity in {ArgArity.ZeroOrMore, ArgArity.OneOrMore}:
            origin = get_origin(base_type)
            if origin is not list:
                raise TypeError(
                    f"Field '{field.name}' uses vararg marker but type is not list[T]: {base_type}"
                )

        specs.append(
            _FieldSpec(
                field_name=field.name,
                mu_name=mu_name,
                type_hint=hint,
                base_type=base_type,
                metadata=tuple(metadata),
                arity=arity,
                has_default=has_default,
            )
        )

    return tuple(specs)


def _list_item_type(target: Any) -> Any:
    origin = get_origin(target)
    if origin is not list:
        return Any
    args = get_args(target)
    return args[0] if args else Any


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


def _find_metadata(metadata: list[Any], target_type: type[T]) -> T | None:
    found: T | None = None
    for item in metadata:
        if isinstance(item, target_type):
            if found is not None:
                raise TypeError(f"Multiple {target_type.__name__} annotations are not allowed")
            found = item
    return found


def _is_marker(item: Any, marker: type[Any]) -> bool:
    return item is marker or isinstance(item, marker)


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


def _call_deserializer(
    fn: DecoderFn,
    expr: Expr,
    target: Any,
    registry: DecoderRegistry,
    path: str,
) -> Any:
    context = DecodeContext(path=path, target=target, registry=registry)
    try:
        return fn(expr, context)
    except DecodeError:
        raise
    except Exception as cause:
        _raise_decode(path, f"custom deserializer for {_target_name(target)}", expr, cause=cause)


def _decode_quoted(expr: Expr, inner: Any, path: str) -> Any:
    if inner is str:
        if isinstance(expr, StringExpr):
            return Quoted(expr.value)
        if isinstance(expr, AtomExpr):
            return Quoted(expr.value)
        _raise_decode(path, "Quoted[str]", expr)

    if isinstance(inner, type) and issubclass(inner, Expr):
        if isinstance(expr, inner):
            return Quoted(expr)
        _raise_decode(path, f"Quoted[{inner.__name__}]", expr)

    _raise_decode(path, "Quoted[str] or Quoted[Expr subtype]", expr)


def _is_quoted_type(target: Any) -> bool:
    return get_origin(target) is Quoted


def _target_name(target: Any) -> str:
    if isinstance(target, type):
        return target.__name__
    return str(target)


def _is_none_atom(expr: Expr) -> bool:
    return isinstance(expr, AtomExpr) and expr.value.lower() in {"none", "null"}


def _describe_expr(expr: Any) -> str:
    if isinstance(expr, SInt):
        return f"int({expr.value!r})"
    if isinstance(expr, SReal):
        return f"real({expr.value!r})"
    if isinstance(expr, SRational):
        return f"rational({expr.value[0]!r}/{expr.value[1]!r})"
    if isinstance(expr, AtomExpr):
        return f"atom({expr.value!r})"
    if isinstance(expr, StringExpr):
        return f"string({expr.value!r})"
    if isinstance(expr, GroupExpr):
        return "group(...)"
    if isinstance(expr, SequenceExpr):
        return "seq[...]"
    if isinstance(expr, MappingExpr):
        return "map{...}"
    return type(expr).__name__


def _extract_span(expr: Any) -> Any | None:
    if isinstance(expr, (AtomExpr, StringExpr, SInt, SReal, SRational)):
        span = expr.span
        if span is None:
            return None
        token = getattr(span, "token", None)
        return token if token is not None else span

    for attr in ("open_bracket", "span"):
        value = getattr(expr, attr, None)
        if value is not None:
            token = getattr(value, "token", None)
            return token if token is not None else value

    return None


def _raise_decode(
    path: str,
    expected: str,
    expr: Any,
    cause: Exception | None = None,
) -> typing.NoReturn:
    raise DecodeError(
        path=path,
        expected=expected,
        got=_describe_expr(expr),
        span=_extract_span(expr),
        cause=cause,
    )


__all__ = [
    "DecodeContext",
    "DecodeError",
    "DecodeWith",
    "DecoderFn",
    "DecoderRegistry",
    "FieldName",
    "OneOrMore",
    "OptionalArg",
    "ZeroOrMore",
    "decode",
    "tag",
    "parse_many",
    "parse_one",
]
