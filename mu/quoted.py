from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class Quoted(Generic[T]):
    """Wraps a value that should be passed through without runtime evaluation."""

    def __init__(self, value: T):
        self.value = value

    def __repr__(self) -> str:
        return f"Quoted({self.value!r})"

