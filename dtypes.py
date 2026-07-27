from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field
from enum import Enum, auto

from cint import CInt
from tokens import Token


class DtypeKind(Enum):
    """Represents the different kinds of types."""

    INT = auto()
    PTR = auto()
    FUNC = auto()
    ARRAY = auto()


@dataclass
class Dtype:
    """Represents a type."""

    kind: DtypeKind  # Type kind
    size: CInt = 0  # sizeof() value

    # Pointer-to or array-of type. We intentionally use the same member
    # to represent pointer/array duality in C.
    #
    # In many contexts in which a pointer is expected, we examine this
    # member instead of "kind" member to determine whether a type is a
    # pointer or not. That means in many contexts "array of T" is
    # naturally handled as if it were "pointer to T", as required by
    # the C spec.
    base: Dtype | None = None

    # Declaration
    name: Token | None = None  # Declarator token

    # Array
    arrayLen: CInt = 0

    # Function type
    returnDtype: Dtype | None = None
    params: list[Dtype] = field(default_factory=list)


dtypeInt = Dtype(kind=DtypeKind.INT, size=8)


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
    return Dtype(kind=DtypeKind.PTR, size=8, base=base)


def funcType(returnDtype: Dtype) -> Dtype:
    """Creates a function type.

    Args:
        returnDtype (Dtype): The function's return type.

    Returns:
        Dtype: The newly created function type.
    """
    return Dtype(kind=DtypeKind.FUNC, returnDtype=returnDtype)


def arrayOf(base: Dtype, length: CInt) -> Dtype:
    """Creates an array type.

    Args:
        base (Dtype): The array element type.
        length (CInt): The number of elements.

    Returns:
        Dtype: The resulting array type.
    """
    return Dtype(
        kind=DtypeKind.ARRAY,
        size=base.size * length,
        base=base,
        arrayLen=length,
    )
