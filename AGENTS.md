# AGENTS

Add repo-specific instructions above or below the managed facts block. Keep manual guidance outside the generated markers.

<!-- BEGIN app-wabbit-dev managed facts -->
## Generated Facts

- Workspace config source of truth: `root.clj` at the workspace root.
- Use `dev where` from this repo to confirm the inferred workspace, repo, and project context.
- Canonical repo target: `python-lang-mu`. Useful entrypoints: `dev project show python-lang-mu`, `dev build python-lang-mu`, `dev check python-lang-mu`.
- Setup-managed files are regenerated with `dev setup python-lang-mu`; avoid hand-editing stamped generated files.
- Sanctioned override files in this repo: `pyproject.extra.toml`, `mkdocs.extra.yml`.
- Review `python-conventions.md` before editing Python code in this repo.
- Configured project types: `python`. Docs: `mkdocs`.
- Repo reference docs: `CHANGELOG.md`.
<!-- END app-wabbit-dev managed facts -->
