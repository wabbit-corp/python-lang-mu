"""Load Mu documents from strings, files, and paths."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol, TypeVar, cast, overload

from mu.parser import parse
from mu.typed import DecodeError, DecoderRegistry, decode
from mu.types import Document

T = TypeVar("T")


class _TextReadable(Protocol):
    def read(self, size: int = -1) -> str:
        """Read text data from a file-like object."""


Source = str | os.PathLike[str] | _TextReadable


def _read_source(source: Source, *, encoding: str) -> str:
    if hasattr(source, "read"):
        text = cast(_TextReadable, source).read()
        if not isinstance(text, str):
            raise TypeError("load() source.read() must return str text")
        return text
    return Path(source).read_text(encoding=encoding)


@overload
def loads(
    source: str,
    *,
    type: None = None,
    registry: DecoderRegistry | None = None,
    preserve_spans: bool = False,
) -> Document: ...


@overload
def loads(
    source: str,
    *,
    type: type[T],
    registry: DecoderRegistry | None = None,
    preserve_spans: bool = False,
) -> T: ...


@overload
def loads(
    source: str,
    *,
    type: Any,
    registry: DecoderRegistry | None = None,
    preserve_spans: bool = False,
) -> Any: ...


def loads(
    source: str,
    *,
    type: Any | None = None,
    registry: DecoderRegistry | None = None,
    preserve_spans: bool = False,
) -> Document | Any:
    """Load Mu from a string.

    When `type` is omitted, returns `Document`. When provided, decodes a
    single top-level expression into the target type.
    """
    doc = parse(source, preserve_spans=preserve_spans)
    if type is None:
        return doc

    if len(doc.exprs) != 1:
        raise DecodeError(
            path="$",
            expected="exactly one top-level expression",
            got=f"{len(doc.exprs)} expressions",
        )
    return decode(doc.exprs[0], type, registry=registry, path="$")


@overload
def load(
    source: Source,
    *,
    type: None = None,
    encoding: str = "utf-8",
    registry: DecoderRegistry | None = None,
    preserve_spans: bool = False,
) -> Document: ...


@overload
def load(
    source: Source,
    *,
    type: type[T],
    encoding: str = "utf-8",
    registry: DecoderRegistry | None = None,
    preserve_spans: bool = False,
) -> T: ...


@overload
def load(
    source: Source,
    *,
    type: Any,
    encoding: str = "utf-8",
    registry: DecoderRegistry | None = None,
    preserve_spans: bool = False,
) -> Any: ...


def load(
    source: Source,
    *,
    type: Any | None = None,
    encoding: str = "utf-8",
    registry: DecoderRegistry | None = None,
    preserve_spans: bool = False,
) -> Document | Any:
    """Load Mu from a path or file-like object."""
    text = _read_source(source, encoding=encoding)
    return loads(
        text,
        type=type,
        registry=registry,
        preserve_spans=preserve_spans,
    )


__all__ = ["Source", "load", "loads"]
