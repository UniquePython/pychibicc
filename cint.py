"""A Python integer type that behaves like a C `int` (signed 32-bit).

Every arithmetic operation wraps its result into the signed 32-bit
two's-complement range, mirroring what a real C compiler gets for free
from `int` being a fixed-width type. Unlike Python's `int`, values never
grow unbounded, so overflow/wraparound in the compiled C program's
semantics is reproduced faithfully rather than silently ignored.
"""

from __future__ import annotations

_BITS = 32
_MASK = (1 << _BITS) - 1
_SIGN_BIT = 1 << (_BITS - 1)
_MODULUS = 1 << _BITS


def _wrap(value: int) -> int:
    """Wraps a plain Python int into signed 32-bit two's-complement range.

    Args:
        value (int): Any integer, in or out of 32-bit range.

    Returns:
        int: The value reinterpreted as a signed 32-bit two's-complement
            integer, as a plain Python int already in [-2**31, 2**31 - 1].
    """
    value &= _MASK
    if value & _SIGN_BIT:
        value -= _MODULUS
    return value


class CInt:
    """A signed 32-bit integer that wraps on overflow, like C's `int`."""

    __slots__ = ("_value",)

    def __init__(self, value: int = 0):
        """Creates a CInt, wrapping the input into 32-bit range.

        Args:
            value (int): The value to wrap. Accepts plain int or CInt.
        """
        if isinstance(value, CInt):
            value = value._value
        self._value = _wrap(int(value))

    # --- conversion / display ---

    def __int__(self) -> int:
        return self._value

    def __index__(self) -> int:
        # Lets CInt be used anywhere Python needs a real int: range(),
        # list indexing/slicing, bin()/hex(), etc.
        return self._value

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"CInt({self._value})"

    def __format__(self, spec: str) -> str:
        return format(self._value, spec)

    def __bool__(self) -> bool:
        return self._value != 0

    def __hash__(self) -> int:
        return hash(self._value)

    # --- comparisons ---

    def _coerce(self, other) -> int | None:
        if isinstance(other, CInt):
            return other._value
        if isinstance(other, int):
            return other
        return None

    def __eq__(self, other) -> bool:
        o = self._coerce(other)
        return self._value == o if o is not None else NotImplemented

    def __lt__(self, other) -> bool:
        o = self._coerce(other)
        return self._value < o if o is not None else NotImplemented

    def __le__(self, other) -> bool:
        o = self._coerce(other)
        return self._value <= o if o is not None else NotImplemented

    def __gt__(self, other) -> bool:
        o = self._coerce(other)
        return self._value > o if o is not None else NotImplemented

    def __ge__(self, other) -> bool:
        o = self._coerce(other)
        return self._value >= o if o is not None else NotImplemented

    # --- arithmetic (wrap every result to 32-bit range) ---

    def __add__(self, other):
        o = self._coerce(other)
        return CInt(self._value + o) if o is not None else NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        o = self._coerce(other)
        return CInt(self._value - o) if o is not None else NotImplemented

    def __rsub__(self, other):
        o = self._coerce(other)
        return CInt(o - self._value) if o is not None else NotImplemented

    def __mul__(self, other):
        o = self._coerce(other)
        return CInt(self._value * o) if o is not None else NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __floordiv__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        # C truncates toward zero; Python's // floors toward -inf.
        q = abs(self._value) // abs(o)
        if (self._value < 0) != (o < 0):
            q = -q
        return CInt(q)

    def __rfloordiv__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return CInt(o).__floordiv__(self._value)

    def __mod__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        # C's % has the sign of the dividend, unlike Python's.
        r = abs(self._value) % abs(o)
        if self._value < 0:
            r = -r
        return CInt(r)

    def __rmod__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return CInt(o).__mod__(self._value)

    def __neg__(self):
        return CInt(-self._value)

    def __pos__(self):
        return CInt(self._value)

    def __abs__(self):
        return CInt(abs(self._value))
