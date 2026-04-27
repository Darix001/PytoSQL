from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import partial
from io import StringIO
from operator import methodcaller
from typing import Any, Self

from .query_context import _current_collector, parameters_collector

dataclass_decorator = dataclass(slots=True, frozen=True, order=False, eq=False)


class BaseExpr:
    __slots__ = ()

    def operator_function(op_symbol: str, /) -> Callable[[Self, Any], OperatorExpr]:
        def wrapper(self, other: Any) -> OperatorExpr:
            if not isinstance(other, BaseExpr):
                other = Parameter(other)
            return OperatorExpr(self, op_symbol, other)

        return wrapper

    __add__, __sub__, __mul__, __truediv__ = map(operator_function, "+-*/")

    __eq__, __ne__, __lt__, __le__, __gt__, __ge__ = map(
        operator_function, ("=", "<>", "<", "<=", ">", ">=")
    )

    __and__, __or__, __xor__ = map(operator_function, "&|^")

    __lshift__, __rshift__ = map(operator_function, ("<<", ">>"))

    __concat__ = __matmul__ = operator_function("||")

    glob, like = map(operator_function, ("glob", "like"))

    def __getattr__(self, name: str, /) -> Callable[..., CallableExpr]:
        return partial(CallableExpr.make, name, self)


@dataclass_decorator
class OperatorExpr(BaseExpr):
    left: Any
    op_symbol: str
    right: Any

    def _render(self, /) -> str:
        return f"({self.left._render()} {self.op_symbol} {self.right._render()})"


@dataclass_decorator
class Parameter(BaseExpr):
    value: Any = None
    name: str | None = None

    def _render(self, /) -> str:
        collector = _current_collector.get()
        value = self.value
        paramstyle_ctx = collector.param_context
        positional_symbol = paramstyle_ctx.positional_symbol

        if (name := self.name) is not None:
            if (fmt := paramstyle_ctx.named_format) is None:
                raise ValueError("Name set with no Named format.")
            paramstyle_ctx.params_dict[name] = value
            return fmt.format(name=name)

        collector.params_list.append(value)
        if fmt := paramstyle_ctx.numeric_format:
            collector.param_counter += 1
            return fmt.format(number=paramstyle_ctx.param_counter)
        elif positional_symbol:
            return positional_symbol
        else:
            raise ValueError(
                f"The current parameter style context does not support positional parameters: {paramstyle_ctx}"
            )


Param = Parameter


@dataclass_decorator
class Literal(BaseExpr):
    expr: str

    def _render(self, /) -> str:
        return self.expr

    __str__ = _render


Lit = Literal


@dataclass_decorator
class Expr(BaseExpr):
    max_deepness: int
    attrs: tuple[str, ...] = ()

    def _render(self, /):
        return ".".join(self.attrs)

    __str__ = _render

    def __getattr__(self, name: str, /) -> Expr | Callable[..., CallableExpr]:
        if len(self.attrs) >= self.max_deepness:
            return partial(CallableExpr.make, name, self)
        else:
            return replace(self, attrs=self.attrs + (name,))


@dataclass_decorator
class CallableExpr(BaseExpr):
    function_name: str
    args: tuple[Any, ...]

    @classmethod
    def make(cls, function_name: str, *args) -> CallableExpr:
        return cls(function_name, args)

    def __str__(self, /) -> str:
        return f"{self.function_name}({', '.join(map(str, self.args))})"


# dictionary that sotres specific statement separators.
# returns a tuple where the first element is the separator
# for multiple conditions and the second is the separator for key-value pairs.


class Querier:
    _last: str
    stmts_seps: dict[str, tuple[str, str]] = {
        "where": (" and ", " = "),
        "select": (", ", " as "),
    }

    def __init__(self, /, function_name: str | None = None):
        if function_name:
            self._last = function_name

    def __dir__(self) -> list[str]:
        return list(vars(self))

    def __call__(self, *args, **kw) -> Self:
        setattr(self, self._last, (args, kw))
        del self._last
        return self

    def __getattr__(self, name: str, /) -> Self:
        self._last = name
        return self

    def prepare(self, /) -> tuple[str, tuple[Any] | dict[str, Any]]:
        with StringIO() as buffer, parameters_collector() as ctx:
            args_printer = partial(print, end="", file=buffer)
            for stmt, (args, kw) in vars(self).items():
                buffer.writelines((stmt.replace("_", " ").strip(), " "))
                args_sep, kw_sep = self.stmts_seps.get(stmt, (", ", " = "))
                args_printer(*map(methodcaller("_render"), args), sep=args_sep)

                if kw:
                    buffer.write(", ")
                    for k, v in kw.items():
                        buffer.writelines(f"{v._render()} as {k}")
                buffer.write("\n")

                if ctx.params_dict and ctx.params_list:
                    raise ValueError("Mix of named and positional parameters")
                elif ctx.params_list:
                    data = tuple(ctx.params_list)
                elif ctx.params_dict:
                    data = ctx.params_dict.copy()
            return buffer.getvalue(), data


# T = TypeVar("T")


@dataclass(frozen=True)
class AttrFactory:
    factory: Callable[[str], Any]

    def __getattr__(self, name: str, /) -> Any:
        return self.factory(name)


column = col = Expr(1)
table = tbl = Expr(2)
schema = Expr(3)
database = db = Expr(4)

fn = AttrFactory(partial(partial, CallableExpr))
query = AttrFactory(Querier)

if __name__ == "__main__":
    print(
        *query.select(col.name, fmt_salary=Param("{:,.2f}").format(col.salary))
        .from_(table.employees)
        .where(col.salary > Param(0))
        .prepare()
    )
