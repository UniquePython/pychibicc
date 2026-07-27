from dataclasses import dataclass, field

from pychibicc.ctype.cint import CInt
from pychibicc.syntax.nodes import Node
from pychibicc.syntax.objects import Obj


@dataclass
class Function:
    """Represents a function."""

    name: str = ""  # Function name
    params: list[Obj] = field(default_factory=list)  # Function parameters

    body: Node | None = None  # Function body
    locals: list[Obj] = field(default_factory=list)  # Local variables
    stackSize: CInt = 0  # Stack size
