import pytest

from mu.parser import sexpr, MuParserError
from mu.types import SAtom, SGroup, SSeq, SMap, SStr, SMapField, SExpr
from mu.exec import ExecutionContext, eval_sexpr, MuNameError, Quoted


@pytest.fixture
def ctx():
    return ExecutionContext()

# def test_register_and_call(ctx):
#     @ctx.register
#     def add(a: int, b: int) -> int:
#         return a + b

#     expr = SGroup([
#         SAtom("add"), 
#         SAtom("3"), 
#         SAtom("4")
#     ])
#     result = eval_sexpr(ctx, expr)
#     assert result == 7

def test_name_not_found(ctx):
    with pytest.raises(MuNameError):
        eval_sexpr(ctx, SAtom("not_found"))


def test_python_attribute_lookup(ctx):
    sin_expr = SAtom("py.math/sin")
    sin_fn = eval_sexpr(ctx, sin_expr)
    assert callable(sin_fn.fn)
    assert sin_fn.fn.__name__ == "sin"
    import math
    assert sin_fn.fn is math.sin

# def test_empty_group(ctx):
#     with pytest.raises(MuTypeError):
#         eval_sexpr(ctx, SGroup([]))

def test_string_interpolation(ctx):
    @ctx.register
    def get_user() -> str:
        return "World"
    s = SStr("Hello, ${(get_user)}!")
    result = eval_sexpr(ctx, s)
    assert result == "Hello, World!"

def test_function_signatures(ctx):
    @ctx.register
    def add(a: int, b: int) -> int:
        return a + b

    @ctx.register
    def greet(name: str) -> str:
        return f"Hello, {name}!"
    
    @ctx.register
    def quotes(name: Quoted[SExpr], data: Quoted[SAtom]) -> str:
        assert name.value == SStr("Alice")
        assert data.value == SAtom("data")
        return f"Hello, {name}!"
    
    # Print function signatures
    assert str(ctx.get_function_signature("add")) == "(a: int, b: int) -> int"
    assert str(ctx.get_function_signature("greet")) == "(name: str) -> str"
    assert str(ctx.get_function_signature("quotes")) == "(name: Quoted[SExpr], data: Quoted[SAtom]) -> str"

    @ctx.register(name="app-jvm")
    def app_jvm(name: str, main: str, dependencies: List[str]) -> str:
        return f"Creating JVM app: {name} with main class {main} and dependencies: {dependencies}"

    # Why is it list[str], not List[str]?
    assert str(ctx.get_function_signature("app-jvm")) == "(name: str, main: str, dependencies: list[str]) -> str"
    
def test_quoted(ctx):
    @ctx.register
    def quotes(name: Quoted[SExpr], data: Quoted[SAtom]) -> str:
        assert name.value == SStr("Alice")
        assert data.value == SAtom("data")
        return f"Hello, {name}!"

    eval_sexpr(ctx, SGroup(
        [SAtom("quotes"), SStr("Alice"), SAtom("data")]
    ))

    with pytest.raises(TypeError):
        eval_sexpr(ctx, SGroup(
            [SAtom("quotes"), SStr("Alice"), SStr("data")]
        ))

def test_register_without_decorator(ctx):
    # You can still use it without the decorator
    def multiply(a: int, b: int) -> int:
        return a * b

    ctx.register(multiply)
    assert str(ctx.get_function_signature("multiply")) == "(a: int, b: int) -> int"

def test_complex_call(ctx):
    from typing import List

    @ctx.register(name="app-jvm")
    def app_jvm(name: str, main: str, dependencies: List[str]) -> str:
        return f"Creating JVM app: {name} with main class {main} and dependencies: {dependencies}"

    # Test the function
    test_input = SGroup([
        SAtom("app-jvm"),
        SStr("app-bitebyte"),
        SAtom(":main"), SStr("datatron.MainKt"),
        SAtom(":dependencies"), SSeq([
            SStr(":lib-std-base"),
            SStr(":lib-std-logging"),
            SStr(":lib-lang-parsing-parsers"),
            SStr("kotlinx-cli"),
            SStr("sqlite-jdbc")
        ])
    ])

    result = eval_sexpr(ctx, test_input)
    print(result)