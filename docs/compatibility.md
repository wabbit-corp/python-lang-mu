# Compatibility And Stability

## Stable API

Import stable symbols from `mu`:

- Parser APIs
- AST classes
- Typed decode APIs and marker classes
- `Quoted`

The complete stable symbol list is generated into [Stable API](api-stable.md).

## Experimental API

Import runtime APIs only from `mu.exec`:

- `EvalContext`
- `eval_expr`
- `EvalNameError`

The complete experimental symbol list is generated into [Experimental API](api-experimental.md).

## Policy

- Stable API: additive changes only within `0.3.x`.
- Experimental API: may change without deprecation.
- Non-exported internals (for example `mu.arg_match` and parser private helpers) are unsupported.

## Python Support

- Python `>=3.10`
