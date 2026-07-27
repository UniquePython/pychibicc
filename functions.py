from dataclasses import dataclass, field

from cint import CInt
from nodes import Node
from objects import Obj


@dataclass
class Function:
    """Represents a function."""

    name: str = ""  # Function name
    params: list[Obj] = field(default_factory=list)  # Function parameters

    body: Node | None = None  # Function body
    locals: list[Obj] = field(default_factory=list)  # Local variables
    stackSize: CInt = 0  # Stack size
