from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import pytest

from mu import (
    FieldName,
    GroupExpr,
    OneOrMore,
    OptionalArg,
    StringExpr,
    dumps,
    dumps_concise,
    dumps_pretty,
    parse,
)

_ID_NAME = {"id", "name"}


@dataclass
class AppJvm:
    name: str
    main: str
    ports: list[int]
    env: dict[str, str]


@dataclass
class Include:
    path: str


@dataclass
class Demo:
    name: str
    main: str


@dataclass
class Service:
    name: str
    nickname: Annotated[str | None, OptionalArg]
    features: Annotated[list[str], OneOrMore]


@dataclass
class Aliased:
    first_name: Annotated[str, FieldName("display-name")]
    last_name: str


@dataclass
class Slugged:
    slug: str
    main: str


def test_dumps_pretty_document_like_output() -> None:
    source = [
        AppJvm(
            name="billing-api",
            main="billing.Main",
            ports=[8080, 8443],
            env={"profile": "prod", "region": "us-east-1"},
        ),
        Include(path="shared/logging.mu"),
    ]
    result = dumps_pretty(source, first_positional_fields=_ID_NAME)
    assert (
        result
        == """(app-jvm "billing-api"
  :main "billing.Main"
  :ports [8080 8443]
  :env {
    profile: prod,
    region: us-east-1
  }
)

(include "shared/logging.mu")"""
    )


def test_dumps_concise_document_like_output() -> None:
    source = [
        AppJvm(
            name="billing-api",
            main="billing.Main",
            ports=[8080, 8443],
            env={"profile": "prod", "region": "us-east-1"},
        ),
        Include(path="shared/logging.mu"),
    ]
    result = dumps_concise(source, first_positional_fields=_ID_NAME, max_line_length=140)
    assert (
        result
        == '(app-jvm "billing-api" :main "billing.Main" :ports [8080 8443] :env {profile: prod, region: us-east-1})\n'
        '(include "shared/logging.mu")'
    )


def test_dumps_supports_indent_none_vs_pretty() -> None:
    value = Demo(name="billing-api", main="billing.Main")
    concise = dumps(value, indent=None, first_positional_fields=_ID_NAME, single_field_positional=False)
    pretty = dumps(value, indent=2, first_positional_fields=_ID_NAME, single_field_positional=False)
    assert concise == '(demo "billing-api" :main "billing.Main")'
    assert pretty == '(demo "billing-api" :main "billing.Main")'


def test_field_names_default_and_name_flag() -> None:
    value = Demo(name="billing-api", main="billing.Main")
    named = dumps_concise(value, single_field_positional=False)
    positional = dumps_concise(
        value,
        first_positional_fields=_ID_NAME,
        single_field_positional=False,
    )
    assert named == '(demo :name "billing-api" :main "billing.Main")'
    assert positional == '(demo "billing-api" :main "billing.Main")'


def test_custom_first_positional_fields() -> None:
    value = Slugged(slug="billing-api", main="billing.Main")
    default = dumps_concise(
        value,
        first_positional_fields=_ID_NAME,
        single_field_positional=False,
    )
    custom = dumps_concise(
        value,
        first_positional_fields={"slug"},
        single_field_positional=False,
    )
    assert default == '(slugged :slug "billing-api" :main "billing.Main")'
    assert custom == '(slugged "billing-api" :main "billing.Main")'


def test_annotated_values_optional_and_vararg() -> None:
    value = Service(name="api", nickname=None, features=["http", "metrics"])
    result = dumps_concise(
        value,
        first_positional_fields=_ID_NAME,
        single_field_positional=False,
    )
    assert result == '(service "api" :features "http" "metrics")'


def test_annotated_field_name_override() -> None:
    value = Aliased(first_name="Ada", last_name="Lovelace")
    result = dumps_concise(value, single_field_positional=False)
    assert result == '(aliased :display-name "Ada" :last-name "Lovelace")'


def test_max_line_length_wraps_concise_output() -> None:
    value = AppJvm(
        name="billing-api",
        main="billing.Main",
        ports=[8080, 8443],
        env={"profile": "prod", "region": "us-east-1"},
    )
    wrapped = dumps_concise(
        value,
        max_line_length=40,
        first_positional_fields=_ID_NAME,
    )
    assert "\n" in wrapped
    assert wrapped.startswith('(app-jvm "billing-api"')
    assert "\n  :main " in wrapped


def test_dumps_pretty_accepts_document_ast() -> None:
    doc = parse('(app-jvm "demo" :main "demo.Main") (include "shared/logging.mu")')
    result = dumps_pretty(doc, max_line_length=40)
    assert result == '(app-jvm "demo" :main "demo.Main")\n\n(include "shared/logging.mu")'


def test_preserve_spans_roundtrip_for_spanned_document() -> None:
    source = '(app-jvm    "demo"   :main  "demo.Main")\n\n(include   "shared/logging.mu")\n'
    doc = parse(source, preserve_spans=True)
    result = dumps_pretty(doc, preserve_spans=True)
    assert result == source


def test_preserve_spans_falls_back_when_values_are_modified() -> None:
    doc = parse('(app-jvm "demo" :main   "demo.Main")', preserve_spans=True)
    group = doc.exprs[0]
    assert isinstance(group, GroupExpr)
    group.values[1] = StringExpr("billing-api")
    result = dumps_pretty(doc, preserve_spans=True)
    assert result == '(app-jvm "billing-api" :main   "demo.Main")'


def test_one_or_more_empty_raises() -> None:
    value = Service(name="api", nickname=None, features=[])
    with pytest.raises(ValueError):
        dumps_concise(value)
