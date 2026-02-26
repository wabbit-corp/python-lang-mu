"""Stable public API exports for the `mu` package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from mu.loading import load as load
from mu.loading import loads as loads
from mu.parser import ParseError as ParseError
from mu.parser import parse as parse
from mu.quoted import Quoted as Quoted
from mu.typed import DecodeContext as DecodeContext
from mu.typed import DecodeError as DecodeError
from mu.typed import DecoderFn as DecoderFn
from mu.typed import DecoderRegistry as DecoderRegistry
from mu.typed import DecodeWith as DecodeWith
from mu.typed import FieldName as FieldName
from mu.typed import OneOrMore as OneOrMore
from mu.typed import OptionalArg as OptionalArg
from mu.typed import ZeroOrMore as ZeroOrMore
from mu.typed import decode as decode
from mu.typed import parse_many as parse_many
from mu.typed import parse_one as parse_one
from mu.typed import tag as tag
from mu.types import AtomExpr as AtomExpr
from mu.types import Document as Document
from mu.types import Expr as Expr
from mu.types import GroupExpr as GroupExpr
from mu.types import MappingExpr as MappingExpr
from mu.types import MappingField as MappingField
from mu.types import SequenceExpr as SequenceExpr
from mu.types import StringExpr as StringExpr

try:
    __version__ = version("lang-mu")
except PackageNotFoundError:  # pragma: no cover - local editable installs
    __version__ = "0.3.0"

__all__ = [
    "ParseError",
    "Quoted",
    "DecodeContext",
    "DecodeError",
    "DecodeWith",
    "DecoderFn",
    "DecoderRegistry",
    "FieldName",
    "OneOrMore",
    "OptionalArg",
    "ZeroOrMore",
    "AtomExpr",
    "Document",
    "Expr",
    "GroupExpr",
    "MappingExpr",
    "MappingField",
    "SequenceExpr",
    "StringExpr",
    "__version__",
    "load",
    "loads",
    "decode",
    "tag",
    "parse_many",
    "parse_one",
    "parse",
]
