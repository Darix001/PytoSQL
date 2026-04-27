from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, NamedTuple, Optional

optional_str = Optional[str]

paramstyle_contexts_args: dict[str, tuple[optional_str, optional_str, optional_str]] = {
    "sqlite3": ("?", ":{name}", None),
    "duckdb": ("?", "${name}", "${number}"),
    "mysql": ("%s", "%({name})s", None),
    "oracledb": (None, None, ":{number}"),
    "psycopg2": ("%s", "%({name})s", None),
    "pyodbc": ("?", None, None),
}


class ParamStyleContext(NamedTuple):
    """Controls how parameters are rendered for specific databases"""

    positional_symbol: optional_str  # e.g., '?', '%s', None for named
    named_format: optional_str  # e.g., ':{name}', '%({name})s'
    numeric_format: optional_str  # e.g., ':{name}', '%({name})s'

    @classmethod
    def from_db_api_string(cls, db_api_name: str, /) -> ParamStyleContext:
        return cls(*paramstyle_contexts_args[db_api_name])

    def __enter__(self):
        self.token = _current_paramstyle_context.set(self)
        return self

    def __exit__(self, *args):
        _current_paramstyle_context.reset(self.token)
        del self.token


paramstyle_contexts: dict[str, ParamStyleContext] = {
    db_api_name: ParamStyleContext(*args)
    for db_api_name, args in paramstyle_contexts_args.items()
}

# Context variable for thread-local configuration
_current_paramstyle_context = ContextVar(
    "param_context",
    default=ParamStyleContext(*paramstyle_contexts_args["sqlite3"]),
)


def get_param_context() -> ParamStyleContext:
    """Get the current parameter context"""
    return _current_paramstyle_context.get()


def set_param_context(db_api_name: str):
    """Set the current parameter context"""
    _current_paramstyle_context.set(paramstyle_contexts[db_api_name])


_current_collector = ContextVar(
    "parameters_collector",
)


def get_parameters_collector() -> ParamStyleContext:
    """Get the current parameter context"""
    return _current_collector.get()


@dataclass
class parameters_collector:
    """Context manager for temporary paramstyle changes"""

    param_counter: int = 0
    params_list: list = field(default_factory=list)
    params_dict: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.param_context = get_param_context()

    def __enter__(self):
        self.token = _current_collector.set(self)
        return self

    def __exit__(self, *args):
        self.params_list.clear()
        self.params_dict.clear()
        self.param_counter = 0
        _current_collector.reset(self.token)
