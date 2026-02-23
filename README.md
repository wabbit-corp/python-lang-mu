# mu

`mu` is a Python implementation of the Mu configuration language.
It provides:

- A parser that preserves Mu syntax as an AST.
- A typed decoder that maps Mu expressions into Python dataclasses and typing constructs.
- An experimental runtime evaluator (`mu.exec`) for callable execution semantics.

## Why this library

Mu configuration files can describe nested structures, tagged records, and mixed positional/named arguments.
This package gives you a strict, testable way to parse and decode those configs into Python types.

## Installation

```bash
pip install mu
```

## Quickstart: Parsing

```python
from mu import SDoc, sexpr

doc = sexpr('(app-jvm "demo" :main "demo.Main")')
assert isinstance(doc, SDoc)
assert len(doc.exprs) == 1
```

## Quickstart: Typed decoding

```python
from dataclasses import dataclass
from typing import Annotated

from mu import MuZeroOrMore, parse_one_typed


@dataclass
class Demo:
    name: str
    aliases: Annotated[list[str], MuZeroOrMore]


cfg = parse_one_typed('(demo :name "x" :aliases "a" "b")', Demo)
assert cfg == Demo(name="x", aliases=["a", "b"])
```

## Error handling

Typed decoding raises `MuDecodeError` with structured context:

- `path`: decode path (for example `$.field[0]`)
- `expected`: human-readable expected target/type
- `got`: actual Mu expression description
- `span`: optional source span/token information
- `cause`: optional underlying exception

```python
from dataclasses import dataclass
from mu import MuDecodeError, parse_one_typed


@dataclass
class Counter:
    value: int


try:
    parse_one_typed('(counter :value "not-an-int")', Counter)
except MuDecodeError as e:
    print(e.path, e.expected, e.got)
```

## API contract

### Stable API (`from mu import ...`)

- Parser: `sexpr`, `MuParserError`
- AST: `SExpr`, `SDoc`, `SAtom`, `SStr`, `SGroup`, `SSeq`, `SMap`, `SMapField`
- Typed decoding:
  - `parse_one_typed`, `parse_many_typed`, `decode_expr`
  - `MuDecodeError`, `MuDecodeContext`
  - `MuDeserializerRegistry`, `MuDeserializerFn`, `MuDeserialize`
  - `MuName`, `MuOptional`, `MuZeroOrMore`, `MuOneOrMore`, `mu_tag`
  - `Quoted`

### Experimental API (`from mu.exec import ...`)

- `ExecutionContext`
- `eval_sexpr`
- `MuNameError`

The experimental runtime API is available but not considered stable yet.
Non-exported internals (for example `mu.arg_match` and parser private helpers) are unsupported and may change without notice.

## Python support

- Python `>=3.10`

## License

This project is licensed under **AGPL-3.0-or-later**.
See `LICENSE.md` for full text.

## Development and release checks

```bash
pytest -q
ruff check .
python -m build --sdist --wheel
python -m twine check dist/*
./scripts/check_wheel_contents.sh
```
