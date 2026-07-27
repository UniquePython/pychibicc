from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field
from enum import Enum, auto

from tokens import Token


class DtypeKind(Enum):
    """Represents the different kinds of types."""

    INT = auto()
    PTR = auto()
    FUNC = auto()


@dataclass
class Dtype:
    """Represents a type."""

    kind: DtypeKind  # Type kind

    # Pointer
    base: Dtype | None = None  # Pointee type

    # Declaration
    name: Token | None = None  # Declarator token

    # Function type
    returnDtype: Dtype | None = None
    params: list[Dtype] = field(default_factory=list)


dtypeInt = Dtype(DtypeKind.INT)


def isInteger(dtype: Dtype) -> bool:
    """Returns whether the given type is an integer.

    Args:
        dtype (Dtype): The type to test.

    Returns:
        bool: True if the type is an integer, otherwise False.
    """
    return dtype.kind == DtypeKind.INT


def copyType(dtype: Dtype) -> Dtype:
    """Creates a shallow copy of a type.

    Args:
        dtype (Dtype): The type to copy.

    Returns:
        Dtype: A shallow copy of the type.
    """
    return copy(dtype)


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


def funcType(returnDtype: Dtype) -> Dtype:
    """Creates a function type.

    Args:
        returnDtype (Dtype): The function's return type.

    Returns:
        Dtype: The newly created function type.
    """
    return Dtype(
        kind=DtypeKind.FUNC,
        returnDtype=returnDtype,
    )
