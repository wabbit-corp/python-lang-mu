import pytest

from mu.exec import EvalContext, EvalNameError, Quoted, eval_expr
from mu.types import AtomExpr, Expr, GroupExpr, SequenceExpr, StringExpr


@pytest.fixture
def ctx():
    return EvalContext()


# def test_register_and_call(ctx):
#     @ctx.register
#     def add(a: int, b: int) -> int:
#         return a + b

#     expr = GroupExpr([
#         AtomExpr("add"),
#         AtomExpr("3"),
#         AtomExpr("4")
#     ])
#     result = eval_expr(ctx, expr)
#     assert result == 7


def test_name_not_found(ctx):
    with pytest.raises(EvalNameError):
        eval_expr(ctx, AtomExpr("not_found"))


def test_python_attribute_lookup(ctx):
    sin_expr = AtomExpr("py.math/sin")
    sin_fn = eval_expr(ctx, sin_expr)
    assert callable(sin_fn.fn)
    assert sin_fn.fn.__name__ == "sin"
    import math

    assert sin_fn.fn is math.sin


# def test_empty_group(ctx):
#     with pytest.raises(MuTypeError):
#         eval_expr(ctx, GroupExpr([]))


def test_string_interpolation(ctx):
    @ctx.register
    def get_user() -> str:
        return "World"

    s = StringExpr("Hello, ${(get_user)}!")
    result = eval_expr(ctx, s)
    assert result == "Hello, World!"


def test_function_signatures(ctx):
    @ctx.register
    def add(a: int, b: int) -> int:
        return a + b

    @ctx.register
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    @ctx.register
    def quotes(name: Quoted[Expr], data: Quoted[AtomExpr]) -> str:
        assert name.value == StringExpr("Alice")
        assert data.value == AtomExpr("data")
        return f"Hello, {name}!"

    # Print function signatures
    assert str(ctx.get_function_signature("add")) == "(a: int, b: int) -> int"
    assert str(ctx.get_function_signature("greet")) == "(name: str) -> str"
    assert (
        str(ctx.get_function_signature("quotes"))
        == "(name: Quoted[Expr], data: Quoted[AtomExpr]) -> str"
    )

    @ctx.register(name="app-jvm")
    def app_jvm(name: str, main: str, dependencies: list[str]) -> str:
        return f"Creating JVM app: {name} with main class {main} and dependencies: {dependencies}"

    # Why is it list[str], not List[str]?
    assert (
        str(ctx.get_function_signature("app-jvm"))
        == "(name: str, main: str, dependencies: list[str]) -> str"
    )


def test_quoted(ctx):
    @ctx.register
    def quotes(name: Quoted[Expr], data: Quoted[AtomExpr]) -> str:
        assert name.value == StringExpr("Alice")
        assert data.value == AtomExpr("data")
        return f"Hello, {name}!"

    eval_expr(ctx, GroupExpr([AtomExpr("quotes"), StringExpr("Alice"), AtomExpr("data")]))

    with pytest.raises(TypeError):
        eval_expr(ctx, GroupExpr([AtomExpr("quotes"), StringExpr("Alice"), StringExpr("data")]))


def test_register_without_decorator(ctx):
    # You can still use it without the decorator
    def multiply(a: int, b: int) -> int:
        return a * b

    ctx.register(multiply)
    assert str(ctx.get_function_signature("multiply")) == "(a: int, b: int) -> int"


def test_complex_call(ctx):
    @ctx.register(name="app-jvm")
    def app_jvm(name: str, main: str, dependencies: list[str]) -> str:
        return f"Creating JVM app: {name} with main class {main} and dependencies: {dependencies}"

    # Test the function
    test_input = GroupExpr(
        [
            AtomExpr("app-jvm"),
            StringExpr("app-bitebyte"),
            AtomExpr(":main"),
            StringExpr("datatron.MainKt"),
            AtomExpr(":dependencies"),
            SequenceExpr(
                [
                    StringExpr(":lib-std-base"),
                    StringExpr(":lib-std-logging"),
                    StringExpr(":lib-lang-parsing-parsers"),
                    StringExpr("kotlinx-cli"),
                    StringExpr("sqlite-jdbc"),
                ]
            ),
        ]
    )

    result = eval_expr(ctx, test_input)
    print(result)
