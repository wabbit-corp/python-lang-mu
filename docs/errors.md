# Error Handling

Typed decode failures raise `DecodeError`.

## `DecodeError` Fields

- `path`: decode location (for example `$.field[0]`).
- `expected`: human-readable expected type/shape.
- `got`: description of what was actually received.
- `span`: optional source span/token object when parse spans are enabled.
- `cause`: optional underlying exception.

## Example

```python
from dataclasses import dataclass

from mu import DecodeError, parse_one


@dataclass
class Counter:
    value: int


try:
    parse_one('(counter :value "not-an-int")', Counter)
except DecodeError as err:
    assert err.path == "$.value"
    assert err.expected == "int atom"
    assert "string(" in err.got
    assert err.span is not None
```

## Practical Guidance

- Surface `path`, `expected`, and `got` directly in user-facing validation errors.
- Treat `span` as optional metadata and guard for `None`.
- Preserve `cause` when re-raising domain-specific exceptions.
