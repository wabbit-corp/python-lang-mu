# Changelog

All notable changes to this project are documented in this file.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.2] - 2026-02-26

### Fixed

- Fixed AST `__str__` behavior for nodes without spans:
  - `StringExpr` now emits properly quoted/escaped Mu string literals when spans are absent.
  - `GroupExpr`, `SequenceExpr`, and `MappingExpr` now render canonical concise separators when spans are absent.
  - `MappingField` now renders `key: value` fallback when span separator is absent.
  - `Document.drop_spans()` now drops `leading_space` so spanless documents print concise canonical output.

### Added

- Regression tests for no-span AST string rendering in `tests/test_parser.py`.

## [0.3.1] - 2026-02-26

### Added

- Kotlin-parity parser test coverage in `tests/test_parser_kotlin_parity.py` for:
  - single-quoted strings
  - numeric literals (`SInt`, `SReal`, `SRational`)
  - adjacent comment handling (`foo;bar`)
  - parser error paths raising `ParseError`

### Changed

- Parser behavior aligned with Kotlin reference:
  - parser input failures now raise `ParseError` (no assertion-based user errors)
  - single-quoted strings supported
  - unknown string escapes preserved, `\u{...}` escapes supported
  - numeric literals parsed to typed AST nodes
- Typed decode, printer, and experimental eval runtime updated to handle numeric AST nodes.
- Documentation updated to describe literal parsing behavior and current `0.3.x` compatibility policy.

## [0.3.0] - 2026-02-26

### Added

- `load` and `loads` convenience APIs for string/path/file loading with optional typed decode.
- Mu printer API:
  - `dumps`, `dumps_pretty`, `dumps_concise`
  - dataclass-aware rendering with `Annotated` marker handling
  - line-length-aware pretty/concise layout controls
  - optional span-preserving rendering with fallback for partially modified ASTs

### Changed

- Parser API now uses `preserve_spans` as the span-control parameter.

### Removed

- Removed parser `no_spans` alias.

## [0.2.1] - 2026-02-25

### Added

- MkDocs documentation site with installation, quickstart, typed decoding, error handling, compatibility, and FAQ pages.
- Generated API reference pages (`docs/api-stable.md`, `docs/api-experimental.md`) from exported code symbols.
- Documentation quality checks:
  - markdown link checker (`scripts/check_docs_links.py`)
  - snippet execution tests (`tests/test_docs_snippets.py`)
  - spelling checks in CI (`codespell`)
  - strict docs build (`mkdocs build --strict`)
- CI workflow enforcing docs quality and PR guard for changelog/docs updates on user-visible code changes.

### Changed

- README now links to a full documentation workflow and generated API reference contract.

## [0.2.0] - 2026-02-24

### Changed

- Renamed stable API to normalized naming conventions:
  - Parser: `parse`, `ParseError`
  - AST: `Expr`, `Document`, `AtomExpr`, `StringExpr`, `GroupExpr`, `SequenceExpr`, `MappingExpr`, `MappingField`
  - Typed decoding: `parse_one`, `parse_many`, `decode`, `DecodeError`, `DecodeContext`, `DecoderRegistry`, `DecoderFn`, `DecodeWith`, `FieldName`, `OptionalArg`, `ZeroOrMore`, `OneOrMore`, `tag`
- Renamed experimental runtime API:
  - `EvalContext`, `eval_expr`, `EvalNameError`
- Updated local consumers under sibling workspaces to the new API names.
