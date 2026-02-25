# Changelog

All notable changes to this project are documented in this file.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
