# Quickstart

## Parse Mu Source

```python
from mu import AtomExpr, Document, GroupExpr, parse

source = """
; application plus shared includes
(app-jvm "billing-api"
  :main "billing.Main"
  :ports [8080 8443]
  :env {profile: prod, region: us-east-1}
)
(include "shared/logging.mu")
"""

doc = parse(source)
assert isinstance(doc, Document)
assert len(doc.exprs) == 2

app = doc.exprs[0]
assert isinstance(app, GroupExpr)
assert isinstance(app.values[0], AtomExpr)
assert app.values[0].value == "app-jvm"
```

## Decode a Single Expression

```python
from dataclasses import dataclass
from typing import Annotated

from mu import ZeroOrMore, parse_one


@dataclass
class Demo:
    name: str
    aliases: Annotated[list[str], ZeroOrMore]


cfg = parse_one('(demo :name "x" :aliases "a" "b")', Demo)
assert cfg == Demo(name="x", aliases=["a", "b"])
```

## Decode Multiple Expressions

```python
from dataclasses import dataclass

from mu import parse_many


@dataclass
class Run:
    task: str


@dataclass
class Include:
    path: str


result = parse_many('(run "lint") (include "defaults.mu")', Run | Include)
assert result == [Run(task="lint"), Include(path="defaults.mu")]
```
