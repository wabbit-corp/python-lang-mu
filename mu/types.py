from dataclasses import dataclass

from mu.input import Span

# from decimal import Decimal
# from fractions import Fraction


class Expr:
    """Base class for all Mu expression AST nodes."""

    Atom: type["AtomExpr"] = None  # type: ignore
    Str: type["StringExpr"] = None  # type: ignore
    Real: type["SReal"] = None  # type: ignore
    Int: type["SInt"] = None  # type: ignore
    Rational: type["SRational"] = None  # type: ignore

    Group: type["GroupExpr"] = None  # type: ignore
    Seq: type["SequenceExpr"] = None  # type: ignore
    Map: type["MappingExpr"] = None  # type: ignore

    def drop_spans(self) -> "Expr":
        """Return a structurally equivalent node with token/space spans removed."""
        match self:
            case AtomExpr(value=value):
                return AtomExpr(value)
            case StringExpr(value=value):
                return StringExpr(value)
            case SReal(value=value):
                return SReal(value)
            case SInt(value=value):
                return SInt(value)
            case SRational(value=value):
                return SRational(value)
            case GroupExpr(values=values):
                return GroupExpr([v.drop_spans() for v in values])
            case SequenceExpr(values=values):
                return SequenceExpr([v.drop_spans() for v in values])
            case MappingExpr(values=values):
                return MappingExpr(
                    [
                        MappingField(field.key.drop_spans(), field.value.drop_spans())
                        for field in values
                    ]
                )
        raise TypeError(f"Unsupported expression type: {type(self).__name__}")


@dataclass
class TokenSpans:
    """Captured token and trailing space spans for source-preserving parsing."""

    token: Span | None = None
    space: Span | None = None

    def __str__(self) -> str:
        result = ""
        if self.token is not None:
            result += f"{self.token.raw}"
        if self.space is not None:
            result += f"{self.space.raw}"
        return result


# a | ab | define-test | 123 | 123.456 | 123. | .456
@dataclass
class AtomExpr(Expr):
    """Atom expression (identifier-like token) node."""

    value: str
    span: TokenSpans | None = None

    def __str__(self) -> str:
        if self.span is not None:
            return str(self.span)
        return self.value


# "a" | "ab" | "define-test" | "123" | "123.456" | "123." | ".456"
# #"\d+" | #"\d+.\*" ... (raw)
@dataclass
class StringExpr(Expr):
    """String expression node (normal or raw Mu string literal)."""

    value: str
    span: TokenSpans | None = None

    def __str__(self) -> str:
        if self.span is not None:
            return str(self.span)
        return self.value


# 123.456 | 123. | .456 | 123e4 | 123.456e4 | 123.e4 | .456e4
@dataclass
class SReal(Expr):
    """Real-number token node (currently stored as source text)."""

    value: str
    span: TokenSpans | None = None

    def __str__(self) -> str:
        if self.span is not None:
            return str(self.span)
        return self.value


# 123 | 0x123 | 0b101 | 0o123
@dataclass
class SInt(Expr):
    """Integer token node."""

    value: int
    span: TokenSpans | None = None

    def __str__(self) -> str:
        if self.span is not None:
            return str(self.span)
        return str(self.value)


# 123/456
@dataclass
class SRational(Expr):
    """Rational token node represented as `(numerator, denominator)`."""

    value: tuple[int, int]
    span: TokenSpans | None = None

    def __str__(self) -> str:
        if self.span is not None:
            return str(self.span)
        return f"{self.value[0]}/{self.value[1]}"


# (a b c)
@dataclass
class GroupExpr(Expr):
    """Parenthesized expression group node."""

    values: list[Expr]

    open_bracket: TokenSpans | None = None
    separators: list[TokenSpans] | None = None
    close_bracket: TokenSpans | None = None

    def __str__(self) -> str:
        result = ""
        if self.open_bracket is not None:
            result += f"{self.open_bracket}"

        for i, value in enumerate(self.values):
            result += str(value)
            if self.separators is not None:
                result += f"{self.separators[i]}"

        if self.close_bracket is not None:
            result += f"{self.close_bracket}"
        return result


# [a b c] | [a, b, c] | []
@dataclass
class SequenceExpr(Expr):
    """Bracketed sequence node."""

    values: list[Expr]

    open_bracket: TokenSpans | None = None
    separators: list[TokenSpans] | None = None
    close_bracket: TokenSpans | None = None

    def __str__(self) -> str:
        result = ""
        if self.open_bracket is not None:
            result += f"{self.open_bracket}"

        for i, value in enumerate(self.values):
            result += str(value)
            if self.separators is not None:
                result += f"{self.separators[i]}"

        if self.close_bracket is not None:
            result += f"{self.close_bracket}"
        return result


@dataclass
class MappingField:
    """Single key/value field inside a mapping expression."""

    key: Expr
    value: Expr
    separator: TokenSpans | None = None

    def __str__(self) -> str:
        result = ""
        result += str(self.key)
        if self.separator is not None:
            result += f"{self.separator}"
        result += str(self.value)
        return result


# { a : b, c : d }
@dataclass
class MappingExpr(Expr):
    """Brace-delimited mapping node."""

    values: list[MappingField]

    open_bracket: TokenSpans | None = None
    separators: list[TokenSpans] | None = None
    close_bracket: TokenSpans | None = None

    def __str__(self) -> str:
        result = ""
        if self.open_bracket is not None:
            result += f"{self.open_bracket}"

        for i, field in enumerate(self.values):
            result += str(field)
            if self.separators is not None:
                result += f"{self.separators[i]}"

        if self.close_bracket is not None:
            result += f"{self.close_bracket}"
        return result


@dataclass
class Document:
    """Top-level Mu parse result containing one or more expressions."""

    exprs: list[Expr]
    leading_space: Span | None = None

    def __str__(self) -> str:
        result = ""
        if self.leading_space is not None:
            result += f"{self.leading_space.raw}"
        result += "".join(str(expr) for expr in self.exprs)
        return result

    def drop_spans(self) -> "Document":
        """Return an equivalent document with spans removed from all expressions."""
        return Document(
            [expr.drop_spans() for expr in self.exprs], leading_space=self.leading_space
        )


Expr.Atom = AtomExpr
Expr.Str = StringExpr
Expr.Real = SReal
Expr.Int = SInt
Expr.Rational = SRational

Expr.Group = GroupExpr
Expr.Seq = SequenceExpr
Expr.Map = MappingExpr
