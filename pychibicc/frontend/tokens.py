from __future__ import annotations

import typing
from dataclasses import dataclass
from enum import Enum, auto

from pychibicc.ctype.cint import CInt

if typing.TYPE_CHECKING:
    from pychibicc.syntax.dtypes import Dtype


class TokenKind(Enum):
    """Represents the different kinds of lexical tokens.

    Args:
        Enum (Enum): Base enumeration class.
    """

    IDENT = auto()  # Identifiers
    PUNCT = auto()  # Punctuators
    KEYWORD = auto()  # Keywords
    STR = auto()  # String literals
    NUM = auto()  # Numeric literals
    EOF = auto()  # End-of-file markers


@dataclass
class Token:
    """Represents a lexical token produced by the tokenizer."""

    kind: TokenKind  # Token kind
    val: CInt = 0  # If kind is NUM, its value
    lexeme: str = ""  # Token lexeme
    pos: CInt = 0  # Token starting position
    length: CInt = 0  # Token length
    dtype: Dtype | None = None  # Used if kind == TokenKind.STR
    string: str = "\0"  # String literal contents including terminating '\0'
