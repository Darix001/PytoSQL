from collections.abc import Sequence
from operator import attrgetter
from string.templatelib import Template
from types import ModuleType
from typing import Any, Callable

from more_itertools import interleave_longest

tuple_sanitizer_type = Callable[[Template], tuple[str, tuple[Any]]]

dict_sanitizer_type = Callable[[Template], tuple[str, dict[str, Any]]]

get_expression = attrgetter("expression")


def get_sanitizer(
    db_module: ModuleType,
) -> tuple_sanitizer_type | dict_sanitizer_type:
    return sanitizers[db_module.paramstyle]


def static_symbol_sanitizer(symbol: str) -> tuple_sanitizer_type:
    def sanitizer(template: Template) -> tuple[str, tuple[Any]]:
        return symbol.join(template.strings), template.values

    return sanitizer


def create_named_sanitizer(format_func: Callable[[str], str]) -> dict_sanitizer_type:
    def sanitizer(template: Template) -> tuple[str, dict[str, Any]]:
        names = [interpolation.expression for interpolation in template.interpolations]
        return "".join(
            interleave_longest(map(format_func, names), template.strings)
        ), dict(zip(names, template.values))

    return sanitizer


sanitizers: dict[str, tuple_sanitizer_type | dict_sanitizer_type] = {
    "qmark": static_symbol_sanitizer("?"),
    # "numeric": numeric_sanitizer,
    # "named": named_sanitizer,
    # "pyformat": pyformat_sanitizer,
    "format": static_symbol_sanitizer("%s"),
}
