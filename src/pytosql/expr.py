from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import partial
from io import StringIO
from itertools import starmap
from typing import Any, Self

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
        operator_function, ("==", "!=", "<", "<=", ">", ">=")
    )

    __and__, __or__, __xor__ = map(operator_function, "&|^")

    __lshift__, __rshift__ = map(operator_function, ("<<", ">>"))

    __concat__ = __matmul__ = operator_function("||")

    def __getattr__(self, name: str, /) -> Callable[..., CallableExpr]:
        return partial(CallableExpr.make, name, self)


@dataclass_decorator
class OperatorExpr(BaseExpr):
    left: Any
    op_symbol: str
    right: Any

    def __str__(self, /) -> str:
        return f"({self.left} {self.op_symbol} {self.right})"


@dataclass_decorator
class Parameter(BaseExpr):
    value: Any
    name: str | None = None

    def __str__(self, /) -> str:
        return self.name or "?"


Param = Parameter


@dataclass_decorator
class Literal(BaseExpr):
    text: str

    def __str__(self, /) -> str:
        return self.text


Lit = Literal


@dataclass_decorator
class Expr(BaseExpr):
    max_deepness: int
    attrs: tuple[str, ...] = ()

    def __str__(self, /):
        return ".".join(self.attrs)

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


class Querier:
    _last: str

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

    def prepare(self, /) -> tuple[str, list[Any]]:
        parameters = []
        with StringIO() as buffer:
            args_printer = partial(print, sep=", ", end="", file=buffer)
            for stmt, (args, kw) in vars(self).items():
                buffer.writelines((stmt.replace("_", " "), " "))
                args_printer(*args)

                if kw:
                    buffer.write(", ")
                    for k, v in kw.items():
                        buffer.writelines(f"{v} as {k}")
                buffer.write("\n")
            return buffer.getvalue(), parameters


col = Expr(1)
table = Expr(2)
schema = Expr(3)
db = Expr(4)

if __name__ == "__main__":
    querier = Querier()
    print(
        *querier.select(col.name, fmt_salary=Param("{:,.2f}").format(col.salary))
        .from_(table.employees)
        .where(col.salary > Param(0))
        .prepare()
    )
