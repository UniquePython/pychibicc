from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class DTypeKind(Enum):
    """Represents the different kinds of types."""

    INT = auto()
    PTR = auto()


@dataclass
class DType:
    """Represents a type."""

    kind: DTypeKind
    base: DType | None = None


dtypeInt = DType(DTypeKind.INT)


def isInteger(dtype: DType) -> bool:
    """Returns whether the given type is an integer.

    Args:
        dtype (DType): The type to test.

    Returns:
        bool: True if the type is an integer, otherwise False.
    """
    return dtype.kind == DTypeKind.INT


def pointerTo(base: DType) -> DType:
    """Creates a pointer type to the given base type.

    Args:
        base (DType): The pointee type.

    Returns:
        DType: The resulting pointer type.
    """
    return DType(
        kind=DTypeKind.PTR,
        base=base,
    )
