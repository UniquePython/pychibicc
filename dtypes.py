from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from tokens import Token


class DtypeKind(Enum):
    """Represents the different kinds of types."""

    INT = auto()
    PTR = auto()


@dataclass
class Dtype:
    """Represents a type."""

    kind: DtypeKind  # Type kind

    # Pointer
    base: Dtype | None = None  # Pointee type

    # Declaration
    name: Token | None = None  # Declarator token


dtypeInt = Dtype(DtypeKind.INT)


def isInteger(dtype: Dtype) -> bool:
    """Returns whether the given type is an integer.

    Args:
        dtype (Dtype): The type to test.

    Returns:
        bool: True if the type is an integer, otherwise False.
    """
    return dtype.kind == DtypeKind.INT


def pointerTo(base: Dtype) -> Dtype:
    """Creates a pointer type to the given base type.

    Args:
        base (Dtype): The pointee type.

    Returns:
        Dtype: The resulting pointer type.
    """
    return Dtype(
        kind=DtypeKind.PTR,
        base=base,
    )
