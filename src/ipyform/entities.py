import dataclasses
from dataclasses import dataclass
from operator import attrgetter
from typing import List, Literal, Optional, Union


@dataclass(repr=False)
class Param:
    code: str
    lineno: int
    field_type: Literal["dropdown", "slider", "input"]
    var_type: Literal["boolean", "date", "string", "raw", "number", "integer"]
    variable: str
    value: Union[int, float, str, bool, None]

    options: Optional[List[str]] = None
    allow_input: bool = False

    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None

    placeholder: Optional[str] = None

    # Custom __repr__ to only show non-default fields
    def __repr__(self):  # pragma: no cover
        nodef_f_vals = (
            (f.name, attrgetter(f.name)(self))
            for f in dataclasses.fields(self)
            if attrgetter(f.name)(self) != f.default
        )

        nodef_f_repr = ", ".join(f"{name}={value}" for name, value in nodef_f_vals)
        return f"{self.__class__.__name__}({nodef_f_repr})"


@dataclass
class ParamError:
    code: str
    lineno: int
    error: str


@dataclass
class Markdown:
    code: str
    lineno: int
    text: str


@dataclass
class Form:
    code: list[str]
    title: Optional[str]
    params: List[Param]
    markdowns: List[Markdown]
    errors: List[ParamError]

    display_mode: Literal["form", "code", "both"] = "both"
