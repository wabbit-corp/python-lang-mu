#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


@dataclass(frozen=True)
class LinkError:
    file: Path
    line: int
    target: str
    message: str


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+#+\s*$", "", text)
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text


def _heading_slugs(path: Path) -> set[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    for line in lines:
        match = HEADING_RE.match(line)
        if match is None:
            continue
        base = _slugify(match.group(1))
        if not base:
            continue
        count = counts.get(base, 0)
        slug = base if count == 0 else f"{base}-{count}"
        counts[base] = count + 1
        slugs.add(slug)
    return slugs


def _markdown_files(repo_root: Path) -> list[Path]:
    files = [repo_root / "README.md"]
    files.extend(sorted((repo_root / "docs").rglob("*.md")))
    return files


def _normalize_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if " " in target and not target.startswith("http"):
        target = target.split(" ", 1)[0]
    return target


def _validate_target(source: Path, target: str, repo_root: Path) -> list[LinkError]:
    if not target:
        return [LinkError(source, 0, target, "Empty link target")]

    if SCHEME_RE.match(target):
        return []

    path_part, anchor = (target.split("#", 1) + [""])[:2]
    anchor = unquote(anchor)

    if path_part == "":
        resolved = source
    else:
        resolved = (source.parent / path_part).resolve()

    errors: list[LinkError] = []
    if not str(resolved).startswith(str(repo_root.resolve())):
        errors.append(LinkError(source, 0, target, "Link points outside repository"))
        return errors

    if not resolved.exists():
        errors.append(LinkError(source, 0, target, f"Linked file does not exist: {resolved}"))
        return errors

    if anchor and resolved.suffix.lower() == ".md":
        slugs = _heading_slugs(resolved)
        if _slugify(anchor) not in slugs:
            errors.append(LinkError(source, 0, target, f"Missing heading anchor '#{anchor}' in {resolved}"))

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    errors: list[LinkError] = []

    for file_path in _markdown_files(repo_root):
        lines = file_path.read_text(encoding="utf-8").splitlines()
        for line_no, line in enumerate(lines, start=1):
            for match in LINK_RE.finditer(line):
                raw_target = match.group(1)
                target = _normalize_target(raw_target)
                target_errors = _validate_target(file_path, target, repo_root)
                for err in target_errors:
                    errors.append(
                        LinkError(
                            file=err.file,
                            line=line_no,
                            target=err.target,
                            message=err.message,
                        )
                    )

    if errors:
        print("[ERROR] Documentation link check failed:")
        for err in errors:
            print(f"- {err.file}:{err.line}: {err.target} -> {err.message}")
        return 1

    print("[OK] Documentation link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
