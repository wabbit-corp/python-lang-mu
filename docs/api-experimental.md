# Experimental API Reference

_Generated from code by `scripts/generate_api_docs.py`. Do not edit by hand._

Experimental APIs are imported from `mu.exec` and are not covered by stable compatibility guarantees.

## Exported Symbols

| Name | Kind | Signature | Defined In | Summary |
|---|---|---|---|---|
| `EvalContext` | class |  | `mu.exec` | Evaluation context holding callable/value bindings. |
| `eval_expr` | function | `(ctx: mu.exec.EvalContext, e: mu.types.Document \| mu.types.Expr \| list[mu.types.Expr], ignore_toplevel_exceptions: bool = False) -> Any` | `mu.exec` | Evaluate Mu expressions using a provided `EvalContext`. |
| `EvalNameError` | class |  | `mu.exec` | Raised when evaluating an unbound symbol name. |
