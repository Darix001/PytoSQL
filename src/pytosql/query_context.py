from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from types import ModuleType
from typing import Any, Dict, Optional, Tuple, Union


class ParamStyle(Enum):
    """Common database paramstyles"""

    QMARK = "qmark"  # ?
    NUMERIC = "numeric"  # :1, :2
    NAMED = "named"  # :name
    FORMAT = "format"  # %s
    PYFORMAT = "pyformat"  # %(name)s


param_styles_args = {
    "qmark": ("?", None),
    "numeric": (":", None, True),
    "named": (None, ":{}"),
    "format": ("%s", "%({})s"),
    "pyformat": (None, "%({})s"),
}


@dataclass
class ParamContext:
    """Controls how parameters are rendered for specific databases"""

    paramstyle: ParamStyle
    positional_symbol: Optional[str]  # e.g., '?', '%s', None for named
    named_format: Optional[str]  # e.g., ':{name}', '%({name})s'
    auto_increment: bool = False  # Auto-number named params as positional
    param_counter: int = field(default=0, repr=False)
    param_list: list = field(default_factory=list, repr=False)

    @classmethod
    def from_db_module(cls, db_module: ModuleType, /):
        paramstyle = db_module.paramstyle
        return cls(paramstyle, *param_styles_args[paramstyle])

    def __enter__(self):
        self.token = _current_context.set(self)
        self.param_counter = 0
        return self

    def __exit__(self, *args):
        self.param_list.clear()
        self.param_counter = 0
        _current_context.reset(self.token)


# Context variable for thread-local configuration
_current_context = ContextVar(
    "param_context",
    default=ParamContext(ParamStyle.QMARK, "?", None),
)


def get_context() -> ParamContext:
    """Get the current parameter context"""
    return _current_context.get()


def set_context(db_module: ModuleType):
    """Set the current parameter context"""
    _current_context.set(ParamContext.from_db_module(db_module))


# class redirect_param_context:
#     """Context manager for temporary paramstyle changes"""

#     def __init__(self, db_module: ModuleType):
#         self.context = ParamContext.from_db_module(db_module)

#     def __enter__(self):
#         self.token = _current_context.set(self.context)
#         self.context.param_counter = 0
#         return self.context

#     def __exit__(self, *args):
#         self.context.param_list.clear()
#         self.context.param_counter = 0
#         _current_context.reset(self.token)
