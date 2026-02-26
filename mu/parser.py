"""Parser for Mu source text into AST nodes."""

from __future__ import annotations

import re
from math import gcd

from mu.input import Span, _Input, debug
from mu.types import (
    AtomExpr,
    Document,
    Expr,
    GroupExpr,
    MappingExpr,
    MappingField,
    SequenceExpr,
    SInt,
    SRational,
    SReal,
    StringExpr,
    TokenSpans,
)


class ParseError(Exception):
    """Raised when Mu source cannot be parsed into a valid AST."""

    pass


_NAME_EXTRA_CHARS = "_.@/+-$%=!?*#&~^|<>:'"
_INTEGER_RE = re.compile(r"^[+-]?[0-9](?:[0-9_]*[0-9])?$")
_RATIONAL_RE = re.compile(
    r"^(?P<num>[+-]?[0-9](?:[0-9_]*[0-9])?)/(?P<den>[0-9](?:[0-9_]*[0-9])?)$"
)
_REAL_RE = re.compile(
    r"^[+-]?[0-9](?:[0-9_]*[0-9])?\.[0-9](?:[0-9_]*[0-9])?(?:[eE][+-]?[0-9]+)?$"
)
_REAL_DOT_RE = re.compile(r"^[+-]?[0-9](?:[0-9_]*[0-9])?\.(?:[eE][+-]?[0-9]+)?$")
_REAL_EXP_RE = re.compile(
    r"^[+-]?[0-9](?:[0-9_]*[0-9])?(?:\.[0-9](?:[0-9_]*[0-9])?)?[eE][+-]?[0-9]+$"
)
_PERCENT_RE = re.compile(
    r"^(?P<value>[+-]?[0-9](?:[0-9_]*[0-9])?(?:\.[0-9](?:[0-9_]*[0-9])?)?)%$"
)


def _is_name_char(ch: str) -> bool:
    if ch == _Input.EOS:
        return False
    return ch.isalnum() or ch in _NAME_EXTRA_CHARS


def _clean_numeric(text: str) -> str:
    return text.replace("_", "")


@debug
def _parse_one_sexpr(input: _Input) -> Expr:
    _skip_whitespace(input)
    c = input.current
    if c == _Input.EOS:
        raise ParseError("Unexpected end of input")
    if c == "(":
        return _parse_group(input)
    elif c == "[":
        return _parse_list(input)
    elif c in {'"', "'"}:
        return _parse_string(input, quote=c)
    elif c == "#":
        return _parse_raw_string(input)
    elif c == "{":
        return _parse_map(input)
    elif _is_name_char(c):
        return _parse_symbol_or_number(input)
    raise ParseError(f"Expected expression, found {c!r}")


@debug
def _skip_whitespace(input: _Input) -> Span:
    while True:
        if input.current == _Input.EOS:
            break
        if input.current.isspace():
            input.next()
        elif input.current == ";":
            while input.current not in ["\n", _Input.EOS]:
                input.next()
            if input.current != _Input.EOS:
                input.next()  # consume the newline if it actually was a newline
        else:
            break
    return input.capture()


@debug
def _parse_group(input: _Input) -> GroupExpr:
    if input.current != "(":
        raise ParseError(f"Expected '(' but got {input.current!r}")
    input.next()
    open_bracket = TokenSpans(token=input.capture(), space=_skip_whitespace(input))

    values: list[Expr] = []
    separators: list[TokenSpans] = []
    while input.current != ")":
        if input.current == _Input.EOS:
            break

        values.append(_parse_one_sexpr(input))

        if input.current == ",":  # Skip empty values
            input.next()

        separators.append(
            TokenSpans(token=input.capture(), space=_skip_whitespace(input))
        )

    if input.current == _Input.EOS:
        raise ParseError("Unexpected end of input")

    if input.current != ")":
        raise ParseError(f"Expected ')' but got {input.current!r}")
    input.next()
    close_bracket = TokenSpans(token=input.capture(), space=_skip_whitespace(input))

    return GroupExpr(
        values=values,
        open_bracket=open_bracket,
        separators=separators,
        close_bracket=close_bracket,
    )


@debug
def _parse_list(input: _Input) -> SequenceExpr:
    if input.current != "[":
        raise ParseError(f"Expected '[' but got {input.current!r}")
    input.next()
    open_bracket = TokenSpans(token=input.capture(), space=_skip_whitespace(input))

    values: list[Expr] = []
    separators: list[TokenSpans] = []
    while input.current != "]":
        if input.current == _Input.EOS:
            raise ParseError("Unexpected end of input")

        values.append(_parse_one_sexpr(input))

        if input.current == ",":  # Skip empty values
            input.next()

        separators.append(
            TokenSpans(token=input.capture(), space=_skip_whitespace(input))
        )

    if input.current != "]":
        raise ParseError(f"Expected ']' but got {input.current!r}")
    input.next()
    close_bracket = TokenSpans(token=input.capture(), space=_skip_whitespace(input))

    return SequenceExpr(
        values=values,
        open_bracket=open_bracket,
        separators=separators,
        close_bracket=close_bracket,
    )


@debug
def _parse_symbol_or_number(input: _Input) -> Expr:
    if not _is_name_char(input.current):
        raise ParseError(f"Unexpected character: {input.current!r}")

    value = ""
    while _is_name_char(input.current):
        value += input.current
        input.next()

    value_span = TokenSpans(token=input.capture(), space=_skip_whitespace(input))
    numeric_expr = _parse_number_token(value, value_span)
    if numeric_expr is not None:
        return numeric_expr
    return AtomExpr(value=value, span=value_span)


def _parse_number_token(value: str, span: TokenSpans) -> Expr | None:
    rational_match = _RATIONAL_RE.fullmatch(value)
    if rational_match is not None:
        numerator = int(_clean_numeric(rational_match.group("num")))
        denominator = int(_clean_numeric(rational_match.group("den")))
        if denominator == 0:
            raise ParseError("Rational denominator cannot be zero")
        factor = gcd(abs(numerator), denominator)
        return SRational(value=(numerator // factor, denominator // factor), span=span)

    percent_match = _PERCENT_RE.fullmatch(value)
    if percent_match is not None:
        return SReal(value=float(_clean_numeric(percent_match.group("value"))) / 100.0, span=span)

    if _REAL_RE.fullmatch(value) or _REAL_DOT_RE.fullmatch(value) or _REAL_EXP_RE.fullmatch(value):
        return SReal(value=float(_clean_numeric(value)), span=span)

    if _INTEGER_RE.fullmatch(value):
        return SInt(value=int(_clean_numeric(value)), span=span)

    return None


@debug
def _parse_string(input: _Input, quote: str = '"') -> StringExpr:
    if quote not in {'"', "'"}:
        raise ParseError(f"Invalid string quote delimiter {quote!r}")
    if input.current != quote:
        raise ParseError(f"Expected {quote!r} but got {input.current!r}")
    input.next()

    value = ""
    while input.current != quote:
        if input.current == _Input.EOS:
            raise ParseError("Unexpected end of input")
        if input.current == "\\":
            input.next()
            if input.current == _Input.EOS:
                raise ParseError("Unexpected end of input in escape sequence")
            match input.current:
                case "n":
                    value += "\n"
                    input.next()
                case "t":
                    value += "\t"
                    input.next()
                case "r":
                    value += "\r"
                    input.next()
                case "0":
                    value += "\0"
                    input.next()
                case "\\":
                    value += "\\"
                    input.next()
                case "'":
                    value += "'"
                    input.next()
                case '"':
                    value += '"'
                    input.next()
                case "u":
                    input.next()
                    value += _parse_unicode_escape(input)
                case _:
                    # Kotlin parser preserves unknown escapes verbatim.
                    value += "\\"
                    value += input.current
                    input.next()
        else:
            value += input.current
            input.next()

    if input.current != quote:
        raise ParseError(f"Expected closing quote {quote!r}")
    input.next()

    value_span = TokenSpans(token=input.capture(), space=_skip_whitespace(input))

    return StringExpr(value=value, span=value_span)


def _parse_unicode_escape(input: _Input) -> str:
    if input.current != "{":
        raise ParseError("Expected '{' after '\\u' in string escape")
    input.next()

    digits = ""
    while input.current != "}":
        if input.current == _Input.EOS:
            raise ParseError("Unexpected end of input in unicode escape")
        if not input.current.isdigit() and input.current.lower() not in "abcdef":
            raise ParseError("Expected hex digit in unicode escape")
        digits += input.current
        input.next()

    if digits == "":
        raise ParseError("Unicode escape must contain at least one hex digit")

    input.next()

    codepoint = int(digits, 16)
    try:
        return chr(codepoint)
    except ValueError as error:  # pragma: no cover - defensive for invalid code points
        raise ParseError("Invalid unicode code point in escape") from error


@debug
def _parse_raw_string(input: _Input) -> StringExpr:
    if input.current != "#":
        raise ParseError(f"Expected '#' but got {input.current!r}")
    input.next()
    tag = ""
    while input.current.isalnum():
        tag += input.current
        input.next()
    if input.current != '"':
        raise ParseError("Expected '\"' after raw string tag")
    input.next()
    value = ""

    while True:
        if input.current == _Input.EOS:
            raise ParseError("Unexpected end of input")
        if input.current != '"':
            value += input.current
            input.next()
            continue
        else:
            input.next()
            if tag == "":
                break

            count = 0
            while input.current == tag[count]:
                count += 1
                input.next()
                if count == len(tag):
                    break

            if count == len(tag):
                break

            value += '"' + tag[:count]
            continue

    value_span = TokenSpans(token=input.capture(), space=_skip_whitespace(input))

    return StringExpr(value=value, span=value_span)


@debug
def _parse_map(input: _Input) -> MappingExpr:
    if input.current != "{":
        raise ParseError(f"Expected '{{' but got {input.current!r}")
    input.next()
    open_bracket = TokenSpans(token=input.capture(), space=_skip_whitespace(input))

    values: list[MappingField] = []
    separators: list[TokenSpans] = []
    while input.current != "}":
        if input.current == _Input.EOS:
            raise ParseError("Unexpected end of input")

        key = _parse_one_sexpr(input)

        if isinstance(key, AtomExpr) and key.value.endswith(":"):
            # We are gonna have to do some surgery here
            if key.span is None or key.span.token is None:
                raise ParseError("Missing span information for map key")
            key_span = key.span.token
            new_key = AtomExpr(key.value[:-1], TokenSpans(key_span[:-1], key_span[-1:-1]))
            colon_span = key_span[-1:]
            colon = TokenSpans(token=colon_span, space=key.span.space)
            key = new_key
        else:
            if input.current != ":":
                raise ParseError(f"Expected ':' but got '{input.current}'")
            input.next()
            colon = TokenSpans(token=input.capture(), space=_skip_whitespace(input))

        value = _parse_one_sexpr(input)
        values.append(MappingField(key, value, colon))

        if input.current == ",":
            input.next()
        separators.append(
            TokenSpans(token=input.capture(), space=_skip_whitespace(input))
        )

    if input.current != "}":
        raise ParseError(f"Expected '}}' but got {input.current!r}")
    input.next()

    close_bracket = TokenSpans(token=input.capture(), space=_skip_whitespace(input))

    return MappingExpr(
        values=values,
        open_bracket=open_bracket,
        separators=separators,
        close_bracket=close_bracket,
    )


@debug
def parse(
    input: str,
    preserve_spans: bool = False,
) -> Document:
    """Parse Mu source text into a `Document`.

    Args:
        input: Mu source text.
        preserve_spans: When `True`, keep token/space span metadata on nodes.
            Default `False` returns span-free nodes.

    Returns:
        Parsed `Document`.
    """
    top_level: list[Expr] = []
    input_r = _Input(input)
    leading_space = _skip_whitespace(input_r)
    while input_r.current != _Input.EOS:
        top_level.append(_parse_one_sexpr(input_r))

    result = Document(top_level, leading_space=leading_space)
    if not preserve_spans:
        result = result.drop_spans()
    return result
