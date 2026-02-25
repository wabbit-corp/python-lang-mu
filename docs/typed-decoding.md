# Typed Decoding

## Dataclass Tags

By default, dataclass names are converted from `CamelCase` to `kebab-case`.
Use `tag(...)` to override.

```python
from dataclasses import dataclass

from mu import parse_one, tag


@tag("app-jvm")
@dataclass
class AppJvm:
    name: str
    main: str


cfg = parse_one('(app-jvm "demo" :main "demo.Main")', AppJvm)
assert cfg == AppJvm(name="demo", main="demo.Main")
```

## Field Names And Arity

- `FieldName("...")` overrides the Mu argument name.
- `OptionalArg` means field can be omitted.
- `ZeroOrMore` and `OneOrMore` model repeated values.

```python
from dataclasses import dataclass
from typing import Annotated

from mu import FieldName, OptionalArg, OneOrMore, parse_one


@dataclass
class Service:
    first_name: Annotated[str, FieldName("display-name")]
    nickname: Annotated[str | None, OptionalArg]
    features: Annotated[list[str], OneOrMore]


cfg = parse_one(
    '(service :display-name "alice" :features "http" "metrics")',
    Service,
)
assert cfg == Service(first_name="alice", nickname=None, features=["http", "metrics"])
```

## Union Tag Dispatch

When target type is a union of dataclasses, decode dispatches by tag.

```python
from dataclasses import dataclass

from mu import parse_one


@dataclass
class AppJvm:
    name: str
    main: str


@dataclass
class AppPy:
    entry: str


cfg = parse_one('(app-jvm "demo" :main "demo.Main")', AppJvm | AppPy)
assert isinstance(cfg, AppJvm)
assert cfg == AppJvm(name="demo", main="demo.Main")
```

Unions also work for nested fields:

```python
from dataclasses import dataclass

from mu import parse_one


@dataclass
class Http:
    port: int


@dataclass
class Worker:
    queue: str


@dataclass
class Service:
    name: str
    mode: Http | Worker


cfg = parse_one('(service "api" :mode (http :port 8080))', Service)
assert cfg == Service(name="api", mode=Http(port=8080))
```

## Decode Mixed Top-Level Commands

Use `parse_many(...)` with a union target to decode a top-level command stream
where each expression can be a different command type.

```python
from dataclasses import dataclass

from mu import parse_many


@dataclass
class Run:
    task: str


@dataclass
class Include:
    path: str


commands = parse_many(
    '(run "lint") (include "defaults.mu") (run "test")',
    Run | Include,
)
assert commands == [
    Run(task="lint"),
    Include(path="defaults.mu"),
    Run(task="test"),
]
```

## Custom Decoders

- Use `DecodeWith(fn)` on a field for field-specific decoding.
- Use `DecoderRegistry` for global decoding behavior by target type.

```python
from dataclasses import dataclass
from typing import Annotated

from mu import DecodeContext, DecodeWith, DecoderRegistry, parse_one


@dataclass
class Cfg:
    value: Annotated[int, DecodeWith(lambda _expr, _ctx: 7)]


registry = DecoderRegistry()
registry.register(int, lambda _expr, _ctx: 999)
result = parse_one("(cfg 123)", Cfg, registry=registry)
assert result.value == 7
```

```python
from dataclasses import dataclass

from mu import DecodeContext, DecoderRegistry, parse_one


@dataclass
class Cfg:
    value: int


def decode_int(_expr, _ctx: DecodeContext) -> int:
    return 5


registry = DecoderRegistry()
registry.register(int, decode_int)
result = parse_one("(cfg 12345)", Cfg, registry=registry)
assert result == Cfg(value=5)
```
