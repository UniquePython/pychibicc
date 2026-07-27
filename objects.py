from dataclasses import dataclass

from cint import CInt
from dtypes import Dtype


@dataclass
class Obj:
    """Represents a local variable."""

    name: str  # Variable name
    dtype: Dtype  # Data type
    offset: CInt = 0  # Offset from RBP
