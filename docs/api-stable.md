# Stable API Reference

_Generated from code by `scripts/generate_api_docs.py`. Do not edit by hand._

Stable APIs are imported from top-level `mu`.

## Exported Symbols

| Name | Kind | Signature | Defined In | Summary |
|---|---|---|---|---|
| `ParseError` | class |  | `mu.parser` | Raised when Mu source cannot be parsed into a valid AST. |
| `Quoted` | class |  | `mu.quoted` | Wraps a value that should be passed through without runtime evaluation. |
| `DecodeContext` | class |  | `mu.typed` | Context object passed to custom decoder functions. |
| `DecodeError` | class |  | `mu.typed` | Structured decode error with path/expected/got/span/cause details. |
| `DecodeWith` | class |  | `mu.typed` | Annotated marker for a field-specific custom decode function. |
| `DecoderFn` | type alias |  | `collections.abc` | No documentation provided. |
| `DecoderRegistry` | class |  | `mu.typed` | Registry of target-type-specific decoder functions. |
| `FieldName` | class |  | `mu.typed` | Annotated marker for overriding a dataclass field's Mu argument name. |
| `OneOrMore` | class |  | `mu.typed` | Annotated marker for required variadic field arity (`1..N`). |
| `OptionalArg` | class |  | `mu.typed` | Annotated marker for optional field arity (`0..1`). |
| `ZeroOrMore` | class |  | `mu.typed` | Annotated marker for variadic field arity (`0..N`). |
| `AtomExpr` | class |  | `mu.types` | Atom expression (identifier-like token) node. |
| `Document` | class |  | `mu.types` | Top-level Mu parse result containing one or more expressions. |
| `Expr` | class |  | `mu.types` | Base class for all Mu expression AST nodes. |
| `GroupExpr` | class |  | `mu.types` | Parenthesized expression group node. |
| `MappingExpr` | class |  | `mu.types` | Brace-delimited mapping node. |
| `MappingField` | class |  | `mu.types` | Single key/value field inside a mapping expression. |
| `SequenceExpr` | class |  | `mu.types` | Bracketed sequence node. |
| `StringExpr` | class |  | `mu.types` | String expression node (normal or raw Mu string literal). |
| `load` | function | `(source: 'Source', *, type: 'Any \| None' = None, encoding: 'str' = 'utf-8', registry: 'DecoderRegistry \| None' = None, preserve_spans: 'bool' = False) -> 'Document \| Any'` | `mu.loading` | Load Mu from a path or file-like object. |
| `loads` | function | `(source: 'str', *, type: 'Any \| None' = None, registry: 'DecoderRegistry \| None' = None, preserve_spans: 'bool' = False) -> 'Document \| Any'` | `mu.loading` | Load Mu from a string. |
| `decode` | function | `(expr: 'Expr', target: 'Any', *, registry: 'DecoderRegistry \| None' = None, path: 'str' = '$') -> 'Any'` | `mu.typed` | Decode a pre-parsed Mu `Expr` into a target Python type. |
| `tag` | function | `(tag: 'str') -> 'Callable[[type[T]], type[T]]'` | `mu.typed` | Decorator that overrides the default dataclass tag used during decoding. |
| `parse_many` | function | `(source: 'str', target: 'Any', *, registry: 'DecoderRegistry \| None' = None) -> 'list[Any]'` | `mu.typed` | Parse and decode all top-level Mu expressions as a list. |
| `parse_one` | function | `(source: 'str', target: 'Any', *, registry: 'DecoderRegistry \| None' = None) -> 'Any'` | `mu.typed` | Parse and decode exactly one top-level Mu expression. |
| `parse` | function | `(input: str, preserve_spans: bool = False) -> mu.types.Document` | `mu.parser` | Parse Mu source text into a `Document`. |
