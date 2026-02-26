from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, cast

import pytest

from mu import DecodeError, Document, GroupExpr, load, loads


@dataclass
class AppJvm:
    name: str
    main: str


def test_loads_returns_document_when_type_is_omitted() -> None:
    doc = loads('(app-jvm "demo" :main "demo.Main")')
    assert isinstance(doc, Document)
    assert isinstance(doc.exprs[0], GroupExpr)


def test_loads_decodes_when_type_is_provided() -> None:
    cfg = loads('(app-jvm "demo" :main "demo.Main")', type=AppJvm)
    assert cfg == AppJvm(name="demo", main="demo.Main")


def test_loads_with_type_requires_single_expression() -> None:
    with pytest.raises(DecodeError):
        loads('(app-jvm "a" :main "A") (app-jvm "b" :main "B")', type=AppJvm)


def test_load_reads_from_path_str_and_path_object(tmp_path: Path) -> None:
    path = tmp_path / "cfg.mu"
    path.write_text('(app-jvm "demo" :main "demo.Main")', encoding="utf-8")

    cfg_from_str = load(str(path), type=AppJvm)
    cfg_from_path = load(path, type=AppJvm)

    assert cfg_from_str == AppJvm(name="demo", main="demo.Main")
    assert cfg_from_path == AppJvm(name="demo", main="demo.Main")


def test_load_reads_from_file_object() -> None:
    with StringIO('(app-jvm "demo" :main "demo.Main")') as f:
        cfg = load(f, type=AppJvm)
    assert cfg == AppJvm(name="demo", main="demo.Main")


def test_load_file_like_must_return_text() -> None:
    with pytest.raises(TypeError):
        load(cast(Any, BytesIO(b"(app-jvm demo)")))


def test_loads_preserve_spans_option() -> None:
    doc = loads('(app-jvm    "demo" :main "demo.Main")', preserve_spans=True)
    assert isinstance(doc, Document)
    assert str(doc) == '(app-jvm    "demo" :main "demo.Main")'
