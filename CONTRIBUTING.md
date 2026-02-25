# Contributing

## Scope

This project ships a public parsing/typed-decoding library.
Documentation and changelog accuracy are part of the release contract.

## Required For User-Visible Changes

If a change affects exported behavior, public symbols, error semantics, docs examples, or packaging metadata:

- Update `CHANGELOG.md` under `## [Unreleased]`.
- Update docs in `docs/` and/or `README.md`.
- Regenerate API docs:
  - `python scripts/generate_api_docs.py`

## Documentation Quality Checklist

Run before opening a PR:

```bash
python scripts/generate_api_docs.py --check
python scripts/check_docs_links.py
pytest -q tests/test_docs_snippets.py
codespell README.md docs CHANGELOG.md CONTRIBUTING.md --ignore-words=.codespell-ignore-words.txt
mkdocs build --strict
```

CI enforces these checks and will fail PRs that change user-visible code without docs/changelog updates.
