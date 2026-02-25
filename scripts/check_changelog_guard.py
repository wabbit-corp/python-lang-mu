#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _run(*args: str) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _changed_files(base_ref: str) -> list[str]:
    subprocess.run(["git", "fetch", "origin", base_ref, "--depth=1"], check=False)
    diff = _run("git", "diff", "--name-only", f"origin/{base_ref}...HEAD")
    return [line.strip() for line in diff.splitlines() if line.strip()]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)

    base_ref = os.environ.get("GITHUB_BASE_REF", "")
    if not base_ref:
        print("[INFO] GITHUB_BASE_REF not set. Skipping changelog/docs guard.")
        return 0

    changed = _changed_files(base_ref)
    if not changed:
        print("[INFO] No changed files detected.")
        return 0

    user_visible = any(path.startswith("mu/") or path == "pyproject.toml" for path in changed)
    docs_updated = any(path.startswith("docs/") or path == "README.md" for path in changed)
    changelog_updated = "CHANGELOG.md" in changed

    if user_visible and not docs_updated:
        print("[ERROR] User-visible code changed, but docs were not updated (docs/ or README.md).")
        return 1

    if user_visible and not changelog_updated:
        print("[ERROR] User-visible code changed, but CHANGELOG.md was not updated.")
        return 1

    print("[OK] Changelog/docs guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
