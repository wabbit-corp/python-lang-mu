"""Parser for Mu source text into AST nodes."""

from mu.input import Span, _Input, debug
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


class ParseError(Exception):
    """Raised when Mu source cannot be parsed into a valid AST."""

    pass


@debug
def _parse_one_sexpr(input: _Input) -> Expr:
    _skip_whitespace(input)
    c = input.current
    if c == "(":
        return _parse_group(input)
    elif c == "[":
        return _parse_list(input)
    elif c == '"':
        return _parse_string(input)
    elif c == "#":
        return _parse_raw_string(input)
    elif c == "{":
        return _parse_map(input)
    else:
        return _parse_atom(input)


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
    assert input.current == "("
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

    assert input.current == ")"
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
    assert input.current == "["
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

    assert input.current == "]"
    input.next()
    close_bracket = TokenSpans(token=input.capture(), space=_skip_whitespace(input))

    return SequenceExpr(
        values=values,
        open_bracket=open_bracket,
        separators=separators,
        close_bracket=close_bracket,
    )


@debug
def _parse_atom(input: _Input) -> AtomExpr:
    assert input.current not in [
        _Input.EOS,
        "(",
        ")",
        "[",
        "]",
        ",",
        "{",
        "}",
        '"',
    ], f"Unexpected character: {input.current} at {input}"
    assert (
        not input.current.isspace()
    ), f"Unexpected whitespace character: {input.current} at {input.index}"

    value = ""
    while (
        input.current not in [_Input.EOS, "(", ")", "[", "]", ",", "{", "}", '"']
        and not input.current.isspace()
    ):
        value += input.current
        input.next()

    value_span = TokenSpans(token=input.capture(), space=_skip_whitespace(input))

    return AtomExpr(value=value, span=value_span)


@debug
def _parse_string(input: _Input) -> StringExpr:
    assert input.current == '"'
    input.next()

    value = ""
    while input.current != '"':
        if input.current == _Input.EOS:
            raise ParseError("Unexpected end of input")
        if input.current == "\\":
            input.next()
            match input.current:
                case "n":
                    value += "\n"
                case "t":
                    value += "\t"
                case "r":
                    value += "\r"
                case "0":
                    value += "\0"
                case "\\":
                    value += "\\"
                case '"':
                    value += '"'
                case _:
                    raise ParseError(f"Invalid escape sequence: '\\{input.current}'")
            input.next()
        else:
            value += input.current
            input.next()

    assert input.current == '"'
    input.next()

    value_span = TokenSpans(token=input.capture(), space=_skip_whitespace(input))

    return StringExpr(value=value, span=value_span)


@debug
def _parse_raw_string(input: _Input) -> StringExpr:
    assert input.current == "#"
    input.next()
    tag = ""
    while input.current.isalnum():
        tag += input.current
        input.next()
    assert input.current == '"'
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
    assert input.current == "{"
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

    assert input.current == "}"
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
