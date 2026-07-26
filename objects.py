from dataclasses import dataclass

from dtypes import Dtype


@dataclass
class Obj:
    """Represents a local variable."""

    name: str  # Variable name
    dtype: Dtype  # Data type
    offset: int = 0  # Offset from RBP
