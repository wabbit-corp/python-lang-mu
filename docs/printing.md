# Pretty Printing And `dumps`

Use `dumps(...)` APIs to serialize Mu AST nodes and Python values.

## API Overview

- `dumps(value, ...)`
  - `indent=None` gives concise mode.
  - `indent=<int>` gives pretty mode.
- `dumps_pretty(value, ...)`
  - Convenience wrapper for pretty mode.
- `dumps_concise(value, ...)`
  - Convenience wrapper for concise mode.

## Basic Usage

```python
from dataclasses import dataclass

from mu import dumps_concise, dumps_pretty


@dataclass
class AppJvm:
    name: str
    main: str
    ports: list[int]


cfg = AppJvm(name="billing-api", main="billing.Main", ports=[8080, 8443])

pretty = dumps_pretty(cfg, positional_first_id_or_name=True, max_line_length=30)
assert pretty.startswith('(app-jvm "billing-api"')
assert "\n" in pretty

concise = dumps_concise(cfg, positional_first_id_or_name=True)
assert concise == '(app-jvm "billing-api" :main "billing.Main" :ports [8080 8443])'
```

## `dumps(...)` With Explicit Mode

```python
from dataclasses import dataclass

from mu import dumps


@dataclass
class Include:
    path: str


cfg = Include(path="shared/logging.mu")
assert dumps(cfg, indent=None) == '(include "shared/logging.mu")'
assert dumps(cfg, indent=2) == '(include "shared/logging.mu")'
```

## Preserving Source Spans

When parsing with `preserve_spans=True`, dumping with `preserve_spans=True`
reuses the original token/spacing where possible.

```python
from mu import dumps_pretty, parse

source = '(app-jvm    "demo" :main   "demo.Main")'
doc = parse(source, preserve_spans=True)

assert dumps_pretty(doc, preserve_spans=True) == source
assert dumps_pretty(doc, preserve_spans=False) == '(app-jvm "demo" :main "demo.Main")'
```

## Line Length And Wrapping

Use `max_line_length` to control when output wraps.

```python
from dataclasses import dataclass

from mu import dumps_concise


@dataclass
class Service:
    name: str
    main: str
    features: list[str]


cfg = Service(name="api", main="billing.Main", features=["http", "metrics", "tracing"])
wrapped = dumps_concise(cfg, positional_first_id_or_name=True, max_line_length=30)
assert "\n" in wrapped
```
