# Development

## Environment setup

Create and activate a local virtual environment, then install runtime and dev tooling:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e . \
  pytest "mypy>=1.10,<2.0" "ruff>=0.8,<1.0" "black>=24,<26" \
  "mkdocs>=1.6,<2.0" "mkdocs-material>=9.6,<9.7" \
  "codespell>=2.3,<3.0" "build>=1.2,<2.0" "twine>=5,<6"
```

## Checks before opening a PR

Run docs quality checks:

```bash
python scripts/generate_api_docs.py --check
python scripts/check_docs_links.py
python -m pytest -q tests/test_docs_snippets.py
codespell README.md docs CHANGELOG.md CONTRIBUTING.md --ignore-words=.codespell-ignore-words.txt
mkdocs build --strict
```

Run library quality checks:

```bash
python -m pytest -q
python -m ruff check .
python -m mypy mu tests
python -m black --check .
```

Run packaging checks:

```bash
python -m build --sdist --wheel
python -m twine check dist/*
./scripts/check_wheel_contents.sh
```

## User-visible changes

If your change affects public behavior, symbols, docs examples, error semantics, or packaging metadata:

- Update `CHANGELOG.md` under `## [Unreleased]`.
- Update relevant docs in `docs/` and/or `README.md`.
- Regenerate API docs when needed with:
  - `python scripts/generate_api_docs.py`
