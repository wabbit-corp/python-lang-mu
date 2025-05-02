from typing import List, Tuple, Dict, Any, NewType, Callable, Optional, Generic, TypeVar
import typing
import traceback
from dataclasses import dataclass, field
import dataclasses
import re
import inspect
from collections import OrderedDict
from abc import ABC, abstractmethod

from mu.types import SExpr, SAtom, SStr, SGroup, SSeq, SMap, SDoc
from mu.parser import sexpr


class MuNameError(NameError):
    pass


T = TypeVar('T')

class Quoted(Generic[T]):
    def __init__(self, value: T):
        self.value = value

    def __repr__(self) -> str:
        return f'Quoted({self.value!r})'
    

@dataclass
class FunctionSignature:
    arg_names: List[str]
    arg_types: Dict[str, Any]
    return_type: Any

    def __str__(self):
        def format_type(t: Any):
            if t == Any:
                return 'Any'
            # if t has type arguments
            if hasattr(t, '__args__'):
                return f"{t.__origin__.__name__}[{', '.join([format_type(arg) for arg in t.__args__])}]"
            return t.__name__

        args_str = ", ".join([f"{name}: {format_type(self.arg_types[name])}" for name in self.arg_names])
        return_str = self.return_type.__name__
        return f"({args_str}) -> {return_str}"


class CallableObject(ABC):
    @abstractmethod
    def __call__(self, ctx: 'ExecutionContext', *args: Any, **kwargs: Any) -> Any:
        pass

    @abstractmethod
    def get_signature(self) -> FunctionSignature:
        pass


@dataclass
class NativeFunction(CallableObject):
    fn: Callable
    signature: FunctionSignature

    def __call__(self, ctx: 'ExecutionContext', *args: Any, **kwargs: Any) -> Any:
        bound_args = self.signature.arg_names[:len(args)]
        bound_kwargs = {k: v for k, v in kwargs.items() if k in self.signature.arg_names}

        arg_types = self.signature.arg_types

        def eval_arg_maybe(ctx, arg, type):
            if hasattr(type, '__origin__') and type.__origin__ == Quoted:
                assert isinstance(arg, SExpr), f"Expected SExpr, got {type(arg)}"
                assert issubclass(type.__args__[0], SExpr), f"Expected SExpr subtype, got {type.__args__[0]}"
                if not isinstance(arg, type.__args__[0]):
                    raise TypeError(f"Expected {type.__args__[0]}, got {arg}")
                return Quoted(arg)
            return eval_sexpr(ctx, arg)

        # Evaluate all arguments
        evaluated_args = [eval_arg_maybe(ctx, arg, arg_types.get(bound_args[arg_index], Any))
                          for arg_index, arg in enumerate(args)]
        evaluated_kwargs = {k: eval_arg_maybe(ctx, v, arg_types.get(k, Any)) for k, v in kwargs.items()}

        # print(f"Calling {self.fn.__name__} with args: {evaluated_args} and kwargs: {evaluated_kwargs}")

        return self.fn(*evaluated_args, **evaluated_kwargs)

    def get_signature(self) -> FunctionSignature:
        return self.signature


@dataclass
class ExecutionContext:
    env: Dict[str, Any] = field(default_factory=dict)

    def register(self, func: Callable | None = None, name: Optional[str] = None) -> Callable | NativeFunction:
        name_override = name
        def decorator(f):
            sig = inspect.signature(f)
            arg_names = list(sig.parameters.keys())
            type_hints = typing.get_type_hints(f)

            arg_types = {name: type_hints.get(name, Any) for name in arg_names}
            return_type = type_hints.get('return', Any)

            func_signature = FunctionSignature(arg_names, arg_types, return_type)
            native_func = NativeFunction(f, func_signature)
            name = name_override or f.__name__
            self.env[name] = native_func
            return native_func

        if func is None:
            return decorator
        else:
            return decorator(func)

    def get_function_signature(self, func_name: str) -> str:
        if func_name not in self.env or not isinstance(self.env[func_name], CallableObject):
            return f"Function '{func_name}' not found"

        return str(self.env[func_name].get_signature())


def eval_sexpr(ctx: ExecutionContext, e: SDoc | SExpr | List[SExpr], ignore_toplevel_exceptions: bool = False) -> Any:
    if isinstance(e, SDoc):
        return [eval_sexpr(ctx, x) for x in e.exprs]
    if isinstance(e, list):
        return [eval_sexpr(ctx, x) for x in e]
    
    assert isinstance(e, SExpr), f"Expected SExpr, got {type(e)}"

    match e:
        case SAtom(a):
            if a.startswith('py.'):
                a = a[3:]
                module, attr = a.rsplit('/', 1)
                import importlib
                module_obj = importlib.import_module(module)
                result = getattr(module_obj, attr)
                if hasattr(result, '__call__'):
                    sig = inspect.signature(result)
                    arg_names = list(sig.parameters.keys())
                    type_hints = typing.get_type_hints(result)
                    arg_types = {name: type_hints.get(name, Any) for name in arg_names}
                    return_type = type_hints.get('return', Any)
                    func_signature = FunctionSignature(arg_names, arg_types, return_type)
                    return NativeFunction(result, func_signature)
                return result

            if a not in ctx.env:
                raise MuNameError(f"Name '{a}' is not defined")

            return ctx.env[a]

        case SStr(s):
            if '$' in s:
                result = ''
                last_end = 0
                for m in re.finditer(r'\$\{([^\}]+)\}|\$\$', s):
                    result += s[last_end:m.start()]
                    if m.group() == '$$':
                        result += '$'
                    else:
                        result += str(eval_sexpr(ctx, sexpr(m.group(1)).exprs)[-1])
                    last_end = m.end()

                result += s[last_end:]

                return result

            return s

        case SSeq(s):
            return [eval_sexpr(ctx, e) for e in s]

        case SMap(s):
            result = OrderedDict()
            for field in s:
                result[eval_sexpr(ctx, field.key)] = eval_sexpr(ctx, field.value)
            return result

        case SGroup(g):
            assert len(g) > 0, "Empty group"

            try:
                fn = eval_sexpr(ctx, g[0])
                tail = g[1:]
                args = []
                kwargs = {}
                for index, arg in enumerate(tail):
                    if isinstance(arg, SAtom) and arg.value.startswith(':'):
                        key = arg.value[1:]
                        assert index + 1 < len(g), f"Missing value for keyword argument {key}"
                        assert key not in kwargs, f"Duplicate keyword argument {key}"
                        kwargs[key] = tail[index + 1]
                    elif arg not in kwargs.values():
                        args.append(arg)

                if isinstance(fn, CallableObject):
                    return fn(ctx, *args, **kwargs)
                elif callable(fn):
                    evaluated_args = [eval_sexpr(ctx, arg) for arg in args]
                    evaluated_kwargs = {k: eval_sexpr(ctx, v) for k, v in kwargs.items()}
                    return fn(*evaluated_args, **evaluated_kwargs)
                else:
                    raise TypeError(f"Cannot call {fn}")
            except Exception as e:
                if ignore_toplevel_exceptions:
                    import traceback
                    traceback.print_exc()
                    return e
                else:
                    raise e