from __future__ import annotations

from array import array
from itertools import starmap
from typing import Any, Self

from frozendict import frozendict


class BaseExpr:
    __slots__ = ("attr_sep", "attrs")


class Expr(BaseExpr):
    __slots__ = ()
    attr_sep: str
    attrs: tuple[str, ...]

    def __init__(self, /, attr_sep: str = ".", attrs: tuple[str, ...] = ()):
        self.attr_sep = attr_sep
        self.attrs = attrs

    def __str__(self, /):
        return self.attr_sep.join(self.attrs)

    def __getattr__(self, name: str) -> Expr:
        return type(self)(self.attr_sep, self.attrs + (name,))


attrs_type = frozendict[str, tuple[tuple[Any], dict[str, Any]]]


class CallableExpr(BaseExpr):
    __slots__ = "function_name"
    attrs: attrs_type
    function_name: str | None
    attr_sep: str

    def __init__(
        self,
        /,
        attrs: attrs_type = frozendict(),
        function_name: str | None = None,
        attr_sep: str = " ",
    ):
        self.attrs = attrs
        self.function_name = function_name
        self.attr_sep = attr_sep

    def __call__(self: Self, *args, **kwargs) -> Self:
        if not (function_name := self.function_name):
            raise ValueError("function_name must be set")
        return type(self)(self.attrs.set(function_name, (args, kwargs)))

    def __getattr__(self: Self, name: str) -> Self:
        return type(self)(self.attrs, name)


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

    def __getattr__(self, name: str) -> Self:
        self._last = name
        return self

    def __str__(self, /) -> str:
        buffer = array("u")
        for stmt, (args, kw) in vars(self).items():
            buffer.append(stmt)
            if args:
                buffer.append(" ")
                buffer.extend(", ".join(map(str, args)))
            if kw:
                buffer.extend(", ".join(starmap("{} {}".format, kw.items())))
        return buffer.tounicode()


if __name__ == "__main__":
    expr1 = Expr(".", ("a", "b", "c"))
    expr2 = Expr(".").a.b.c
    print(expr1, expr2, expr1 == expr2)

    querier = Querier()
    print(vars(querier.select(expr1).filter(expr2)))

    print(frozendict.__module__)
