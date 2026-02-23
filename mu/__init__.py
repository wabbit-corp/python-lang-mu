from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from mu.parser import MuParserError as MuParserError
from mu.parser import sexpr as sexpr
from mu.quoted import Quoted as Quoted
from mu.typed import MuDecodeContext as MuDecodeContext
from mu.typed import MuDecodeError as MuDecodeError
from mu.typed import MuDeserialize as MuDeserialize
from mu.typed import MuDeserializerFn as MuDeserializerFn
from mu.typed import MuDeserializerRegistry as MuDeserializerRegistry
from mu.typed import MuName as MuName
from mu.typed import MuOneOrMore as MuOneOrMore
from mu.typed import MuOptional as MuOptional
from mu.typed import MuZeroOrMore as MuZeroOrMore
from mu.typed import decode_expr as decode_expr
from mu.typed import mu_tag as mu_tag
from mu.typed import parse_many_typed as parse_many_typed
from mu.typed import parse_one_typed as parse_one_typed
from mu.types import SAtom as SAtom
from mu.types import SDoc as SDoc
from mu.types import SExpr as SExpr
from mu.types import SGroup as SGroup
from mu.types import SMap as SMap
from mu.types import SMapField as SMapField
from mu.types import SSeq as SSeq
from mu.types import SStr as SStr

try:
    __version__ = version("mu")
except PackageNotFoundError:  # pragma: no cover - local editable installs
    __version__ = "0.2.0"

__all__ = [
    "MuParserError",
    "Quoted",
    "MuDecodeContext",
    "MuDecodeError",
    "MuDeserialize",
    "MuDeserializerFn",
    "MuDeserializerRegistry",
    "MuName",
    "MuOneOrMore",
    "MuOptional",
    "MuZeroOrMore",
    "SAtom",
    "SDoc",
    "SExpr",
    "SGroup",
    "SMap",
    "SMapField",
    "SSeq",
    "SStr",
    "__version__",
    "decode_expr",
    "mu_tag",
    "parse_many_typed",
    "parse_one_typed",
    "sexpr",
]
