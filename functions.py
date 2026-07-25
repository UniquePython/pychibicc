from dataclasses import dataclass, field

from nodes import Node
from objects import Obj


@dataclass
class Function:
    """Represents a function."""

    body: list[Node] = field(default_factory=list)  # Function body
    locals: list[Obj] = field(default_factory=list)  # Local variables
    stackSize: int = 0  # Stack size
