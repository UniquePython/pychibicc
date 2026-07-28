from __future__ import annotations

import typing
from dataclasses import dataclass, field

from pychibicc.ctype.cint import CInt
from pychibicc.syntax.dtypes import Dtype

if typing.TYPE_CHECKING:
    from pychibicc.syntax.nodes import Node


@dataclass
class Obj:
    """Represents a variable or function."""

    name: str  # Variable name
    dtype: Dtype  # Data type
    isLocal: bool = False  # Local or global

    # Local variable
    offset: CInt = 0  # Offset from RBP

    # Global variable or function
    isFunction: bool = False

    params: list[Obj] = field(default_factory=list)  # Function parameters
    body: Node | None = None  # Function body
    locals: list[Obj] = field(default_factory=list)  # Local variables
    stackSize: CInt = 0  # Stack size
