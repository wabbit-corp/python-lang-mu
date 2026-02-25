# Quickstart

## Parse Mu Source

`docs/examples/quickstart-parse.mu`

```clojure
; application plus shared includes
(app-jvm "billing-api"
  :main "billing.Main"
  :ports [8080 8443]
  :env {
    profile: prod,
    region: us-east-1
  }
)

(include "shared/logging.mu")
```

```python
from mu import AtomExpr, Document, GroupExpr, parse

with open("docs/examples/quickstart-parse.mu", "r", encoding="utf-8") as f:
    source = f.read()

doc = parse(source)
assert isinstance(doc, Document)
assert len(doc.exprs) == 2

app = doc.exprs[0]
assert isinstance(app, GroupExpr)
assert isinstance(app.values[0], AtomExpr)
assert app.values[0].value == "app-jvm"
```

## Decode a Single Expression

`docs/examples/quickstart-single.mu`

```clojure
(demo
  :name "backend"
  :aliases "api"
  :aliases "service"
)
```

```python
from dataclasses import dataclass
from typing import Annotated

from mu import ZeroOrMore, parse_one


@dataclass
class Demo:
    name: str
    aliases: Annotated[list[str], ZeroOrMore]


with open("docs/examples/quickstart-single.mu", "r", encoding="utf-8") as f:
    source = f.read()

cfg = parse_one(source, Demo)
assert cfg == Demo(name="backend", aliases=["api", "service"])
```

## Decode Multiple Expressions

`docs/examples/quickstart-many.mu`

```clojure
(run "lint")
(include "defaults.mu")
(run "test")
```

```python
from dataclasses import dataclass

from mu import parse_many


@dataclass
class Run:
    task: str


@dataclass
class Include:
    path: str


with open("docs/examples/quickstart-many.mu", "r", encoding="utf-8") as f:
    source = f.read()

result = parse_many(source, Run | Include)
assert result == [Run(task="lint"), Include(path="defaults.mu"), Run(task="test")]
```
