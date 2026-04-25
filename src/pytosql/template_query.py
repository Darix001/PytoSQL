from collections.abc import Iterable
from functools import partial
from itertools import chain, repeat, zip_longest
from operator import mod
from string.templatelib import Template
from types import ModuleType
from typing import Any, Callable

tuple_converter_type = Callable[[Template], tuple[str, tuple[Any]]]

dict_converter_type = Callable[[Template], tuple[str, dict[str, Any]]]


def str_join_longest(*args: Iterable[str]) -> str:
    return "".join(chain.from_iterable(zip_longest(*args, fillvalue="")))


def get_converter(
    db_module: ModuleType,
) -> tuple_converter_type | dict_converter_type:
    return converters[db_module.paramstyle]


def static_symbol_converter(symbol: str) -> tuple_converter_type:
    def converter(template: Template) -> tuple[str, tuple[Any]]:
        return symbol.join(template.strings), template.values

    return converter


def create_named_converter(preffix: str, suffix: str = "") -> dict_converter_type:

    def converter(template: Template) -> tuple[str, dict[str, Any]]:
        names = [interpolation.expression for interpolation in template.interpolations]
        repeats = len(names)
        return str_join_longest(
            template.strings,
            repeat(preffix, repeats),
            names,
            repeat(suffix, repeats),
        ), dict(zip(names, template.values))

    return converter


def create_numeric_converter(preffix: str) -> tuple_converter_type:
    fmt_func = partial(mod, preffix + "%d")

    def converter(template: Template) -> tuple[str, tuple[Any]]:
        str_indexes = map(fmt_func, range(1, len(values := template.values) + 1))
        return str_join_longest(template.strings, str_indexes), values

    return converter


converters: dict[str, tuple_converter_type | dict_converter_type] = {
    "qmark": static_symbol_converter("?"),
    "numeric": create_numeric_converter(":"),
    "named": create_named_converter(":"),
    "pyformat": create_named_converter("%(", ")s"),
    "format": static_symbol_converter("%s"),
}
