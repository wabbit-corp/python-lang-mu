from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import pytest

from mu.arg_match import (
    AmbiguousPositionalArgumentException,
    ArgArity,
    DuplicateArgumentException,
    MatchArgsException,
    MissingArgumentException,
    NamedArg,
    NamedArgumentRequiresValueException,
    PositionalArg,
    PositionalArgumentsAfterOutOfOrderNamedArgumentException,
    TooManyArgumentsException,
    UnknownArgumentException,
    match_args,
)

E = TypeVar("E", bound=Exception)


def parse_param_defs(args: str) -> list[tuple[ArgArity, str]]:
    result: list[tuple[ArgArity, str]] = []
    for arg in args.split():
        if arg.endswith("?"):
            result.append((ArgArity.Optional, arg[:-1]))
        elif arg.endswith("*"):
            result.append((ArgArity.ZeroOrMore, arg[:-1]))
        elif arg.endswith("+"):
            result.append((ArgArity.OneOrMore, arg[:-1]))
        else:
            result.append((ArgArity.Required, arg))
    return result


def parse_args(args: str) -> list[NamedArg[str] | PositionalArg[str]]:
    result: list[NamedArg[str] | PositionalArg[str]] = []
    for arg in args.split():
        if arg.startswith(":"):
            result.append(NamedArg(arg[1:]))
        else:
            result.append(PositionalArg(arg))
    return result


def assert_match(param_defs: str, args: str, expected_map: dict[str, list[str]]) -> None:
    params = parse_param_defs(param_defs)
    arguments = parse_args(args)
    actual_map = match_args(params, arguments)
    assert actual_map == expected_map


def assert_match_fails(
    exc_type: type[E],
    param_defs: str,
    args: str,
    condition: Callable[[E], bool] | None = None,
) -> None:
    params = parse_param_defs(param_defs)
    arguments = parse_args(args)
    with pytest.raises(exc_type) as exc:
        match_args(params, arguments)
    if condition is not None:
        assert condition(exc.value)


def test_helper_functions() -> None:
    param_defs = parse_param_defs("x y z?")
    assert param_defs == [
        (ArgArity.Required, "x"),
        (ArgArity.Required, "y"),
        (ArgArity.Optional, "z"),
    ]
    args = parse_args("x y :z z")
    assert args == [PositionalArg("x"), PositionalArg("y"), NamedArg("z"), PositionalArg("z")]
    assert parse_param_defs("") == []
    assert parse_args("") == []


def test_empty_definitions_or_args() -> None:
    assert_match("", "", {})
    assert_match_fails(
        TooManyArgumentsException,
        "",
        "a",
        lambda e: e.values == ["a"],
    )
    assert_match_fails(
        UnknownArgumentException,
        "",
        ":a a",
        lambda e: e.names == ["a"],
    )

    assert_match("x?", "", {"x": []})
    assert_match("x*", "", {"x": []})
    assert_match_fails(
        MissingArgumentException,
        "x",
        "",
        lambda e: e.names == ["x"],
    )
    assert_match_fails(
        MissingArgumentException,
        "x+",
        "",
        lambda e: e.names == ["x"],
    )
    assert_match_fails(
        MissingArgumentException,
        "x y",
        "",
        lambda e: e.names == ["x", "y"],
    )


def test_duplicate_variations() -> None:
    assert_match_fails(
        DuplicateArgumentException,
        "x y",
        "a :x b",
        lambda e: e.name == "x",
    )
    assert_match_fails(
        TooManyArgumentsException,
        "x y",
        ":x a b c",
        lambda e: e.values == ["c"],
    )
    assert_match(
        "x y*",
        "a :y b :y c",
        {"x": ["a"], "y": ["b", "c"]},
    )


def test_req_req_req_req() -> None:
    params = "x y z w"
    expected = {"x": ["x"], "y": ["y"], "z": ["z"], "w": ["w"]}

    assert_match(params, "x y z w", expected)
    assert_match(params, ":x x :y y :z z :w w", expected)
    assert_match(params, ":y y :x x :z z :w w", expected)
    assert_match(params, ":x x y z w", expected)
    assert_match(params, ":x x y :w w :z z", expected)

    assert_match_fails(
        PositionalArgumentsAfterOutOfOrderNamedArgumentException,
        params,
        ":y y x z w",
    )
    assert_match_fails(
        PositionalArgumentsAfterOutOfOrderNamedArgumentException,
        params,
        "x :z z y w",
    )
    assert_match_fails(
        PositionalArgumentsAfterOutOfOrderNamedArgumentException,
        params,
        "x y :w w z",
    )
    assert_match_fails(
        PositionalArgumentsAfterOutOfOrderNamedArgumentException,
        params,
        ":x x y :w w z",
    )
    assert_match_fails(
        TooManyArgumentsException,
        params,
        "x y z w extra",
        lambda e: e.values == ["extra"],
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        "x y z",
        lambda e: e.names == ["w"],
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        ":x x :y y z",
        lambda e: e.names == ["w"],
    )
    assert_match_fails(
        DuplicateArgumentException,
        params,
        "x y z w :x extra",
        lambda e: e.name == "x",
    )
    assert_match_fails(
        UnknownArgumentException,
        params,
        "x y z :unknown u",
        lambda e: e.names == ["unknown"],
    )
    assert_match_fails(
        NamedArgumentRequiresValueException,
        params,
        "x y z :w",
        lambda e: e.names == ["w"],
    )


def test_req_req_star() -> None:
    params = "x y z*"
    assert_match(params, "x y", {"x": ["x"], "y": ["y"], "z": []})
    assert_match(params, "x y z", {"x": ["x"], "y": ["y"], "z": ["z"]})
    assert_match(
        params,
        "x y z1 z2 z3",
        {"x": ["x"], "y": ["y"], "z": ["z1", "z2", "z3"]},
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        "x",
        lambda e: e.names == ["y"],
    )


def test_req_req_plus() -> None:
    params = "x y z+"
    assert_match(
        params,
        "x y z1",
        {"x": ["x"], "y": ["y"], "z": ["z1"]},
    )
    assert_match(
        params,
        "x y z1 z2 z3",
        {"x": ["x"], "y": ["y"], "z": ["z1", "z2", "z3"]},
    )
    assert_match(
        params,
        ":y y :x x :z z1 z2",
        {"x": ["x"], "y": ["y"], "z": ["z1", "z2"]},
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        "x y",
        lambda e: e.names == ["z"],
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        ":x x :y y",
        lambda e: e.names == ["z"],
    )
    assert_match_fails(
        NamedArgumentRequiresValueException,
        params,
        ":x x :y y :z",
        lambda e: e.names == ["z"],
    )


def test_req_req_opt() -> None:
    params = "x y z?"
    assert_match(params, "x y", {"x": ["x"], "y": ["y"], "z": []})
    assert_match(params, "x y z1", {"x": ["x"], "y": ["y"], "z": ["z1"]})
    assert_match(params, ":x x :y y", {"x": ["x"], "y": ["y"], "z": []})
    assert_match(params, ":y y :x x :z z1", {"x": ["x"], "y": ["y"], "z": ["z1"]})
    assert_match(params, ":z z1 :y y :x x", {"x": ["x"], "y": ["y"], "z": ["z1"]})

    assert_match_fails(TooManyArgumentsException, params, "x y z1 z2")
    assert_match_fails(
        DuplicateArgumentException,
        params,
        "x y :z z1 :z z2",
        lambda e: e.name == "z",
    )


def test_req_star_req() -> None:
    params = "x y* z"
    assert_match(params, "x z", {"x": ["x"], "y": [], "z": ["z"]})
    assert_match(params, "x y1 z", {"x": ["x"], "y": ["y1"], "z": ["z"]})
    assert_match(
        params,
        "x y1 y2 y3 z",
        {"x": ["x"], "y": ["y1", "y2", "y3"], "z": ["z"]},
    )
    assert_match(params, ":x x :z z", {"x": ["x"], "y": [], "z": ["z"]})
    assert_match(params, "x :z z", {"x": ["x"], "y": [], "z": ["z"]})
    assert_match(params, "x :y y1 :z z", {"x": ["x"], "y": ["y1"], "z": ["z"]})
    assert_match(params, ":x x :y y :z z", {"x": ["x"], "y": ["y"], "z": ["z"]})
    assert_match(params, ":y y :x x :z z", {"x": ["x"], "y": ["y"], "z": ["z"]})
    assert_match(
        params,
        ":x x :y y1 y2 y3 :z z",
        {"x": ["x"], "y": ["y1", "y2", "y3"], "z": ["z"]},
    )
    assert_match(
        params,
        ":x x :y y1 :y y2 :z z",
        {"x": ["x"], "y": ["y1", "y2"], "z": ["z"]},
    )
    assert_match(
        params,
        ":x x :z z :y y1 y2 y3",
        {"x": ["x"], "y": ["y1", "y2", "y3"], "z": ["z"]},
    )
    assert_match(params, "x y1 :z z", {"x": ["x"], "y": ["y1"], "z": ["z"]})

    assert_match_fails(
        MissingArgumentException,
        params,
        ":y a",
        lambda e: e.names == ["x", "z"],
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        ":x a :y b",
        lambda e: e.names == ["z"],
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        ":y b :z c",
        lambda e: e.names == ["x"],
    )


def test_req_star_star() -> None:
    params = "x y* z*"
    assert_match(params, "x", {"x": ["x"], "y": [], "z": []})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "x a")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "x a b")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "x a b c")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "x y1 :z z1")

    assert_match(params, ":x x", {"x": ["x"], "y": [], "z": []})
    assert_match(params, "x :y y1", {"x": ["x"], "y": ["y1"], "z": []})
    assert_match(params, "x :z z1", {"x": ["x"], "y": [], "z": ["z1"]})
    assert_match(params, "x :y y1 :z z1", {"x": ["x"], "y": ["y1"], "z": ["z1"]})
    assert_match(
        params,
        "x :y y1 y2 :z z1 z2 z3",
        {"x": ["x"], "y": ["y1", "y2"], "z": ["z1", "z2", "z3"]},
    )
    assert_match(
        params,
        "x :y y1 :y y2 :y y3 :z z1 z2 z3",
        {"x": ["x"], "y": ["y1", "y2", "y3"], "z": ["z1", "z2", "z3"]},
    )
    assert_match(
        params,
        "x :y y1 :y y2 :z z1 :z z2 :z z3",
        {"x": ["x"], "y": ["y1", "y2"], "z": ["z1", "z2", "z3"]},
    )
    assert_match(params, "x :y y1 y2", {"x": ["x"], "y": ["y1", "y2"], "z": []})


def test_req_star_star_req_req() -> None:
    params = "x y* z* w a"
    assert_match_fails(AmbiguousPositionalArgumentException, params, "x y1 z1 w a")

    assert_match(
        params,
        "x :y y1 :z z1 :w w :a a",
        {"x": ["x"], "y": ["y1"], "z": ["z1"], "w": ["w"], "a": ["a"]},
    )
    assert_match(
        params,
        "x :w w :a a",
        {"x": ["x"], "y": [], "z": [], "w": ["w"], "a": ["a"]},
    )
    assert_match(
        params,
        "x :y y1 y2 :w w :a a",
        {"x": ["x"], "y": ["y1", "y2"], "z": [], "w": ["w"], "a": ["a"]},
    )
    assert_match(
        params,
        "x :z z1 z2 :w w :a a",
        {"x": ["x"], "y": [], "z": ["z1", "z2"], "w": ["w"], "a": ["a"]},
    )
    assert_match(
        params,
        "x :y y1 :z z1 :w w :a a",
        {"x": ["x"], "y": ["y1"], "z": ["z1"], "w": ["w"], "a": ["a"]},
    )

    assert_match_fails(MissingArgumentException, params, "a :y b :z c d e")
    assert_match_fails(MissingArgumentException, params, "a :y b c d")


def test_regression() -> None:
    params = "from preceded-by? not-preceded-by? to probability min-alcohol?"
    args = ":from x :to y :probability 6 :min-alcohol 80"
    expected = {
        "from": ["x"],
        "preceded-by": [],
        "not-preceded-by": [],
        "to": ["y"],
        "probability": ["6"],
        "min-alcohol": ["80"],
    }
    assert_match(params, args, expected)


def test_req_opt_req() -> None:
    params = "x y? z"
    assert_match(params, "x z", {"x": ["x"], "y": [], "z": ["z"]})
    assert_match(params, "x y z", {"x": ["x"], "y": ["y"], "z": ["z"]})
    assert_match(params, "x :z z", {"x": ["x"], "y": [], "z": ["z"]})
    assert_match(params, "x :y y :z z", {"x": ["x"], "y": ["y"], "z": ["z"]})

    assert_match_fails(
        PositionalArgumentsAfterOutOfOrderNamedArgumentException,
        params,
        ":z z x",
    )
    assert_match_fails(
        PositionalArgumentsAfterOutOfOrderNamedArgumentException,
        params,
        ":z z x y",
    )
    assert_match_fails(
        PositionalArgumentsAfterOutOfOrderNamedArgumentException,
        params,
        ":y y :z z x",
    )
    assert_match_fails(TooManyArgumentsException, params, "x :z z y")
    assert_match_fails(TooManyArgumentsException, params, "x y z extra")
    assert_match_fails(
        MissingArgumentException,
        params,
        "x",
        lambda e: e.names == ["z"],
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        ":y y",
        lambda e: e.names == ["x", "z"],
    )


def test_opt_star() -> None:
    params = "x? y*"
    assert_match(params, "", {"x": [], "y": []})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c")
    assert_match(params, ":x vx", {"x": ["vx"], "y": []})
    assert_match(params, ":y vy1", {"x": [], "y": ["vy1"]})
    assert_match(params, ":y y1 y2", {"x": [], "y": ["y1", "y2"]})
    assert_match(params, ":x vx :y vy1 vy2", {"x": ["vx"], "y": ["vy1", "vy2"]})
    assert_match(params, ":y vy1 vy2 :x vx", {"x": ["vx"], "y": ["vy1", "vy2"]})


def test_plus_req() -> None:
    params = "x+ y"
    assert_match(params, "a b", {"x": ["a"], "y": ["b"]})
    assert_match(params, "a b c", {"x": ["a", "b"], "y": ["c"]})
    assert_match(params, ":y a :x b c", {"x": ["b", "c"], "y": ["a"]})
    assert_match(params, ":x a b :y c", {"x": ["a", "b"], "y": ["c"]})

    assert_match_fails(MatchArgsException, params, "a")
    assert_match_fails(
        MissingArgumentException,
        params,
        ":y a",
        lambda e: e.names == ["x"],
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        ":x a",
        lambda e: e.names == ["y"],
    )
    assert_match_fails(
        NamedArgumentRequiresValueException,
        params,
        ":y a :x",
        lambda e: e.names == ["x"],
    )
    assert_match_fails(
        NamedArgumentRequiresValueException,
        params,
        ":x :y a",
        lambda e: e.names == ["x"],
    )


def test_plus_star() -> None:
    params = "a+ b*"
    assert_match(params, "x", {"a": ["x"], "b": []})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "x y")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "x y z w")
    assert_match(params, ":a x :b y", {"a": ["x"], "b": ["y"]})
    assert_match(params, ":b x y :a z w", {"a": ["z", "w"], "b": ["x", "y"]})
    assert_match_fails(
        MissingArgumentException,
        params,
        "",
        lambda e: e.names == ["a"],
    )


def test_plus_opt() -> None:
    params = "a+ b?"
    assert_match(params, "x", {"a": ["x"], "b": []})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "x y")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "x y z")
    assert_match(params, ":a x :b y", {"a": ["x"], "b": ["y"]})
    assert_match(params, ":b x :a y z", {"a": ["y", "z"], "b": ["x"]})
    assert_match_fails(
        MissingArgumentException,
        params,
        "",
        lambda e: e.names == ["a"],
    )


def test_req_opt_star_req() -> None:
    params = "x y? z* w"
    assert_match(params, "a b", {"x": ["a"], "y": [], "z": [], "w": ["b"]})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c")
    assert_match(params, ":w a :x b", {"x": ["b"], "y": [], "z": [], "w": ["a"]})
    assert_match_fails(PositionalArgumentsAfterOutOfOrderNamedArgumentException, params, ":w a b")
    assert_match(params, "a :w b", {"x": ["a"], "y": [], "z": [], "w": ["b"]})
    assert_match_fails(PositionalArgumentsAfterOutOfOrderNamedArgumentException, params, ":w a b c")


def test_plus_plus() -> None:
    params = "x+ y+"
    assert_match_fails(
        MissingArgumentException,
        params,
        "",
        lambda e: e.names == ["x", "y"],
    )
    assert_match_fails(MissingArgumentException, params, "a")
    assert_match(params, "a b", {"x": ["a"], "y": ["b"]})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c")
    assert_match(params, ":x a :y b", {"x": ["a"], "y": ["b"]})
    assert_match(params, ":x a b :y c d", {"x": ["a", "b"], "y": ["c", "d"]})
    assert_match(params, ":y c d :x a b", {"x": ["a", "b"], "y": ["c", "d"]})
    assert_match_fails(
        MissingArgumentException,
        params,
        ":x a",
        lambda e: e.names == ["y"],
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        ":y b",
        lambda e: e.names == ["x"],
    )


def test_star_plus() -> None:
    params = "x* y+"
    assert_match_fails(
        MissingArgumentException,
        params,
        "",
        lambda e: e.names == ["y"],
    )
    assert_match(params, "a", {"x": [], "y": ["a"]})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b")
    assert_match(params, ":y a", {"x": [], "y": ["a"]})
    assert_match(params, ":x a :y b", {"x": ["a"], "y": ["b"]})
    assert_match(params, ":x a b :y c d", {"x": ["a", "b"], "y": ["c", "d"]})
    assert_match_fails(
        MissingArgumentException,
        params,
        ":x a",
        lambda e: e.names == ["y"],
    )


def test_plus_star_plus() -> None:
    params = "x+ y* z+"
    assert_match_fails(MissingArgumentException, params, "")
    assert_match_fails(MissingArgumentException, params, "a")
    assert_match(params, "a b", {"x": ["a"], "y": [], "z": ["b"]})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c d")
    assert_match(params, ":x a :z b", {"x": ["a"], "y": [], "z": ["b"]})
    assert_match(params, ":x a :y b :z c", {"x": ["a"], "y": ["b"], "z": ["c"]})
    assert_match(
        params,
        ":x a d :y b e :z c f",
        {"x": ["a", "d"], "y": ["b", "e"], "z": ["c", "f"]},
    )


def test_plus_opt_req() -> None:
    params = "x+ y? z"
    assert_match_fails(MissingArgumentException, params, "")
    assert_match(params, "a b", {"x": ["a"], "y": [], "z": ["b"]})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c d")
    assert_match(params, ":x a :z c", {"x": ["a"], "y": [], "z": ["c"]})
    assert_match(params, ":x a :y b :z c", {"x": ["a"], "y": ["b"], "z": ["c"]})
    assert_match_fails(
        MissingArgumentException,
        params,
        ":x a",
        lambda e: e.names == ["z"],
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        ":z c",
        lambda e: e.names == ["x"],
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        ":y a",
        lambda e: e.names == ["x", "z"],
    )


def test_opt_plus_req() -> None:
    params = "x? y+ z"
    assert_match_fails(MissingArgumentException, params, "")
    assert_match(params, "a b", {"x": [], "y": ["a"], "z": ["b"]})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c d")
    assert_match(params, ":y b :z c", {"x": [], "y": ["b"], "z": ["c"]})
    assert_match(params, ":x a :y b :z c", {"x": ["a"], "y": ["b"], "z": ["c"]})
    assert_match_fails(
        MissingArgumentException,
        params,
        ":y b",
        lambda e: e.names == ["z"],
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        ":x a :z c",
        lambda e: e.names == ["y"],
    )


def test_req_plus_opt_req() -> None:
    params = "x y+ z? w"
    assert_match_fails(MissingArgumentException, params, "")
    assert_match(params, "a b c", {"x": ["a"], "y": ["b"], "z": [], "w": ["c"]})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c d")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c d e")
    assert_match(params, ":x a :y b :w d", {"x": ["a"], "y": ["b"], "z": [], "w": ["d"]})
    assert_match(
        params,
        ":x a :y b :z c :w d",
        {"x": ["a"], "y": ["b"], "z": ["c"], "w": ["d"]},
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        ":x a :y b",
        lambda e: e.names == ["w"],
    )
    assert_match_fails(
        MissingArgumentException,
        params,
        ":x a :w d",
        lambda e: e.names == ["y"],
    )


def test_opt_req() -> None:
    params = "x? y"
    assert_match(params, "b", {"x": [], "y": ["b"]})
    assert_match(params, "a b", {"x": ["a"], "y": ["b"]})
    assert_match(params, ":y b", {"x": [], "y": ["b"]})
    assert_match(params, ":x a :y b", {"x": ["a"], "y": ["b"]})
    assert_match_fails(
        MissingArgumentException,
        params,
        ":x a",
        lambda e: e.names == ["y"],
    )


def test_star_opt() -> None:
    params = "x* y?"
    assert_match(params, "", {"x": [], "y": []})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b")
    assert_match(params, ":x a", {"x": ["a"], "y": []})
    assert_match(params, ":y b", {"x": [], "y": ["b"]})
    assert_match(params, ":x a b :y c", {"x": ["a", "b"], "y": ["c"]})


def test_star_req_star() -> None:
    params = "x* y z*"
    assert_match_fails(MissingArgumentException, params, "")
    assert_match(params, "a", {"x": [], "y": ["a"], "z": []})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c d")
    assert_match(params, ":y b :z c", {"x": [], "y": ["b"], "z": ["c"]})
    assert_match(params, ":x a :y b :z c", {"x": ["a"], "y": ["b"], "z": ["c"]})
    assert_match(params, ":y b", {"x": [], "y": ["b"], "z": []})
    assert_match_fails(
        MissingArgumentException,
        params,
        ":x a :z c",
        lambda e: e.names == ["y"],
    )


def test_star_req_req_star() -> None:
    params = "x* y z w*"
    assert_match_fails(MissingArgumentException, params, "")
    assert_match_fails(MissingArgumentException, params, "a")
    assert_match(params, "a b", {"x": [], "y": ["a"], "z": ["b"], "w": []})
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c")
    assert_match_fails(AmbiguousPositionalArgumentException, params, "a b c d")
