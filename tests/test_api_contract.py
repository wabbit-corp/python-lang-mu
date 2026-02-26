from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import pytest

import mu
from mu import (
    AtomExpr,
    DecodeContext,
    DecodeError,
    DecoderFn,
    DecoderRegistry,
    DecodeWith,
    Document,
    Expr,
    FieldName,
    GroupExpr,
    MappingExpr,
    MappingField,
    OneOrMore,
    OptionalArg,
    ParseError,
    Quoted,
    SequenceExpr,
    StringExpr,
    ZeroOrMore,
    decode,
    load,
    loads,
    parse,
    parse_many,
    parse_one,
    tag,
)
from mu.exec import EvalContext, EvalNameError, eval_expr


def test_stable_top_level_imports_exist() -> None:
    stable_symbols = [
        ParseError,
        Quoted,
        DecodeContext,
        DecodeError,
        DecodeWith,
        DecoderFn,
        DecoderRegistry,
        FieldName,
        OneOrMore,
        OptionalArg,
        ZeroOrMore,
        AtomExpr,
        Document,
        Expr,
        GroupExpr,
        MappingExpr,
        MappingField,
        SequenceExpr,
        StringExpr,
        decode,
        load,
        loads,
        tag,
        parse_many,
        parse_one,
        parse,
    ]
    assert all(stable_symbols)
    assert isinstance(mu.__version__, str)
    assert mu.__version__


def test_experimental_runtime_imports_exist() -> None:
    assert EvalContext is not None
    assert eval_expr is not None
    assert EvalNameError is not None


@dataclass
class Demo:
    name: str
    aliases: Annotated[list[str], ZeroOrMore]


def test_readme_contract_parser_and_typed_example() -> None:
    parsed = parse('(demo :name "x" :aliases "a" "b")')
    assert isinstance(parsed, Document)
    result = parse_one('(demo :name "x" :aliases "a" "b")', Demo)
    assert result == Demo(name="x", aliases=["a", "b"])


@dataclass
class Counter:
    value: int


def test_readme_contract_error_handling_example() -> None:
    with pytest.raises(DecodeError):
        parse_one('(counter :value "not-an-int")', Counter)
