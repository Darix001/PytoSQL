from functools import partial
from operator import concat, mod
from re import sub
from string.templatelib import Template
from types import ModuleType
from typing import Any, Callable

from more_itertools import interleave_longest

tuple_sanitizer_type = Callable[[Template], tuple[str, tuple[Any]]]

dict_sanitizer_type = Callable[[Template], tuple[str, dict[str, Any]]]


def get_sanitizer(
    db_module: ModuleType,
) -> tuple_sanitizer_type | dict_sanitizer_type:
    return sanitizers[db_module.paramstyle]


def static_symbol_sanitizer(symbol: str) -> tuple_sanitizer_type:
    def sanitizer(template: Template) -> tuple[str, tuple[Any]]:
        return symbol.join(template.strings), template.values

    return sanitizer


def create_named_sanitizer(
    preffix: str, suffix: str | None = None
) -> dict_sanitizer_type:
    format_func = (
        partial(concat, preffix)
        if suffix is None
        else lambda name: f"{preffix}{name}{suffix}"
    )

    def sanitizer(template: Template) -> tuple[str, dict[str, Any]]:
        names = [interpolation.expression for interpolation in template.interpolations]
        return "".join(
            interleave_longest(template.strings, map(format_func, names))
        ), dict(zip(names, template.values))

    return sanitizer


def create_numeric_sanitizer(preffix: str) -> tuple_sanitizer_type:
    fmt_func = partial(mod, preffix + "%d")

    def sanitizer(template: Template) -> tuple[str, tuple[Any]]:
        str_indexes = map(fmt_func, range(len(values := template.values)))
        return "".join(interleave_longest(template.strings, str_indexes)), values

    return sanitizer


sanitizers: dict[str, tuple_sanitizer_type | dict_sanitizer_type] = {
    "qmark": static_symbol_sanitizer("?"),
    "numeric": create_numeric_sanitizer(":"),
    "named": create_named_sanitizer(":"),
    "pyformat": create_named_sanitizer("%(", ")s"),
    "format": static_symbol_sanitizer("%s"),
}
