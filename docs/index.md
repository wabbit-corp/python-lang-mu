# lang-mu

`lang-mu` is a Python distribution that provides the `mu` import package:

- A parser that preserves Mu syntax as a structured AST.
- A typed decoder that maps Mu expressions to Python dataclasses and type hints.
- An experimental execution runtime under `mu.exec`.

## Problem This Solves

Mu configuration files encode nested data, tagged records, and mixed positional/named arguments.
`lang-mu` gives you strict parsing and deterministic decoding for these files so you can load configuration into typed Python models.

## Quick Sample

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

## Next Steps

- Start with [Installation](installation.md).
- Follow [Quickstart](quickstart.md).
- Use [Printing](printing.md) for `dumps`, `dumps_pretty`, and `dumps_concise`.
- Use [Typed Decoding](typed-decoding.md) for dataclass-based models.
- Review [Compatibility](compatibility.md) before depending on runtime APIs.
