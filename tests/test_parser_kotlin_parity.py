from __future__ import annotations

import pytest

from mu import parse
from mu.parser import ParseError
from mu.types import AtomExpr, MappingExpr, MappingField, SInt, SRational, SReal, StringExpr


def _one(source: str):
    doc = parse(source)
    assert len(doc.exprs) == 1
    return doc.exprs[0]


def test_parser_reports_parse_error_for_invalid_tokens() -> None:
    with pytest.raises(ParseError):
        parse(")")
    with pytest.raises(ParseError):
        parse("#tagabc")


def test_semicolon_starts_comment_even_without_space() -> None:
    doc = parse("foo;bar")
    assert doc.exprs == [AtomExpr("foo")]


def test_single_quoted_strings_are_supported() -> None:
    assert _one("'a'") == StringExpr("a")
    assert _one("'\"'") == StringExpr('"')


def test_unknown_escape_is_preserved_like_kotlin_parser() -> None:
    assert _one(r'"a\q"') == StringExpr(r"a\q")


def test_unicode_brace_escape_is_supported() -> None:
    assert _one(r'"\u{41}"') == StringExpr("A")


def test_numeric_literals_match_kotlin_int_real_rational_behavior() -> None:
    assert _one("1") == SInt(1)
    assert _one("-1_000_000") == SInt(-1_000_000)

    assert _one("1.0") == SReal(1.0)
    assert _one("1.0e+01") == SReal(10.0)
    assert _one("50%") == SReal(0.5)

    assert _one("1/2") == SRational((1, 2))
    assert _one("20/30") == SRational((2, 3))


def test_numeric_like_tokens_that_are_symbols_remain_atoms() -> None:
    assert _one("10h") == AtomExpr("10h")
    assert _one("+") == AtomExpr("+")
    assert _one(".a") == AtomExpr(".a")


def test_map_numeric_keys_and_values_parse_as_numeric_expressions() -> None:
    assert _one("{1 : 2}") == MappingExpr([MappingField(SInt(1), SInt(2))])


def test_single_quote_can_still_appear_in_symbol_name_when_not_leading() -> None:
    assert _one("first'") == AtomExpr("first'")
