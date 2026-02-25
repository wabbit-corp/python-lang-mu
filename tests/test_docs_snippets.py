from __future__ import annotations

import re
import sys
import textwrap
import types
import uuid
from pathlib import Path
from typing import Any

import pytest

PY_SNIPPET_RE = re.compile(r"```python\s*\n(.*?)```", re.DOTALL)


def _markdown_files(repo_root: Path) -> list[Path]:
    files = [repo_root / "README.md"]
    files.extend(sorted((repo_root / "docs").rglob("*.md")))
    return files


def _snippets(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [textwrap.dedent(match.group(1)).strip() for match in PY_SNIPPET_RE.finditer(text)]


def _snippet_params() -> list[Any]:
    repo_root = Path(__file__).resolve().parents[1]
    params: list[Any] = []
    for md_file in _markdown_files(repo_root):
        for index, snippet in enumerate(_snippets(md_file), start=1):
            if not snippet:
                continue
            params.append(
                pytest.param(
                    snippet,
                    id=f"{md_file.relative_to(repo_root)}::{index}",
                )
            )
    return params


@pytest.mark.parametrize("snippet", _snippet_params())
def test_markdown_python_snippet_executes(snippet: str) -> None:
    module_name = f"__docs_snippet_{uuid.uuid4().hex}__"
    module = types.ModuleType(module_name)
    namespace = module.__dict__
    namespace["__name__"] = module_name
    namespace["__file__"] = "<docs-snippet>"
    sys.modules[module_name] = module
    try:
        exec(compile(snippet, "<docs-snippet>", "exec"), namespace, namespace)
    finally:
        sys.modules.pop(module_name, None)
