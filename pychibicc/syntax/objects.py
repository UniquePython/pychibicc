from dataclasses import dataclass

from pychibicc.ctype.cint import CInt
from pychibicc.syntax.dtypes import Dtype


@dataclass
class Obj:
    """Represents a local variable."""

    name: str  # Variable name
    dtype: Dtype  # Data type
    offset: CInt = 0  # Offset from RBP
