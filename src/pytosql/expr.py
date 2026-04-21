from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import partial
from io import StringIO
from itertools import starmap
from typing import Any, Self

dataclass_decorator = dataclass(slots=True, frozen=True)


class MethodFallBack:
    __slots__ = ()

    def __getattr__(self, name: str, /) -> Callable[..., CallableExpr]:
        return partial(CallableExpr.make, name, self)


@dataclass_decorator
class Parameter(MethodFallBack):
    value: Any


@dataclass_decorator
class Expr(MethodFallBack):
    max_deepness: int
    attrs: tuple[str, ...] = ()

    def __str__(self, /):
        return ".".join(self.attrs)

    def __getattr__(self, name: str, /) -> Expr | Callable[..., CallableExpr]:
        if len(self.attrs) >= self.max_deepness:
            return super().__getattr__(name)
        else:
            return replace(self, attrs=self.attrs + (name,))


@dataclass_decorator
class CallableExpr(MethodFallBack):
    function_name: str
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] | None = None

    @classmethod
    def make(cls, function_name: str, *args, **kwargs) -> CallableExpr:
        return cls(function_name, args, kwargs)


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

    def __str__(self, /) -> str:
        with StringIO() as buffer:
            for stmt, (args, kw) in vars(self).items():
                buffer.write(stmt)
                if args:
                    buffer.write(" ")
                    buffer.write(", ".join(map(str, args)))
                if kw:
                    buffer.write(", ".join(starmap("{!s} as {!s}".format, kw.items())))
            return buffer.getvalue()


if __name__ == "__main__":
    expr1 = Expr(4, ("a", "b", "c"))
    expr2 = Expr(4).a.b.c
    print(expr1, expr2, expr1 == expr2)

    querier = Querier()
    print(vars(querier.select(expr1).filter(expr2)))
