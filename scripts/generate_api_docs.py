#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ApiEntry:
    name: str
    kind: str
    signature: str
    module: str
    summary: str


def _kind_of(obj: Any) -> str:
    if inspect.isclass(obj):
        return "class"
    if inspect.isfunction(obj):
        return "function"
    if getattr(obj, "__origin__", None) is not None:
        return "type alias"
    return type(obj).__name__


def _signature_of(obj: Any) -> str:
    if not inspect.isfunction(obj):
        return ""
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return ""


def _summary_of(obj: Any) -> str:
    doc = inspect.getdoc(obj)
    if not doc:
        return "No documentation provided."
    return doc.strip().splitlines()[0]


def _escape_cell(text: str) -> str:
    return text.replace("|", "\\|")


def _stable_entries() -> list[ApiEntry]:
    import mu

    entries: list[ApiEntry] = []
    for name in mu.__all__:
        if name == "__version__":
            continue
        obj = getattr(mu, name)
        entries.append(
            ApiEntry(
                name=name,
                kind=_kind_of(obj),
                signature=_signature_of(obj),
                module=getattr(obj, "__module__", "unknown"),
                summary=_summary_of(obj),
            )
        )
    return entries


def _experimental_entries() -> list[ApiEntry]:
    import mu.exec as mu_exec

    names = ["EvalContext", "eval_expr", "EvalNameError"]
    entries: list[ApiEntry] = []
    for name in names:
        obj = getattr(mu_exec, name)
        entries.append(
            ApiEntry(
                name=name,
                kind=_kind_of(obj),
                signature=_signature_of(obj),
                module=getattr(obj, "__module__", "unknown"),
                summary=_summary_of(obj),
            )
        )
    return entries


def _render_table(entries: list[ApiEntry]) -> str:
    lines = [
        "| Name | Kind | Signature | Defined In | Summary |",
        "|---|---|---|---|---|",
    ]
    for entry in entries:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_escape_cell(entry.name)}`",
                    _escape_cell(entry.kind),
                    f"`{_escape_cell(entry.signature)}`" if entry.signature else "",
                    f"`{_escape_cell(entry.module)}`",
                    _escape_cell(entry.summary),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _render_stable(entries: list[ApiEntry]) -> str:
    return (
        "# Stable API Reference\n\n"
        "_Generated from code by `scripts/generate_api_docs.py`. Do not edit by hand._\n\n"
        "Stable APIs are imported from top-level `mu`.\n\n"
        "## Exported Symbols\n\n"
        f"{_render_table(entries)}\n"
    )


def _render_experimental(entries: list[ApiEntry]) -> str:
    return (
        "# Experimental API Reference\n\n"
        "_Generated from code by `scripts/generate_api_docs.py`. Do not edit by hand._\n\n"
        "Experimental APIs are imported from `mu.exec` and are not covered by stable compatibility guarantees.\n\n"
        "## Exported Symbols\n\n"
        f"{_render_table(entries)}\n"
    )


def _write_or_check(path: Path, content: str, check: bool) -> int:
    normalized = content if content.endswith("\n") else content + "\n"
    if check:
        if not path.exists():
            print(f"[ERROR] Missing generated file: {path}")
            return 1
        existing = path.read_text(encoding="utf-8")
        if existing != normalized:
            print(f"[ERROR] Generated file is out of date: {path}")
            print("Run: python scripts/generate_api_docs.py")
            return 1
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalized, encoding="utf-8")
    print(f"[OK] Wrote {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate API reference markdown from exported code symbols.")
    parser.add_argument("--check", action="store_true", help="Fail if generated files are out of date.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    stable_out = repo_root / "docs" / "api-stable.md"
    experimental_out = repo_root / "docs" / "api-experimental.md"

    stable_content = _render_stable(_stable_entries())
    experimental_content = _render_experimental(_experimental_entries())

    rc = 0
    rc |= _write_or_check(stable_out, stable_content, args.check)
    rc |= _write_or_check(experimental_out, experimental_content, args.check)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
