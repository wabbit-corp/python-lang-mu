from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Generic, TypeVar

ArgumentName = TypeVar("ArgumentName")
ArgumentValue = TypeVar("ArgumentValue")


@dataclass(frozen=True)
class ArgArity:
    min_required: int
    max_required: int | None
    Required: ClassVar[ArgArity]
    Optional: ClassVar[ArgArity]
    ZeroOrMore: ClassVar[ArgArity]
    OneOrMore: ClassVar[ArgArity]

    def __post_init__(self) -> None:
        if self.min_required < 0:
            raise ValueError("min_required must be non-negative")
        if self.max_required is not None and self.max_required < self.min_required:
            raise ValueError("max_required must be >= min_required")

    @property
    def is_vararg(self) -> bool:
        return self.max_required is None

    @property
    def is_nullable(self) -> bool:
        return self.min_required == 0

    def consume(self, consumed: int) -> ArgArity:
        if consumed < 0:
            raise ValueError(f"consumed must be non-negative: {consumed}")
        if consumed == 0:
            return self
        new_min_required = max(0, self.min_required - consumed)
        if self.max_required is None:
            new_max_required: int | None = None
        else:
            if consumed > self.max_required:
                raise ValueError(
                    f"consumed must be <= max_required: {consumed} > {self.max_required}"
                )
            new_max_required = self.max_required - consumed
        return ArgArity(new_min_required, new_max_required)

    def as_suffix_string(self) -> str:
        if self.min_required == 1 and self.max_required == 1:
            return ""
        if self.min_required == 0 and self.max_required == 1:
            return "?"
        if self.min_required == 1 and self.max_required is None:
            return "+"
        if self.min_required == 0 and self.max_required is None:
            return "*"
        if self.max_required is None:
            return f"{{{self.min_required},}}"
        return f"{{{self.min_required}..{self.max_required}}}"


ArgArity.Required = ArgArity(1, 1)  # type: ignore[attr-defined]
ArgArity.Optional = ArgArity(0, 1)  # type: ignore[attr-defined]
ArgArity.ZeroOrMore = ArgArity(0, None)  # type: ignore[attr-defined]
ArgArity.OneOrMore = ArgArity(1, None)  # type: ignore[attr-defined]


class MatchArgsException(Exception):
    pass


class TooManyArgumentsException(MatchArgsException):
    def __init__(self, values: Sequence[object]):
        self.values = list(values)
        super().__init__(
            f"Too many arguments provided. Extra: {', '.join(map(str, self.values))}"
        )


class MissingArgumentException(MatchArgsException):
    def __init__(self, names: Sequence[object]):
        self.names = list(names)
        super().__init__(f"Missing required argument: '{self.names}'")


class DuplicateArgumentException(MatchArgsException):
    def __init__(self, name: object):
        self.name = name
        super().__init__(f"Duplicate argument provided for: '{name}'")


class PositionalArgumentsAfterOutOfOrderNamedArgumentException(MatchArgsException):
    def __init__(self, arg_value: str, arg_index: int, named_arg_index: int):
        self.arg_value = arg_value
        self.arg_index = arg_index
        self.named_arg_index = named_arg_index
        super().__init__(
            "Positional argument "
            f"'{arg_value}' (at index {arg_index}) cannot follow an out-of-order named "
            f"argument (last one at index {named_arg_index})."
        )


class UnknownArgumentException(MatchArgsException):
    def __init__(self, names: Sequence[object]):
        self.names = list(names)
        super().__init__(f"Unknown named argument: {self.names}")


class NamedArgumentRequiresValueException(MatchArgsException):
    def __init__(self, names: Sequence[object]):
        self.names = list(names)
        super().__init__(f"Named argument {self.names} requires at least one value.")


class AmbiguousPositionalArgumentException(MatchArgsException):
    def __init__(
        self,
        arg_value: str | None = None,
        possible_params: list[str] | None = None,
        details: str = "Ambiguous assignment for positional arguments.",
    ):
        self.arg_value = arg_value
        self.possible_params = possible_params
        message = details
        if arg_value is not None:
            message += f" Argument: '{arg_value}'."
        if possible_params is not None:
            message += f" Could belong to: {', '.join(possible_params)}."
        super().__init__(message)


class NamedArgumentValueExpectedException(MatchArgsException):
    def __init__(self, name: str, unexpected_arg: str):
        self.name = name
        self.unexpected_arg = unexpected_arg
        super().__init__(
            f"Named argument ':{name}' expected a value, but got named argument ':{unexpected_arg}'."
        )


@dataclass(frozen=True)
class NamedArg(Generic[ArgumentName]):
    name: ArgumentName


@dataclass(frozen=True)
class PositionalArg(Generic[ArgumentValue]):
    value: ArgumentValue


class GoResult:
    @property
    def severity(self) -> int:
        raise NotImplementedError


@dataclass(frozen=True)
class GoSuccess(GoResult, Generic[ArgumentName, ArgumentValue]):
    result: dict[ArgumentName, list[ArgumentValue]]

    @property
    def severity(self) -> int:
        return 0


@dataclass(frozen=True)
class GoMissing(GoResult, Generic[ArgumentName, ArgumentValue]):
    missing: list[tuple[ArgArity, ArgumentName]]

    @property
    def severity(self) -> int:
        return 2


@dataclass(frozen=True)
class GoTooMany(GoResult, Generic[ArgumentName, ArgumentValue]):
    arg_name: ArgumentName
    extra_values: list[ArgumentValue]
    is_duplicate: bool

    @property
    def severity(self) -> int:
        return 1


@dataclass(frozen=True)
class GoPositionalInNamedMode(GoResult, Generic[ArgumentName, ArgumentValue]):
    arg_value: ArgumentValue
    due_to_named_out_of_order: bool

    @property
    def severity(self) -> int:
        return 5


@dataclass(frozen=True)
class GoUnknownPositionalArgument(GoResult, Generic[ArgumentName, ArgumentValue]):
    arg_value: ArgumentValue

    @property
    def severity(self) -> int:
        return 5


@dataclass(frozen=True)
class GoAmbiguous(GoResult, Generic[ArgumentName, ArgumentValue]):
    arg_name: ArgumentName

    @property
    def severity(self) -> int:
        return 10


class ParameterPosition:
    def inc_if_positional(self) -> ParameterPosition:
        if isinstance(self, PositionalPosition):
            return PositionalPosition(self.parameter_index + 1)
        return self


@dataclass(frozen=True)
class NamedPosition(ParameterPosition):
    due_to_named_out_of_order: bool


@dataclass(frozen=True)
class PositionalPosition(ParameterPosition):
    parameter_index: int


@dataclass(frozen=True)
class ConsumptionMode:
    min: int
    greedy: bool


def _result_map_put(
    result: dict[ArgumentName, list[ArgumentValue]],
    key: ArgumentName,
    values: list[ArgumentValue],
) -> dict[ArgumentName, list[ArgumentValue]]:
    updated = {k: list(v) for k, v in result.items()}
    updated[key] = values
    return updated


def match_args(
    parameters: list[tuple[ArgArity, ArgumentName]],
    arguments: list[NamedArg[ArgumentName] | PositionalArg[ArgumentValue]],
) -> dict[ArgumentName, list[ArgumentValue]]:
    parameter_names = [name for _, name in parameters]
    if len(set(parameter_names)) != len(parameters):
        raise ValueError(f"Duplicate parameter names found: {parameter_names}")

    param_to_arity: dict[ArgumentName, ArgArity] = {name: arity for arity, name in parameters}

    invalid_named_args = [
        arg.name
        for arg in arguments
        if isinstance(arg, NamedArg) and arg.name not in param_to_arity
    ]
    if invalid_named_args:
        raise UnknownArgumentException(invalid_named_args)

    empty_named_args: list[object] = []
    for index, arg in enumerate(arguments):
        if not isinstance(arg, NamedArg):
            continue
        if index + 1 >= len(arguments) or isinstance(arguments[index + 1], NamedArg):
            empty_named_args.append(arg.name)
    if empty_named_args:
        raise NamedArgumentRequiresValueException(empty_named_args)

    def go(
        depth: int,
        position: ParameterPosition,
        argument_index: int,
        result: dict[ArgumentName, list[ArgumentValue]],
    ) -> GoResult:
        if depth > len(parameters) + len(arguments):
            raise RuntimeError(
                f"Recursion depth exceeded: {depth} > {len(parameters) + len(arguments)}"
            )

        def consume(
            arg_position: ParameterPosition,
            arg_param_name: ArgumentName,
            mode: ConsumptionMode,
            skip_args: int,
            new_values: list[ArgumentValue],
        ) -> GoResult:
            current_value_list = result[arg_param_name]
            param_arity = param_to_arity[arg_param_name]
            effective_arity = param_arity.consume(len(current_value_list))
            new_value_count = len(new_values)

            if effective_arity.max_required == 0:
                return GoTooMany(
                    arg_param_name,
                    new_values,
                    param_arity.max_required == 1,
                )

            min_consumed = max(mode.min, min(effective_arity.min_required, new_value_count))
            if effective_arity.max_required is not None:
                max_consumable = min(effective_arity.max_required, new_value_count)
            else:
                max_consumable = new_value_count

            if mode.greedy:
                min_consumed = max(min_consumed, max_consumable)

            best: GoResult | None = None

            def consider(case: GoResult) -> GoAmbiguous | None:
                nonlocal best
                if isinstance(case, GoAmbiguous):
                    return case

                if not isinstance(best, GoSuccess):
                    if isinstance(case, GoSuccess):
                        best = case
                    else:
                        if best is None:
                            best = case
                        elif best.severity < case.severity:
                            best = case
                else:
                    if isinstance(case, GoSuccess) and case != best:
                        return GoAmbiguous(arg_param_name)
                return None

            for consumed in range(min_consumed, max_consumable + 1):
                final_arity = effective_arity.consume(consumed)
                new_result = _result_map_put(
                    result,
                    arg_param_name,
                    current_value_list + new_values[:consumed],
                )

                case = go(
                    depth + 1,
                    arg_position.inc_if_positional(),
                    argument_index + skip_args + consumed,
                    new_result,
                )
                r = consider(case)
                if r is not None:
                    return r

                if final_arity.max_required != 0 and consumed > 0:
                    case2 = go(
                        depth + 1,
                        arg_position,
                        argument_index + skip_args + consumed,
                        new_result,
                    )
                    r2 = consider(case2)
                    if r2 is not None:
                        return r2

            if best is None:
                raise RuntimeError("Expected at least one branch result")
            return best

        if argument_index >= len(arguments):
            missing_params = [
                (arity, name)
                for arity, name in parameters
                if arity.consume(len(result[name])).min_required > 0
            ]
            if missing_params:
                return GoMissing(missing_params)
            return GoSuccess(result)

        if isinstance(position, PositionalPosition) and position.parameter_index >= len(parameters):
            return go(depth + 1, NamedPosition(due_to_named_out_of_order=False), argument_index, result)

        arg = arguments[argument_index]
        if isinstance(arg, PositionalArg):
            if isinstance(position, PositionalPosition):
                _, param_name = parameters[position.parameter_index]
                return consume(
                    arg_position=position,
                    arg_param_name=param_name,
                    mode=ConsumptionMode(min=0, greedy=False),
                    skip_args=0,
                    new_values=[arg.value],
                )
            assert isinstance(position, NamedPosition)
            return GoPositionalInNamedMode(arg.value, position.due_to_named_out_of_order)

        arg_param_name = arg.name
        new_values: list[ArgumentValue] = []
        for next_arg in arguments[argument_index + 1 :]:
            if isinstance(next_arg, NamedArg):
                break
            new_values.append(next_arg.value)

        greedy = True

        if isinstance(position, NamedPosition):
            return consume(
                arg_position=position,
                arg_param_name=arg_param_name,
                mode=ConsumptionMode(min=1, greedy=greedy),
                skip_args=1,
                new_values=new_values,
            )

        assert isinstance(position, PositionalPosition)
        _, param_name = parameters[position.parameter_index]
        if arg_param_name == param_name:
            return consume(
                arg_position=position,
                arg_param_name=arg_param_name,
                mode=ConsumptionMode(min=1, greedy=greedy),
                skip_args=1,
                new_values=new_values,
            )

        new_parameter_index = next(
            (i for i, (_, name) in enumerate(parameters) if name == arg_param_name),
            -1,
        )
        if new_parameter_index == -1:
            raise RuntimeError("Invariant violated: named arg should have been validated")
        if new_parameter_index == position.parameter_index:
            raise RuntimeError("Invariant violated: expected mismatched parameter index")

        if new_parameter_index < position.parameter_index:
            return consume(
                arg_position=NamedPosition(due_to_named_out_of_order=True),
                arg_param_name=arg_param_name,
                mode=ConsumptionMode(min=1, greedy=greedy),
                skip_args=1,
                new_values=new_values,
            )

        all_optional = all(
            parameters[i][0].is_nullable
            for i in range(position.parameter_index, new_parameter_index)
        )
        if all_optional:
            return consume(
                arg_position=PositionalPosition(new_parameter_index),
                arg_param_name=arg_param_name,
                mode=ConsumptionMode(min=1, greedy=greedy),
                skip_args=1,
                new_values=new_values,
            )

        return consume(
            arg_position=NamedPosition(due_to_named_out_of_order=True),
            arg_param_name=arg_param_name,
            mode=ConsumptionMode(min=1, greedy=greedy),
            skip_args=1,
            new_values=new_values,
        )

    initial_map: dict[ArgumentName, list[ArgumentValue]] = {
        name: [] for _, name in parameters
    }
    result = go(
        depth=0,
        position=PositionalPosition(0),
        argument_index=0,
        result=initial_map,
    )

    if isinstance(result, GoSuccess):
        return result.result
    if isinstance(result, GoMissing):
        raise MissingArgumentException([str(name) for _, name in result.missing])
    if isinstance(result, GoUnknownPositionalArgument):
        raise UnknownArgumentException([str(result.arg_value)])
    if isinstance(result, GoTooMany):
        if result.is_duplicate:
            raise DuplicateArgumentException(str(result.arg_name))
        raise TooManyArgumentsException([str(v) for v in result.extra_values])
    if isinstance(result, GoAmbiguous):
        raise AmbiguousPositionalArgumentException(str(result.arg_name))
    if isinstance(result, GoPositionalInNamedMode):
        if result.due_to_named_out_of_order:
            raise PositionalArgumentsAfterOutOfOrderNamedArgumentException(
                str(result.arg_value),
                0,
                0,
            )
        raise TooManyArgumentsException([str(result.arg_value)])

    raise RuntimeError(f"Unexpected go result: {result!r}")
