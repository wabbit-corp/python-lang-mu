from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import pytest

from mu.exec import Quoted
from mu.typed import (
    DecodeContext,
    DecodeError,
    DecoderRegistry,
    DecodeWith,
    FieldName,
    OneOrMore,
    OptionalArg,
    ZeroOrMore,
    parse_many,
    parse_one,
    tag,
)


@dataclass
class AppJvm:
    name: str
    main: str


@dataclass
class AppPy:
    entry: str


@tag("custom-app")
@dataclass
class CustomTagApp:
    value: str


@dataclass
class Person:
    first_name: str
    age: int


@dataclass
class AliasedPerson:
    first_name: Annotated[str, FieldName("display-name")]


@dataclass
class Template:
    content: Quoted[str]


@dataclass
class VariadicCfg:
    name: str
    tags: Annotated[list[str], ZeroOrMore]
    features: Annotated[list[str], OneOrMore]


@dataclass
class OptionalCfg:
    name: str
    nickname: Annotated[str | None, OptionalArg]


@dataclass
class RegistryCfg:
    value: int


@dataclass
class FieldOverrideCfg:
    value: Annotated[int, DecodeWith(lambda _expr, _ctx: 7)]


@dataclass
class Child:
    value: int


@dataclass
class AltChild:
    label: str


@dataclass
class Root:
    child: Child
    items: list[int]
    flags: dict[str, bool]
    node: Child | AltChild


@dataclass
class BoolCfg:
    enabled: bool


@dataclass
class IntCfg:
    count: int


@tag("rooted")
@dataclass
class RootedTag:
    name: str


def test_union_tag_dispatch() -> None:
    result = parse_one('(app-jvm "demo" :main "demo.Main")', AppJvm | AppPy)
    assert isinstance(result, AppJvm)
    assert result == AppJvm(name="demo", main="demo.Main")


def test_union_tag_override() -> None:
    result = parse_one('(custom-app "x")', CustomTagApp | AppJvm)
    assert isinstance(result, CustomTagApp)
    assert result.value == "x"


def test_union_unknown_tag_fails() -> None:
    with pytest.raises(DecodeError):
        parse_one('(unknown-tag "x")', AppJvm | AppPy)


def test_field_name_default_snake_to_kebab() -> None:
    result = parse_one('(person :first-name "alice" :age 32)', Person)
    assert result == Person(first_name="alice", age=32)


def test_field_name_alias_override() -> None:
    result = parse_one('(aliased-person :display-name "alice")', AliasedPerson)
    assert result == AliasedPerson(first_name="alice")


def test_out_of_order_named_then_positional_fails() -> None:
    with pytest.raises(DecodeError) as exc:
        parse_one('(person :age 32 "alice")', Person)
    assert "expected arguments" in str(exc.value)


def test_quoted_str_literal_no_execution() -> None:
    result = parse_one('(template "hello ${name}")', Template)
    assert isinstance(result.content, Quoted)
    assert result.content.value == "hello ${name}"


def test_quoted_str_accepts_atom() -> None:
    result = parse_one('(template hello)', Template)
    assert result.content.value == "hello"


def test_arity_markers_zero_or_more_and_one_or_more() -> None:
    result = parse_one(
        '(variadic-cfg "demo" :tags "a" :tags "b" :features "f1" "f2")',
        VariadicCfg,
    )
    assert result == VariadicCfg(name="demo", tags=["a", "b"], features=["f1", "f2"])


def test_one_or_more_missing_fails() -> None:
    with pytest.raises(DecodeError):
        parse_one('(variadic-cfg "demo")', VariadicCfg)


def test_optional_marker_sets_none_when_omitted() -> None:
    result = parse_one('(optional-cfg "demo")', OptionalCfg)
    assert result == OptionalCfg(name="demo", nickname=None)


def test_custom_deserializer_precedence_field_over_registry() -> None:
    registry = DecoderRegistry()

    def reg_decoder(_expr, _ctx: DecodeContext) -> int:
        return 999

    registry.register(int, reg_decoder)
    result = parse_one('(field-override-cfg 123)', FieldOverrideCfg, registry=registry)
    assert result == FieldOverrideCfg(value=7)


def test_registry_custom_deserializer_used_when_no_field_override() -> None:
    registry = DecoderRegistry()

    def decode_int(expr, _ctx: DecodeContext) -> int:
        from mu.types import AtomExpr, SInt

        if isinstance(expr, SInt):
            return len(str(expr.value))
        assert isinstance(expr, AtomExpr)
        return len(expr.value)

    registry.register(int, decode_int)
    result = parse_one('(registry-cfg 12345)', RegistryCfg, registry=registry)
    assert result == RegistryCfg(value=5)


def test_recursive_nested_decode() -> None:
    source = """
    (root
      :child (child 1)
      :items [1 2 3]
      :flags {enabled: true}
      :node (alt-child :label \"x\"))
    """
    result = parse_one(source, Root)
    assert result == Root(
        child=Child(value=1),
        items=[1, 2, 3],
        flags={"enabled": True},
        node=AltChild(label="x"),
    )


def test_parse_many() -> None:
    source = '(app-jvm "a" :main "A") (app-py "run.py")'
    result = parse_many(source, AppJvm | AppPy)
    assert result == [AppJvm(name="a", main="A"), AppPy(entry="run.py")]


def test_strict_bool_decode_failure() -> None:
    with pytest.raises(DecodeError):
        parse_one('(bool-cfg :enabled yes)', BoolCfg)


def test_strict_int_from_string_failure() -> None:
    with pytest.raises(DecodeError):
        parse_one('(int-cfg :count "42")', IntCfg)


def test_dataclass_requires_tagged_group_not_map() -> None:
    with pytest.raises(DecodeError):
        parse_one('{name: "x"}', RootedTag)


def test_parse_one_requires_exactly_one_toplevel_expression() -> None:
    with pytest.raises(DecodeError):
        parse_one('(rooted "a") (rooted "b")', RootedTag)
