from typing import List, Tuple, TypeAlias, Optional, Callable, Any
from dataclasses import dataclass

from mu.input import Span

# from decimal import Decimal
# from fractions import Fraction

class SExpr:
    Atom: type['SAtom'] = None # type: ignore
    Str: type['SStr'] = None # type: ignore
    Real: type['SReal'] = None # type: ignore
    Int: type['SInt'] = None # type: ignore
    Rational: type['SRational'] = None # type: ignore

    Group: type['SGroup'] = None # type: ignore
    Seq: type['SSeq'] = None # type: ignore
    Map: type['SMap'] = None # type: ignore

    def drop_spans(self) -> 'SExpr':
        match self:
            case SExpr.Atom(value=value): return SExpr.Atom(value)
            case SExpr.Str(value=value): return SExpr.Str(value)
            case SExpr.Real(value=value): return SExpr.Real(value)
            case SExpr.Int(value=value): return SExpr.Int(value)
            case SExpr.Rational(value=value): return SExpr.Rational(value)

            case SExpr.Group(values=values): return SExpr.Group([v.drop_spans() for v in values])
            case SExpr.Seq(values=values): return SExpr.Seq([v.drop_spans() for v in values])
            case SExpr.Map(values=values): return SExpr.Map([SMapField(field.key.drop_spans(), field.value.drop_spans()) 
                                                             for field in values])


@dataclass
class TokenSpans:
    token: Optional[Span] = None
    space: Optional[Span] = None

    def __str__(self) -> str:
        result = ''
        if self.token is not None:
            result += f"{self.token.raw}"
        if self.space is not None:
            result += f"{self.space.raw}"
        return result


# a | ab | define-test | 123 | 123.456 | 123. | .456
@dataclass
class SAtom(SExpr):
    value: str
    span: Optional[TokenSpans] = None

    def __str__(self) -> str:
        if self.span is not None:
            return str(self.span)
        return self.value


# "a" | "ab" | "define-test" | "123" | "123.456" | "123." | ".456"
# #"\d+" | #"\d+.\*" ... (raw)
@dataclass
class SStr(SExpr):
    value: str
    span: Optional[TokenSpans] = None

    def __str__(self) -> str:
        if self.span is not None:
            return str(self.span)
        return self.value

# 123.456 | 123. | .456 | 123e4 | 123.456e4 | 123.e4 | .456e4
@dataclass
class SReal(SExpr):
    value: str
    span: Optional[TokenSpans] = None

    def __str__(self) -> str:
        if self.span is not None:
            return str(self.span)
        return self.value

# 123 | 0x123 | 0b101 | 0o123
@dataclass
class SInt(SExpr):
    value: int
    span: Optional[TokenSpans] = None

    def __str__(self) -> str:
        if self.span is not None:
            return str(self.span)
        return str(self.value)

# 123/456
@dataclass
class SRational(SExpr):
    value: Tuple[int, int]
    span: Optional[TokenSpans] = None

    def __str__(self) -> str:
        if self.span is not None:
            return str(self.span)
        return f"{self.value[0]}/{self.value[1]}"


# (a b c)
@dataclass
class SGroup(SExpr):
    values: List[SExpr]
    
    open_bracket: Optional[TokenSpans] = None
    separators: Optional[List[TokenSpans]] = None
    close_bracket: Optional[TokenSpans] = None

    def __str__(self) -> str:
        result = ''
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
class SSeq(SExpr):
    values: List[SExpr]
    
    open_bracket: Optional[TokenSpans] = None
    separators: Optional[List[TokenSpans]] = None
    close_bracket: Optional[TokenSpans] = None

    def __str__(self) -> str:
        result = ''
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
class SMapField:
    key: SExpr
    value: SExpr
    separator: Optional[TokenSpans] = None

    def __str__(self) -> str:
        result = ''
        result += str(self.key)
        if self.separator is not None:
            result += f"{self.separator}"
        result += str(self.value)
        return result

# { a : b, c : d }
@dataclass
class SMap(SExpr):
    values: List[SMapField]
    
    open_bracket: Optional[Span] = None
    separators: Optional[List[TokenSpans]] = None
    close_bracket: Optional[Span] = None

    def __str__(self) -> str:
        result = ''
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
class SDoc:
    exprs: List[SExpr]
    leading_space: Optional[Span] = None

    def __str__(self) -> str:
        result = ''
        if self.leading_space is not None:
            result += f"{self.leading_space.raw}"
        result += ''.join(str(expr) for expr in self.exprs)
        return result
    
    def drop_spans(self) -> 'SDoc':
        return SDoc([expr.drop_spans() for expr in self.exprs], leading_space=self.leading_space)


SExpr.Atom = SAtom
SExpr.Str = SStr
SExpr.Real = SReal
SExpr.Int = SInt
SExpr.Rational = SRational

SExpr.Group = SGroup
SExpr.Seq = SSeq
SExpr.Map = SMap
