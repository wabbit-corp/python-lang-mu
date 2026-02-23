from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import pytest

import mu
from mu import (
    MuDecodeContext,
    MuDecodeError,
    MuDeserialize,
    MuDeserializerFn,
    MuDeserializerRegistry,
    MuName,
    MuOneOrMore,
    MuOptional,
    MuParserError,
    MuZeroOrMore,
    Quoted,
    SAtom,
    SDoc,
    SExpr,
    SGroup,
    SMap,
    SMapField,
    SSeq,
    SStr,
    decode_expr,
    mu_tag,
    parse_many_typed,
    parse_one_typed,
    sexpr,
)
from mu.exec import ExecutionContext, MuNameError, eval_sexpr


def test_stable_top_level_imports_exist() -> None:
    stable_symbols = [
        MuParserError,
        Quoted,
        MuDecodeContext,
        MuDecodeError,
        MuDeserialize,
        MuDeserializerFn,
        MuDeserializerRegistry,
        MuName,
        MuOneOrMore,
        MuOptional,
        MuZeroOrMore,
        SAtom,
        SDoc,
        SExpr,
        SGroup,
        SMap,
        SMapField,
        SSeq,
        SStr,
        decode_expr,
        mu_tag,
        parse_many_typed,
        parse_one_typed,
        sexpr,
    ]
    assert all(stable_symbols)
    assert isinstance(mu.__version__, str)
    assert mu.__version__


def test_experimental_runtime_imports_exist() -> None:
    assert ExecutionContext
    assert eval_sexpr
    assert MuNameError


@dataclass
class Demo:
    name: str
    aliases: Annotated[list[str], MuZeroOrMore]


def test_readme_contract_parser_and_typed_example() -> None:
    parsed = sexpr('(demo :name "x" :aliases "a" "b")')
    assert isinstance(parsed, SDoc)
    result = parse_one_typed('(demo :name "x" :aliases "a" "b")', Demo)
    assert result == Demo(name="x", aliases=["a", "b"])


@dataclass
class Counter:
    value: int


def test_readme_contract_error_handling_example() -> None:
    with pytest.raises(MuDecodeError):
        parse_one_typed('(counter :value "not-an-int")', Counter)
