# FAQ

## Is `mu.exec` stable?

No. `mu.exec` is explicitly experimental. Only symbols exported from top-level `mu` are stable.

## Can I decode directly to AST types?

Yes. `decode(...)` and typed parse APIs can target AST classes such as `Expr` subclasses where appropriate.

## Does decode preserve source location?

Yes, when parse spans are available. `DecodeError.span` includes source token/span metadata when present.

## Which package name do I install?

Install `lang-mu` from PyPI:

```bash
pip install lang-mu
```

Import from `mu`:

```python
from mu import parse, parse_one
```
