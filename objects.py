from dataclasses import dataclass


@dataclass
class Obj:
    """Represents a local variable."""

    name: str  # Variable name
    offset: int = 0  # Offset from RBP
